"""Calcula o poder estatistico que cada decisao de desenho deixa disponivel para o step 3.

    qual ramo de binding usar     (deterministico x ampliado)
    qual regra de rotulo usar     (any, any_major, maioria, unanime, sev_media)
    por smell ou agregado

Nao roda analise nenhuma: so responde "com este N e esta prevalencia, qual e o menor efeito
que a etapa 3 conseguiria detectar". E o numero que separa "nao ha relacao" de "nao da para
saber", e por isso precisa ser calculado ANTES de olhar qualquer resultado - depois, vira
justificativa.

Convencoes, todas declaradas de proposito:

  alfa = 0,05 bicaudal, poder = 80%     o padrao da area; mudar em --alfa/--poder
  correlacao continua    z de Fisher: n = ((z_a + z_b) / z_r)^2 + 3, invertido para r
  comparacao de grupos   d = (z_a + z_b) * raiz(1/n1 + 1/n2), em desvios-padrao
  r equivalente          converte d em r ponto-bisserial, para comparar as duas escalas

As formulas assumem normalidade e sao aproximacoes: um teste nao-parametrico (Spearman,
Mann-Whitney) precisa de ~5% a mais de amostra para o mesmo poder. Como a diferenca entre
as opcoes aqui e de 2x a 10x, a aproximacao nao muda nenhuma conclusao - mas o artigo deve
dizer que sao aproximacoes.

Uso:
    python poder_analise.py
    python poder_analise.py --poder 0.9
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

RAMOS = [
    ("deterministico", "analise_deterministico.csv"),
    ("ampliado", "analise_ampliado.csv"),
]

REGRAS = ["any", "any_major", "maioria", "unanime"]


def z(p):
    """Quantil da normal padrao, por bissecao - evita depender de scipy."""
    lo, hi = -10.0, 10.0
    for _ in range(200):
        meio = (lo + hi) / 2
        # funcao de distribuicao acumulada via erf
        acum = 0.5 * (1 + math.erf(meio / math.sqrt(2)))
        if acum < p:
            lo = meio
        else:
            hi = meio
    return (lo + hi) / 2


def r_detectavel(n, alfa, poder):
    """Menor correlacao detectavel com n observacoes."""
    if n <= 4:
        return float("nan")
    soma = z(1 - alfa / 2) + z(poder)
    return math.tanh(math.sqrt(soma ** 2 / (n - 3)))


def d_detectavel(n1, n2, alfa, poder):
    """Menor diferenca padronizada detectavel entre dois grupos."""
    if n1 < 2 or n2 < 2:
        return float("nan")
    return (z(1 - alfa / 2) + z(poder)) * math.sqrt(1.0 / n1 + 1.0 / n2)


def d_para_r(d, p):
    """d de Cohen -> r ponto-bisserial, dada a proporcao p do grupo positivo."""
    if math.isnan(d):
        return float("nan")
    return d * math.sqrt(p * (1 - p)) / math.sqrt(d * d * p * (1 - p) + 1)


def coluna(smell, sufixo):
    return "cs_%s_%s" % (smell.replace(" ", "_"), sufixo)


def por_smell(linhas, smells, alfa, poder):
    print("  por code smell (rotulo continuo sev_media):")
    print("    %-14s %6s %10s %8s   %s" % ("smell", "N", "sev media", "N>0", "r detectavel"))
    for sm in smells:
        col = coluna(sm, "sev_media")
        vals = [float(r[col]) for r in linhas if (r[col] or "").strip()]
        if not vals:
            print("    %-14s %6s" % (sm, "-"))
            continue
        nz = sum(1 for v in vals if v > 0)
        print("    %-14s %6d %10.3f %8d   %.3f"
              % (sm, len(vals), sum(vals) / len(vals), nz,
                 r_detectavel(len(vals), alfa, poder)))


def agregado(linhas, smells, alfa, poder):
    """O smell avaliado de cada arquivo, qualquer que seja ele.

    O MLCQ anota cada amostra para UM smell, entao o N por smell e pequeno por construcao.
    Quase todo arquivo tem exatamente um smell avaliado, e a analise agregada recupera o N
    inteiro do ramo sem misturar avaliacoes: e a alavanca de poder mais barata que existe
    aqui, e nao custa nada em construto.
    """
    vals = []
    for r in linhas:
        v = [float(r[coluna(sm, "sev_media")]) for sm in smells
             if (r[coluna(sm, "sev_media")] or "").strip()]
        if v:
            vals.append(max(v))
    if not vals:
        return
    nz = sum(1 for v in vals if v > 0)
    print("\n  agregado (severidade do smell avaliado, qualquer que seja):")
    print("    N = %d | media %.3f | acima de zero %d (%.1f%%) | maximo %.2f"
          % (len(vals), sum(vals) / len(vals), nz, 100 * nz / len(vals), max(vals)))
    print("    r detectavel = %.3f" % r_detectavel(len(vals), alfa, poder))


def por_regra(linhas, smells, alfa, poder):
    """O que cada regra de rotulo custa em poder, no agregado do ramo."""
    print("\n  por regra de rotulo (agregado, dicotomizado):")
    print("    %-12s %10s %10s %8s   %s" % ("regra", "avaliados", "positivos", "prev.",
                                            "efeito minimo detectavel"))
    for regra in REGRAS:
        n = pos = 0
        for r in linhas:
            v = [r[coluna(sm, regra)] for sm in smells if (r[coluna(sm, regra)] or "").strip()]
            if v:
                n += 1
                pos += 1 if any(x == "1" for x in v) else 0
        if not n:
            continue
        neg = n - pos
        d = d_detectavel(pos, neg, alfa, poder)
        if math.isnan(d):
            txt = "grupo pequeno demais para comparar"
        else:
            txt = "d >= %.2f   (r equivalente ~%.2f)" % (d, d_para_r(d, pos / n))
        print("    %-12s %10d %10d %7.1f%%   %s" % (regra, n, pos, 100 * pos / n, txt))

    # a continua, na mesma tabela, para a comparacao ser direta
    vals = []
    for r in linhas:
        v = [float(r[coluna(sm, "sev_media")]) for sm in smells
             if (r[coluna(sm, "sev_media")] or "").strip()]
        if v:
            vals.append(max(v))
    if vals:
        print("    %-12s %10d %10s %8s   r >= %.3f"
              % ("sev_media", len(vals), "-", "-", r_detectavel(len(vals), alfa, poder)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alfa", type=float, default=0.05)
    ap.add_argument("--poder", type=float, default=0.80)
    args = ap.parse_args()

    smells = sorted(c.CODE_SMELLS)
    print("alfa = %.3f bicaudal | poder = %.0f%%" % (args.alfa, 100 * args.poder))
    print("as formulas sao aproximacoes normais; teste nao-parametrico pede ~5% a mais de N")

    for nome, arquivo in RAMOS:
        caminho = os.path.join(c.DADOS, arquivo)
        if not os.path.exists(caminho):
            print("\n=== %s: %s ausente (rode gerar_analises.py) ===" % (nome, arquivo))
            continue
        linhas = c.ler_csv(caminho)
        print("\n" + "=" * 74)
        print("RAMO %s  -  %s  (%d arquivos de producao)" % (nome.upper(), arquivo, len(linhas)))
        print("=" * 74)
        por_smell(linhas, smells, args.alfa, args.poder)
        agregado(linhas, smells, args.alfa, args.poder)
        por_regra(linhas, smells, args.alfa, args.poder)


if __name__ == "__main__":
    main()
