"""Robustez do resultado da analise 01: equivalencia, dependencia entre arquivos e recorte.

A analise 01 deu nulo em densidade. Tres perguntas que um revisor faz a um nulo, e que
este script responde sobre os mesmos dados, sem nenhum desfecho novo:

  equivalencia   "ausencia de evidencia nao e evidencia de ausencia": qual o maior efeito
                 que os dados ainda admitem? Sai do IC90% de rho (o par de testes
                 unilaterais a 5% do TOST), e o TOST e rodado na margem convencional de
                 efeito pequeno, |rho| = 0,10 (Cohen). A margem e convencao, nao escolha:
                 o resultado e reportado tambem como o menor |rho| que os dados excluem.
  dependencia    arquivos do mesmo repositorio nao sao independentes. Bootstrap por
                 repositorio: reamostra repositorios inteiros, com reposicao, e recalcula
                 rho. Se o IC percentil ficar parecido com o de Fisher, a dependencia nao
                 muda a conclusao.
  recorte        sem os arquivos com teste em nome_divergente (o defeito de classe
                 aninhada do JNose, step 2, secao 2), onde n_metodos e as ocorrencias podem
                 ser de outra classe.

Uso:
    python robustez.py
    python robustez.py --csv
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "tools"))
import comum as c
import estat
from variaveis import desfechos, rotulo_agregado

MARGEM = 0.10          # efeito pequeno de Cohen para correlacao
Z90 = 1.644854         # unilateral 5%: o IC90% e o TOST a 5%
REPLICAS = 2000
SEMENTE = 42


def serie(linhas, chave):
    """(repo, desfecho, rotulo) por arquivo, com o mesmo descarte de variaveis.pares."""
    out = []
    for r in linhas:
        d = desfechos(r)
        lab = rotulo_agregado(r)
        if d is None or lab is None or d[chave] is None or c.num(r["n_metodos_teste"]) is None:
            continue
        out.append((r["github_repo"], d[chave], lab))
    return out


def equivalencia(rho, n):
    """IC90% de Fisher e o p do TOST na MARGEM: o maior dos dois p unilaterais."""
    z = math.atanh(max(min(rho, 0.999999), -0.999999))
    ep = 1.0 / math.sqrt(n - 3)
    lo, hi = math.tanh(z - Z90 * ep), math.tanh(z + Z90 * ep)
    p_baixo = 1 - estat.normal_acum((z - math.atanh(-MARGEM)) / ep)
    p_alto = estat.normal_acum((z - math.atanh(MARGEM)) / ep)
    return lo, hi, max(p_baixo, p_alto)


def bootstrap_repo(dados):
    """IC95% percentil de rho, reamostrando repositorios com reposicao."""
    por_repo = {}
    for repo, x, y in dados:
        por_repo.setdefault(repo, []).append((x, y))
    repos = sorted(por_repo)
    rng = random.Random(SEMENTE)
    rhos = []
    for _ in range(REPLICAS):
        xs, ys = [], []
        for repo in (rng.choice(repos) for _ in repos):
            for x, y in por_repo[repo]:
                xs.append(x)
                ys.append(y)
        rho = estat.spearman(xs, ys)[0]
        if not math.isnan(rho):
            rhos.append(rho)
    rhos.sort()
    return rhos[int(0.025 * len(rhos))], rhos[int(math.ceil(0.975 * len(rhos))) - 1], len(repos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("Equivalencia: IC90%% de Fisher e TOST na margem |rho| = %.2f." % MARGEM)
    print("Bootstrap: %d replicas por repositorio, semente %d, IC95%% percentil."
          % (REPLICAS, SEMENTE))
    saida = []
    for ramo in sorted(c.RAMOS):
        linhas = c.ler_ramo(ramo)
        recortes = (("todas", linhas),
                    ("sem_nome_divergente",
                     [r for r in linhas if c.num(r["n_testes_nome_divergente"]) == 0]))
        print("\n" + "=" * 100)
        print("RAMO %s" % ramo.upper())
        print("=" * 100)
        print("  %-20s %-10s %5s %5s %7s %18s %18s %8s %18s"
              % ("recorte", "desfecho", "N", "repos", "rho", "IC95% Fisher", "IC90%",
                 "p TOST", "IC95% bootstrap"))
        for recorte, sub in recortes:
            for chave in ("bruto", "densidade", "distintos"):
                dados = serie(sub, chave)
                rho, p, lo95, hi95, n = estat.spearman([d[1] for d in dados],
                                                       [d[2] for d in dados])
                lo90, hi90, p_tost = equivalencia(rho, n)
                b_lo, b_hi, n_repos = bootstrap_repo(dados)
                print("  %-20s %-10s %5d %5d %7.3f   [%6.3f, %6.3f]   [%6.3f, %6.3f] %8s"
                      "   [%6.3f, %6.3f]"
                      % (recorte, chave, n, n_repos, rho, lo95, hi95, lo90, hi90,
                         estat.formatar_p(p_tost), b_lo, b_hi))
                saida.append([ramo, recorte, chave, n, n_repos, rho, p, lo95, hi95, lo90,
                              hi90, max(abs(lo90), abs(hi90)), p_tost, b_lo, b_hi])

    if args.csv:
        destino = os.path.join(c.dados_de(__file__), "robustez.csv")
        n = c.escrever_csv(destino,
                           ["ramo", "recorte", "desfecho", "n", "n_repos", "rho", "p",
                            "ic95_baixo", "ic95_alto", "ic90_baixo", "ic90_alto",
                            "maior_efeito_compativel", "p_tost", "boot_ic95_baixo",
                            "boot_ic95_alto"],
                           [l[:3] + l[3:5] + [round(x, 6) for x in l[5:]] for l in saida])
        print("\nrobustez.csv  %d linhas" % n)


if __name__ == "__main__":
    main()
