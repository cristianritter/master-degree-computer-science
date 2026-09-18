"""Primeira rodada exploratoria: test smell contra code smell, por Spearman.

A caracterizacao (secao 2 do README) deixou duas coisas decididas e uma em aberto:

  decidido   o teste e nao-parametrico (72% de zeros, assimetria ate 21)
  decidido   o rotulo e sev_media continuo, agregado (step 2, secao 12)
  EM ABERTO  como tratar o tamanho do teste, que nao esta controlado

Este script ataca o que ficou em aberto rodando as tres definicoes de desfecho lado a lado,
para que a escolha seja feita com o resultado das tres a vista:

  bruto       ts_n_total, a soma das ocorrencias        sensivel a tamanho
  densidade   ts_n_total / n_metodos_teste              normalizado por tamanho
  distintos   ts_n_distintos, quantos dos 13 aparecem   pouco sensivel a tamanho

E imprime, junto, a correlacao de cada desfecho com o proprio tamanho do teste: se o bruto
correlaciona forte com tamanho e os outros nao, o tamanho esta mandando no resultado, e
isso ja e achado.

A correlacao parcial fecha a pergunta: sobra relacao depois de descontar o tamanho?

Uso:
    python explorar.py
    python explorar.py --ramo deterministico
    python explorar.py --por-smell        # abre por code smell, com N menor
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c
import estat


def desfechos(linha):
    """As tres definicoes de 'quanto test smell tem o teste desta classe'."""
    total = c.num(linha["ts_n_total"])
    metodos = c.num(linha["n_metodos_teste"])
    distintos = c.num(linha["ts_n_distintos"])
    if total is None or distintos is None:
        return None
    return {
        "bruto": total,
        "densidade": total / metodos if metodos else None,
        "distintos": distintos,
    }


def rotulo_agregado(linha):
    """Severidade do smell avaliado no arquivo, qualquer que seja ele."""
    v = [c.num(linha[c.coluna_cs(sm, "sev_media")]) for sm in c.CODE_SMELLS]
    v = [x for x in v if x is not None]
    return max(v) if v else None


def pares(linhas, chave_desfecho, rotulo):
    x, y, tam = [], [], []
    for r in linhas:
        d = desfechos(r)
        lab = rotulo(r)
        met = c.num(r["n_metodos_teste"])
        if d is None or lab is None or d[chave_desfecho] is None or met is None:
            continue
        x.append(d[chave_desfecho])
        y.append(lab)
        tam.append(met)
    return x, y, tam


def bloco(nome, linhas, rotulo, sufixo=""):
    print("\n  %s%s" % (nome, sufixo))
    print("    %-11s %6s %8s %9s %20s   %s"
          % ("desfecho", "N", "rho", "p", "IC95%", "rho com tamanho"))
    saida = []
    for chave in ("bruto", "densidade", "distintos"):
        x, y, tam = pares(linhas, chave, rotulo)
        if len(x) < 10:
            print("    %-11s %6d  (N insuficiente)" % (chave, len(x)))
            continue
        rho, p, lo, hi, n = estat.spearman(x, y)
        rho_tam, _, _, _, _ = estat.spearman(x, tam)
        print("    %-11s %6d %8.3f %9s   [%6.3f, %6.3f]   %6.3f"
              % (chave, n, rho, estat.formatar_p(p), lo, hi, rho_tam))
        saida.append([chave, n, rho, p, lo, hi, rho_tam])
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ramo", choices=sorted(c.RAMOS), action="append")
    ap.add_argument("--por-smell", action="store_true")
    ap.add_argument("--csv", action="store_true")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("Spearman sobre postos, IC95% por z de Fisher, p bicaudal.")
    print("O rotulo e sev_media continuo. Nenhum ajuste para comparacoes multiplas ainda;")
    print("a contagem de testes rodados esta no caderno da secao 4 do README.")

    tudo = []
    for ramo in (args.ramo or sorted(c.RAMOS)):
        linhas = c.ler_ramo(ramo)
        print("\n" + "=" * 88)
        print("RAMO %s  -  %d arquivos  -  precisao %.1f%% (estrito)"
              % (ramo.upper(), len(linhas), c.PRECISAO[ramo]["estrito"]))
        print("=" * 88)

        for l in bloco("code smell agregado", linhas, rotulo_agregado):
            tudo.append([ramo, "agregado"] + l)

        # sobra relacao depois de descontar o tamanho do teste?
        print("\n  correlacao parcial, controlando n_metodos_teste:")
        for chave in ("bruto", "distintos"):
            x, y, tam = pares(linhas, chave, rotulo_agregado)
            r, p, n = estat.parcial(x, y, tam)
            print("    %-11s N=%d  rho parcial=%.3f  p=%s"
                  % (chave, n, r, estat.formatar_p(p)))

        if args.por_smell:
            for sm in c.CODE_SMELLS:
                def rot(linha, sm=sm):
                    return c.num(linha[c.coluna_cs(sm, "sev_media")])
                for l in bloco("code smell: %s" % sm, linhas, rot):
                    tudo.append([ramo, sm] + l)

    if args.csv:
        destino = os.path.join(c.DADOS, "exploracao.csv")
        n = c.escrever_csv(destino,
                           ["ramo", "code_smell", "desfecho", "n", "rho", "p",
                            "ic_baixo", "ic_alto", "rho_com_tamanho"], tudo)
        print("\nexploracao.csv  %d linhas" % n)


if __name__ == "__main__":
    main()
