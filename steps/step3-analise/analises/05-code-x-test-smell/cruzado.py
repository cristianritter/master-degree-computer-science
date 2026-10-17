"""Analise 05: cada code smell contra cada test smell, a grade 4 x 13.

A analise 02 perguntou se algum test smell se comporta diferente, sempre contra o code
smell agregado. Esta subdivide pelo lado da producao: blob, data class, feature envy e long
method, cada um com a propria severidade media, contra a densidade de cada um dos 13 test
smells. Foi pedida pelo orientador.

Decisoes, todas fixadas antes de rodar:

  rotulo      cs_<smell>_sev_media do proprio code smell; vazio = nao avaliado, fica fora
  desfecho    densidade (ocorrencias / n_metodos_teste); o bruto ja se mostrou tamanho
  Eager/Lazy  so linhas sem teste nome_divergente (step 1, secao 5: caem 28x e 23x ali)
  familia     os 52 testes principais, com p ajustado por Benjamini-Hochberg

As 8 celulas de Eager/Lazy sem filtro rodam como sensibilidade, fora da familia: mostram
o quanto o filtro muda.

Cada celula leva o r detectavel com 80% de poder para o seu N (0,134 a 0,163 no ramo
deterministico): um rho observado abaixo disso nao decide nada, e a tabela tem que dizer.

Uso:
    python cruzado.py
    python cruzado.py --csv
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "tools"))
import comum as c
import estat

DEPENDEM_DA_PRODUCAO = ("Eager Test", "Lazy Test")
Z_ALFA, Z_PODER = 1.959964, 0.841621   # bicaudal 0,05 e poder 80%, como no step 2


def r_detectavel(n):
    """Menor correlacao detectavel, pela transformacao z de Fisher (step 2, secao 12.1)."""
    return math.tanh((Z_ALFA + Z_PODER) / math.sqrt(n - 3))


def series(linhas, code_smell, test_smell, filtrar):
    x, y = [], []
    for r in linhas:
        if filtrar and c.num(r["n_testes_nome_divergente"]):
            continue
        lab = c.num(r[c.coluna_cs(code_smell, "sev_media")])
        v = c.num(r[c.coluna_ts(test_smell)])
        met = c.num(r["n_metodos_teste"])
        if lab is None or v is None or not met:
            continue
        x.append(v / met)
        y.append(lab)
    return x, y


def celula(linhas, cs, ts, filtrar):
    x, y = series(linhas, cs, ts, filtrar)
    rho, p, lo, hi, n = estat.spearman(x, y)
    return {"code_smell": cs, "test_smell": ts, "filtrado": filtrar, "n": n, "rho": rho,
            "p": p, "lo": lo, "hi": hi, "detectavel": r_detectavel(n)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ramo", choices=sorted(c.RAMOS), default="deterministico")
    ap.add_argument("--csv", action="store_true")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    linhas = c.ler_ramo(args.ramo)
    print("=" * 96)
    print("ANALISE 05 - code smell x test smell  |  ramo %s, %d arquivos"
          % (args.ramo, len(linhas)))
    print("Spearman, sev_media do code smell x densidade do test smell. p ajustado por FDR.")
    print("=" * 96)

    principal = [celula(linhas, cs, ts, ts in DEPENDEM_DA_PRODUCAO)
                 for cs in c.CODE_SMELLS for ts in c.SMELLS]
    for r, pa in zip(principal, estat.benjamini_hochberg([r["p"] for r in principal])):
        r["p_ajustado"] = pa

    for cs in c.CODE_SMELLS:
        bloco = [r for r in principal if r["code_smell"] == cs]
        print("\n  %s" % cs)
        print("    %-30s %5s %8s %9s %9s %10s" % ("test smell", "N", "rho", "p", "p ajust.",
                                                  "detectavel"))
        for r in bloco:
            nota = "  (sem nome_divergente)" if r["filtrado"] else ""
            print("    %-30s %5d %8.3f %9s %9s %10.3f%s"
                  % (r["test_smell"], r["n"], r["rho"], estat.formatar_p(r["p"]),
                     estat.formatar_p(r["p_ajustado"]), r["detectavel"], nota))

    sobrevivem = [r for r in principal if r["p_ajustado"] < 0.05]
    menor = min(principal, key=lambda r: r["p_ajustado"])
    acima = [r for r in principal if abs(r["rho"]) >= r["detectavel"]]
    print("\n  %d testes na familia; %d sobrevivem ao FDR; menor p ajustado %.3f (%s x %s)"
          % (len(principal), len(sobrevivem), menor["p_ajustado"], menor["code_smell"],
             menor["test_smell"]))
    print("  celulas com |rho| >= r detectavel: %d" % len(acima))

    print("\n  sensibilidade, fora da familia: Eager/Lazy SEM o filtro")
    sensibilidade = [celula(linhas, cs, ts, False)
                     for cs in c.CODE_SMELLS for ts in DEPENDEM_DA_PRODUCAO]
    for s in sensibilidade:
        p_ = [r for r in principal
              if r["code_smell"] == s["code_smell"] and r["test_smell"] == s["test_smell"]][0]
        print("    %-14s %-11s sem filtro %6.3f (N=%3d, p=%s)  ->  com filtro %6.3f (N=%3d)"
              % (s["code_smell"], s["test_smell"], s["rho"], s["n"],
                 estat.formatar_p(s["p"]), p_["rho"], p_["n"]))

    if args.csv:
        saida = []
        for r in principal:
            saida.append([args.ramo, "principal", r["code_smell"], r["test_smell"],
                          int(r["filtrado"]), r["n"], round(r["rho"], 6), round(r["p"], 6),
                          round(r["p_ajustado"], 6), round(r["lo"], 6), round(r["hi"], 6),
                          round(r["detectavel"], 6)])
        for r in sensibilidade:
            saida.append([args.ramo, "sensibilidade_sem_filtro", r["code_smell"],
                          r["test_smell"], 0, r["n"], round(r["rho"], 6), round(r["p"], 6),
                          "", round(r["lo"], 6), round(r["hi"], 6), round(r["detectavel"], 6)])
        destino = os.path.join(c.dados_de(__file__), "cruzado.csv")
        n = c.escrever_csv(destino,
                           ["ramo", "recorte", "code_smell", "test_smell",
                            "filtro_nome_divergente", "n", "rho", "p", "p_ajustado",
                            "ic_baixo", "ic_alto", "r_detectavel"], saida)
        print("\ncruzado.csv  %d linhas" % n)


if __name__ == "__main__":
    main()
