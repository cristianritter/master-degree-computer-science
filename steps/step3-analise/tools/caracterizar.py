"""Caracteriza as variaveis das duas tabelas do step 2, ANTES de qualquer teste estatistico.

Existe porque escolher o teste sem olhar a distribuicao e como escolher o binding sem
auditar: funciona ate alguem perguntar. O que este script responde:

  - qual a forma de cada variavel (zeros, assimetria, cauda)
  - se cabe teste parametrico ou se tem que ser nao-parametrico
  - se ha outlier capaz de dominar sozinho uma correlacao
  - se o test smell precisa ser normalizado por tamanho do teste
  - quanto o defeito de classe aninhada do step 1 contamina cada coluna

Nenhuma correlacao sai daqui. O objetivo e saber o que se pode perguntar, nao responder.

Uso:
    python caracterizar.py
    python caracterizar.py --ramo deterministico
    python caracterizar.py --csv        # grava dados/caracterizacao.csv
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c


def percentil(ordenados, p):
    if not ordenados:
        return float("nan")
    k = (len(ordenados) - 1) * p
    baixo, alto = math.floor(k), math.ceil(k)
    if baixo == alto:
        return ordenados[int(k)]
    return ordenados[baixo] * (alto - k) + ordenados[alto] * (k - baixo)


def resumo(valores):
    """Estatisticas descritivas sem depender de numpy/scipy."""
    n = len(valores)
    if n == 0:
        return None
    v = sorted(valores)
    media = sum(v) / n
    var = sum((x - media) ** 2 for x in v) / (n - 1) if n > 1 else 0.0
    dp = math.sqrt(var)
    # assimetria de Fisher-Pearson; > 1 ja indica cauda longa a direita
    if dp > 0 and n > 2:
        assim = (sum(((x - media) / dp) ** 3 for x in v) * n / ((n - 1) * (n - 2)))
    else:
        assim = 0.0
    return {
        "n": n,
        "zeros": sum(1 for x in v if x == 0),
        "media": media,
        "dp": dp,
        "min": v[0],
        "p25": percentil(v, 0.25),
        "mediana": percentil(v, 0.50),
        "p75": percentil(v, 0.75),
        "p95": percentil(v, 0.95),
        "max": v[-1],
        "assimetria": assim,
    }


def linha_resumo(nome, r):
    if r is None:
        return "    %-26s (sem dado)" % nome
    return ("    %-26s n=%4d  zeros=%5.1f%%  mediana=%8.2f  p95=%9.2f  max=%10.2f  assim=%6.2f"
            % (nome, r["n"], 100 * r["zeros"] / r["n"], r["mediana"], r["p95"], r["max"],
               r["assimetria"]))


def caracterizar(ramo, linhas_csv):
    print("\n" + "=" * 92)
    print("RAMO %s  -  %d arquivos de producao  -  precisao do binding %.1f%% (estrito)"
          % (ramo.upper(), len(linhas_csv), c.PRECISAO[ramo]["estrito"]))
    print("=" * 92)

    saida = []

    # ---- lado do code smell (variavel independente candidata) ----
    print("\n  CODE SMELL (rotulo continuo sev_media, 0 a 3):")
    for sm in c.CODE_SMELLS:
        vals = [c.num(r[c.coluna_cs(sm, "sev_media")]) for r in linhas_csv]
        vals = [v for v in vals if v is not None]
        r = resumo(vals)
        print(linha_resumo(sm, r))
        if r:
            saida.append([ramo, "code_smell", sm] + [r[k] for k in ORDEM])

    agregado = []
    for r in linhas_csv:
        v = [c.num(r[c.coluna_cs(sm, "sev_media")]) for sm in c.CODE_SMELLS]
        v = [x for x in v if x is not None]
        if v:
            agregado.append(max(v))
    r = resumo(agregado)
    print(linha_resumo("AGREGADO", r))
    if r:
        saida.append([ramo, "code_smell", "agregado"] + [r[k] for k in ORDEM])

    # ---- lado do test smell (variavel dependente candidata) ----
    print("\n  TEST SMELL (soma sobre as classes de teste ligadas):")
    for sm in c.SMELLS:
        col = c.coluna_ts(sm)
        vals = [c.num(r[col]) for r in linhas_csv]
        vals = [v for v in vals if v is not None]
        r = resumo(vals)
        print(linha_resumo(sm, r))
        if r:
            saida.append([ramo, "test_smell", sm] + [r[k] for k in ORDEM])

    for nome, col in (("TOTAL (ts_n_total)", "ts_n_total"),
                      ("DISTINTOS (ts_n_distintos)", "ts_n_distintos")):
        vals = [c.num(r[col]) for r in linhas_csv]
        vals = [v for v in vals if v is not None]
        r = resumo(vals)
        print(linha_resumo(nome, r))
        if r:
            saida.append([ramo, "test_smell", col] + [r[k] for k in ORDEM])

    # ---- tamanho do teste: o confundidor obvio ----
    print("\n  TAMANHO DO LADO DO TESTE (candidatos a confundidor):")
    for nome, col in (("n_testes ligados", "n_testes"),
                      ("LOC de teste", "loc_teste"),
                      ("metodos de teste", "n_metodos_teste")):
        vals = [c.num(r[col]) for r in linhas_csv]
        vals = [v for v in vals if v is not None]
        r = resumo(vals)
        print(linha_resumo(nome, r))
        if r:
            saida.append([ramo, "tamanho", col] + [r[k] for k in ORDEM])

    # ---- contaminacao pelo defeito de classe aninhada ----
    div = sum(1 for r in linhas_csv if c.num(r["n_testes_nome_divergente"]))
    print("\n  DEFEITO DE CLASSE ANINHADA (step 1, secao 5):")
    print("    arquivos com ao menos um teste nome_divergente: %d de %d (%.1f%%)"
          % (div, len(linhas_csv), 100 * div / len(linhas_csv)))
    print("    -> Eager Test e Lazy Test nao sao confiaveis nessas linhas;")
    print("       filtrar ou estratificar por n_testes_nome_divergente e obrigatorio")

    # ---- estratos do MLCQ ----
    print("\n  ESTRATOS DE EVIDENCIA DOS REVISORES:")
    conta = {}
    for r in linhas_csv:
        for e in (r["estratos"] or "").split("|"):
            if e:
                conta[e] = conta.get(e, 0) + 1
    for e in sorted(conta, key=lambda x: -conta[x]):
        print("    %-24s %5d  (%.1f%%)" % (e, conta[e], 100 * conta[e] / len(linhas_csv)))

    return saida


ORDEM = ["n", "zeros", "media", "dp", "min", "p25", "mediana", "p75", "p95", "max",
         "assimetria"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ramo", choices=sorted(c.RAMOS), action="append",
                    help="repetivel; padrao: os dois")
    ap.add_argument("--csv", action="store_true",
                    help="grava dados/caracterizacao.csv com tudo que foi impresso")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    todas = []
    for ramo in (args.ramo or sorted(c.RAMOS)):
        todas += caracterizar(ramo, c.ler_ramo(ramo))

    print("\n" + "=" * 92)
    print("LEITURA: assimetria alta e proporcao grande de zeros descartam teste")
    print("parametrico. O que cabe e Spearman, ou um modelo que trate o excesso de zeros.")
    print("=" * 92)

    if args.csv:
        destino = os.path.join(c.DADOS, "caracterizacao.csv")
        n = c.escrever_csv(destino, ["ramo", "lado", "variavel"] + ORDEM, todas)
        print("\ncaracterizacao.csv  %d linhas" % n)


if __name__ == "__main__":
    main()
