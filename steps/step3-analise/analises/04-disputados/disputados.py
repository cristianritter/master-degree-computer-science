"""Analise 3: entre as amostras SINALIZADAS, o test smell prediz quais a maioria confirmou?

Esta comparacao tem uma propriedade que nenhuma das anteriores tem: ela **neutraliza a
circularidade do desenho amostral do MLCQ**.

O problema, do step 2, secao 3: revisores extras foram alocados so para amostras que
alguem ja havia marcado como positiva. Por isso "alguem marcou > none" e quase um detector
de "esta amostra foi ao crosscheck", e o numero de revisores e consequencia do rotulo, nao
evidencia independente dele.

Os dois grupos aqui passaram pelo mesmo funil:

  positivo_confiavel   alguem sinalizou E a maioria confirmou
  disputado            alguem sinalizou E a maioria NAO confirmou

Os dois foram sinalizados. Os dois foram ao crosscheck. O roteamento e o mesmo, entao a
diferenca entre eles nao pode ser explicada por ele - e o que sobra e o veredito do
crosscheck, que e exatamente o julgamento que o MLCQ coletou para decidir os casos
duvidosos.

E a comparacao menos circular que este dataset permite. Se houver relacao entre qualidade
do teste e code smell, e aqui que ela tem a melhor chance de aparecer limpa.

Contrapartida: o N e pequeno (42 contra 160 no ramo deterministico), entao so um efeito
grande seria detectavel. O script imprime o efeito minimo detectavel junto do resultado,
para que um nulo nao seja lido como ausencia quando for falta de poder.

Uso:
    python disputados.py
    python disputados.py --ramo deterministico --csv
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "tools"))
import comum as c
import estat
from variaveis import desfechos, estrato_unico


def delta_detectavel(n1, n2, alfa=0.05, poder=0.80):
    """Menor r bisserial de postos detectavel, via aproximacao normal do Mann-Whitney."""
    if n1 < 5 or n2 < 5:
        return float("nan")
    za = 1.959964
    zb = 0.841621
    # var(U) ~ n1*n2*(n+1)/12; delta = (U1-U2)/(n1*n2) -> ep(delta) = sqrt((n+1)/(3*n1*n2))
    ep = math.sqrt((n1 + n2 + 1.0) / (3.0 * n1 * n2))
    return (za + zb) * ep


def rodar(ramo, linhas, saida):
    conf = [r for r in linhas if estrato_unico(r) == "positivo_confiavel"]
    disp = [r for r in linhas if estrato_unico(r) == "disputado"]

    print("\n" + "=" * 88)
    print("RAMO %s" % ramo.upper())
    print("=" * 88)
    print("  confirmados pela maioria : %d" % len(conf))
    print("  sinalizados e NAO confirmados : %d" % len(disp))
    print("  os dois grupos passaram pelo mesmo roteamento de crosscheck")

    print("\n  %-12s %7s %7s %10s %10s %9s %9s %12s"
          % ("desfecho", "N conf", "N disp", "mediana+", "mediana-", "delta", "p",
             "detectavel"))
    resultados = []
    for chave in ("bruto", "densidade", "distintos"):
        a = [desfechos(r) for r in conf]
        b = [desfechos(r) for r in disp]
        a = [d[chave] for d in a if d is not None and d[chave] is not None]
        b = [d[chave] for d in b if d is not None and d[chave] is not None]
        if len(a) < 5 or len(b) < 5:
            print("  %-12s (grupo pequeno demais)" % chave)
            continue
        u, p, delta, n1, n2 = estat.mannwhitney(a, b)
        med_a = sorted(a)[len(a) // 2]
        med_b = sorted(b)[len(b) // 2]
        det = delta_detectavel(n1, n2)
        print("  %-12s %7d %7d %10.3f %10.3f %9.3f %9s %12.3f"
              % (chave, n1, n2, med_a, med_b, delta, estat.formatar_p(p), det))
        resultados.append({"desfecho": chave, "n1": n1, "n2": n2, "med_conf": med_a,
                           "med_disp": med_b, "delta": delta, "p": p, "detectavel": det})

    if resultados:
        ajustados = estat.benjamini_hochberg([r["p"] for r in resultados])
        for r, pa in zip(resultados, ajustados):
            r["p_ajustado"] = pa
        print("  p ajustado por FDR: %s"
              % ", ".join("%s=%s" % (r["desfecho"], estat.formatar_p(r["p_ajustado"]))
                          for r in resultados))
        print("  'detectavel' e o menor delta que este N acharia com 80% de poder:")
        print("  delta observado abaixo dele significa que o teste nao tinha como decidir.")

    for r in resultados:
        saida.append([ramo, r["desfecho"], r["n1"], r["n2"], round(r["med_conf"], 4),
                      round(r["med_disp"], 4), round(r["delta"], 6), round(r["p"], 6),
                      round(r["p_ajustado"], 6), round(r["detectavel"], 6)])
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

    print("ANALISE 3 - confirmados x disputados, ambos sinalizados")
    print("A comparacao menos circular deste dataset: o roteamento do crosscheck e o mesmo")
    print("nos dois grupos, entao ele nao pode explicar a diferenca.")

    saida = []
    for ramo in (args.ramo or sorted(c.RAMOS)):
        rodar(ramo, c.ler_ramo(ramo), saida)

    if args.csv:
        destino = os.path.join(c.dados_de(__file__), "disputados.csv")
        n = c.escrever_csv(destino,
                           ["ramo", "desfecho", "n_confirmado", "n_disputado",
                            "mediana_confirmado", "mediana_disputado", "delta", "p",
                            "p_ajustado", "delta_detectavel"], saida)
        print("\ndisputados.csv  %d linhas" % n)


if __name__ == "__main__":
    main()
