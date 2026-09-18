"""Analise 1: cada um dos 13 test smells isoladamente, contra o code smell da classe.

Ate aqui o desfecho foi sempre agregado - ts_n_total e ts_n_distintos. A pergunta desta
rodada e outra: **algum smell especifico se comporta diferente do conjunto?** E plausivel
que sim. Eager Test e Lazy Test dependem da classe de producao para serem detectados;
Assertion Roulette e Verbose Test sao propriedades internas do teste. Se houver relacao
com code smell, ela tem mais razao de aparecer nos primeiros.

Duas colunas por smell, pelo motivo da rodada anterior:

  bruto       contagem de ocorrencias         sensivel ao tamanho do teste
  densidade   contagem / n_metodos_teste      normalizado

E o ajuste para comparacoes multiplas entra aqui de verdade: sao 26 testes de uma vez, e
alfa 0,05 por teste deixaria ~1,3 falsos positivos esperados. O p ajustado por
Benjamini-Hochberg (FDR) e reportado ao lado do bruto.

**Eager Test e Lazy Test nao sao confiaveis nas linhas com nome_divergente** (step 1,
secao 5: caem 28x e 23x). Por isso o script roda tambem a versao filtrada, e a diferenca
entre as duas e informacao.

Uso:
    python por_test_smell.py
    python por_test_smell.py --ramo deterministico --csv
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "tools"))
import comum as c
import estat
from variaveis import rotulo_agregado


def series(linhas, smell, normalizar):
    """Pares (test smell deste tipo, code smell agregado), descartando linha incompleta."""
    col = c.coluna_ts(smell)
    x, y, tam = [], [], []
    for r in linhas:
        v = c.num(r[col])
        lab = rotulo_agregado(r)
        met = c.num(r["n_metodos_teste"])
        if v is None or lab is None or met is None:
            continue
        if normalizar:
            if not met:
                continue
            v = v / met
        x.append(v)
        y.append(lab)
        tam.append(met)
    return x, y, tam


def rodar(linhas, titulo_bloco):
    print("\n  %s" % titulo_bloco)
    print("    %-30s %6s %8s %9s %9s %9s"
          % ("test smell", "N", "rho", "p", "p ajust.", "zeros"))
    resultados = []
    for smell in c.SMELLS:
        for normalizar in (False, True):
            x, y, _ = series(linhas, smell, normalizar)
            if len(x) < 10:
                continue
            rho, p, lo, hi, n = estat.spearman(x, y)
            zeros = 100.0 * sum(1 for v in x if v == 0) / len(x)
            resultados.append({
                "smell": smell, "desfecho": "densidade" if normalizar else "bruto",
                "n": n, "rho": rho, "p": p, "lo": lo, "hi": hi, "zeros": zeros,
            })

    ajustados = estat.benjamini_hochberg([r["p"] for r in resultados])
    for r, pa in zip(resultados, ajustados):
        r["p_ajustado"] = pa
        marca = " *" if pa < 0.05 else ("  ." if r["p"] < 0.05 else "")
        print("    %-22s %-7s %6d %8.3f %9s %9s %8.1f%%%s"
              % (r["smell"], r["desfecho"], r["n"], r["rho"],
                 estat.formatar_p(r["p"]), estat.formatar_p(pa), r["zeros"], marca))
    print("    (* sobrevive ao ajuste FDR; . significativo so sem ajuste)")
    return resultados


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
    print("=" * 92)
    print("ANALISE 1 - cada test smell isolado  |  ramo %s, %d arquivos"
          % (args.ramo, len(linhas)))
    print("Spearman contra code smell agregado (sev_media). p ajustado por FDR.")
    print("=" * 92)

    todos = rodar(linhas, "todas as linhas")

    limpas = [r for r in linhas if not c.num(r["n_testes_nome_divergente"])]
    print("\n  -- filtrando as linhas com teste nome_divergente: %d de %d ficam --"
          % (len(limpas), len(linhas)))
    filtrados = rodar(limpas, "so linhas sem o defeito de classe aninhada")

    print("\n  o filtro muda o resultado de Eager/Lazy Test?")
    for smell in ("Eager Test", "Lazy Test", "General Fixture"):
        a = [r for r in todos if r["smell"] == smell and r["desfecho"] == "densidade"][0]
        b = [r for r in filtrados if r["smell"] == smell and r["desfecho"] == "densidade"][0]
        print("    %-18s densidade: %.3f (N=%d)  ->  %.3f (N=%d)"
              % (smell, a["rho"], a["n"], b["rho"], b["n"]))
    print("    General Fixture e o controle: nao depende da classe de producao,")
    print("    entao nao deveria mudar com o filtro (step 1, secao 5).")

    if args.csv:
        linhas_csv = []
        for conjunto, nome in ((todos, "todas"), (filtrados, "sem_nome_divergente")):
            for r in conjunto:
                linhas_csv.append([args.ramo, nome, r["smell"], r["desfecho"], r["n"],
                                   round(r["rho"], 6), round(r["p"], 6),
                                   round(r["p_ajustado"], 6), round(r["lo"], 6),
                                   round(r["hi"], 6), round(r["zeros"], 2)])
        destino = os.path.join(c.dados_de(__file__), "por_test_smell.csv")
        n = c.escrever_csv(destino,
                           ["ramo", "recorte", "test_smell", "desfecho", "n", "rho", "p",
                            "p_ajustado", "ic_baixo", "ic_alto", "zeros_pct"], linhas_csv)
        print("\npor_test_smell.csv  %d linhas" % n)


if __name__ == "__main__":
    main()
