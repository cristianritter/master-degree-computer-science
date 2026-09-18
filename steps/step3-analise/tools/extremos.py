"""Analise 2: comparar os extremos de evidencia, em vez de correlacionar a escala inteira.

A correlacao pressupoe relacao monotonica ao longo de toda a faixa de severidade. O
desenho do MLCQ nao sustenta bem isso - a severidade media e continua, mas vem de um
processo de rotulagem circular com o crosscheck (step 2, secao 3).

O que o desenho sustenta melhor e a comparacao dos extremos que o proprio step 2 definiu:

  positivo_confiavel   a maioria dos revisores marcou > none
  negativo_confiavel   2+ revisores, nenhum marcou > none

O estrato negativo e especialmente forte neste dataset: pelo desenho amostral, qualquer
flag teria escalado a amostra para mais revisores. Sao negativos com corroboracao, coisa
rara em dataset de code smell.

A pergunta fica direta: **classes que os revisores concordaram ter code smell tem testes
com mais test smell que classes que eles concordaram nao ter?** Mann-Whitney, que nao
supoe distribuicao e lida com os 72% de zeros.

O tamanho de efeito reportado e o r bisserial de postos (delta): a probabilidade de um
arquivo do grupo positivo ter mais test smell que um do negativo, menos a probabilidade do
contrario. Zero significa nenhuma separacao entre os grupos.

Uso:
    python extremos.py
    python extremos.py --ramo ampliado --csv
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c
import estat
import explorar as ex

EXTREMOS = ("positivo_confiavel", "negativo_confiavel")


def grupo_de(linha):
    """O estrato do arquivo, so quando ele e inequivoco.

    Um arquivo com varias amostras pode cair em mais de um estrato; esses ficam de fora,
    porque classifica-lo exigiria uma regra de desempate que seria mais uma decisao
    escondida.
    """
    estratos = {e for e in (linha["estratos"] or "").split("|") if e}
    if len(estratos) != 1:
        return None
    unico = estratos.pop()
    return unico if unico in EXTREMOS else None


def desfecho_de(linha, chave):
    d = ex.desfechos(linha)
    if d is None:
        return None
    return d.get(chave)


def rodar(ramo, linhas, csv_saida):
    pos = [r for r in linhas if grupo_de(r) == "positivo_confiavel"]
    neg = [r for r in linhas if grupo_de(r) == "negativo_confiavel"]
    ambiguos = sum(1 for r in linhas if grupo_de(r) is None)

    print("\n" + "=" * 88)
    print("RAMO %s  -  positivo_confiavel: %d   negativo_confiavel: %d   fora: %d"
          % (ramo.upper(), len(pos), len(neg), ambiguos))
    print("=" * 88)
    print("  (fora = arquivo com amostras de mais de um estrato, ou de estrato intermediario)")

    print("\n  %-12s %7s %7s %10s %10s %9s %9s"
          % ("desfecho", "N pos", "N neg", "mediana+", "mediana-", "delta", "p"))
    resultados = []
    for chave in ("bruto", "densidade", "distintos"):
        a = [desfecho_de(r, chave) for r in pos]
        b = [desfecho_de(r, chave) for r in neg]
        a = [v for v in a if v is not None]
        b = [v for v in b if v is not None]
        if len(a) < 5 or len(b) < 5:
            print("  %-12s (grupo pequeno demais)" % chave)
            continue
        u, p, delta, n1, n2 = estat.mannwhitney(a, b)
        med_a = sorted(a)[len(a) // 2]
        med_b = sorted(b)[len(b) // 2]
        resultados.append({"desfecho": chave, "n1": n1, "n2": n2, "med_pos": med_a,
                           "med_neg": med_b, "delta": delta, "p": p})
        print("  %-12s %7d %7d %10.3f %10.3f %9.3f %9s"
              % (chave, n1, n2, med_a, med_b, delta, estat.formatar_p(p)))

    if resultados:
        ajustados = estat.benjamini_hochberg([r["p"] for r in resultados])
        for r, pa in zip(resultados, ajustados):
            r["p_ajustado"] = pa
        print("  p ajustado por FDR: %s"
              % ", ".join("%s=%s" % (r["desfecho"], estat.formatar_p(r["p_ajustado"]))
                          for r in resultados))

    for r in resultados:
        csv_saida.append([ramo, r["desfecho"], r["n1"], r["n2"], round(r["med_pos"], 4),
                          round(r["med_neg"], 4), round(r["delta"], 6), round(r["p"], 6),
                          round(r["p_ajustado"], 6)])
    return resultados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ramo", choices=sorted(c.RAMOS), action="append")
    ap.add_argument("--csv", action="store_true")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("ANALISE 2 - extremos de evidencia dos revisores, por Mann-Whitney")
    print("delta = r bisserial de postos; 0 significa nenhuma separacao entre os grupos")

    saida = []
    for ramo in (args.ramo or sorted(c.RAMOS)):
        rodar(ramo, c.ler_ramo(ramo), saida)

    if args.csv:
        destino = os.path.join(c.DADOS, "extremos.csv")
        n = c.escrever_csv(destino,
                           ["ramo", "desfecho", "n_positivo", "n_negativo",
                            "mediana_positivo", "mediana_negativo", "delta", "p",
                            "p_ajustado"], saida)
        print("\nextremos.csv  %d linhas" % n)


if __name__ == "__main__":
    main()
