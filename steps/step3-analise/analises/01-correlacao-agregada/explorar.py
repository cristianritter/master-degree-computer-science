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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "tools"))
import comum as c
import estat
from variaveis import desfechos, pares, rotulo_agregado


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
        saida.append(["simples", chave, n, rho, p, lo, hi, rho_tam])
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

        print("")
        print("  correlacao parcial, controlando n_metodos_teste:")
        for chave in ("bruto", "densidade", "distintos"):
            x, y, tam = pares(linhas, chave, rotulo_agregado)
            r, pv, n = estat.parcial(x, y, tam)
            print("    %-11s N=%d  rho parcial=%.3f  p=%s"
                  % (chave, n, r, estat.formatar_p(pv)))
            tudo.append([ramo, "agregado", "parcial", chave, n, r, pv, "", "", ""])

        # o mecanismo da confusao: as outras duas pernas do triangulo. Se code smell
        # correlaciona com tamanho do teste E test smell bruto tambem, a correlacao bruta
        # entre os dois aparece sem que exista relacao com qualidade do teste.
        print("")
        print("  o confundidor, medido:")
        validos = [r for r in linhas if rotulo_agregado(r) is not None
                   and c.num(r["n_metodos_teste"]) is not None]
        rot = [rotulo_agregado(r) for r in validos]
        for nome, serie in (("code smell x n_metodos_teste",
                             [c.num(r["n_metodos_teste"]) for r in validos]),
                            ("code smell x loc_teste",
                             [c.num(r["loc_teste"]) for r in validos])):
            rho, pv, lo, hi, n = estat.spearman(rot, serie)
            print("    %-30s rho=%6.3f  p=%s" % (nome, rho, estat.formatar_p(pv)))
            tudo.append([ramo, "agregado", "confundidor", nome, n, rho, pv, lo, hi, ""])

        if args.por_smell:
            for sm in c.CODE_SMELLS:
                def rot(linha, sm=sm):
                    return c.num(linha[c.coluna_cs(sm, "sev_media")])
                for l in bloco("code smell: %s" % sm, linhas, rot):
                    tudo.append([ramo, sm] + l)

    if args.csv:
        destino = os.path.join(c.dados_de(__file__), "exploracao.csv")
        arredondado = [[x if isinstance(x, str) or isinstance(x, int)
                        else ("" if x == "" else round(x, 6)) for x in linha]
                       for linha in tudo]
        n = c.escrever_csv(destino,
                           ["ramo", "code_smell", "analise", "desfecho", "n", "rho", "p",
                            "ic_baixo", "ic_alto", "rho_com_tamanho"], arredondado)
        print("\nexploracao.csv  %d linhas" % n)


if __name__ == "__main__":
    main()
