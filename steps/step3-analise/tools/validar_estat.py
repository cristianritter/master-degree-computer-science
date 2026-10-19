"""Confere as implementacoes do estat.py contra o scipy, nos dados reais das analises.

O estat.py implementa Spearman, Mann-Whitney e Benjamini-Hochberg na biblioteca padrao,
para que reproduzir o step 3 nao exija montar ambiente. O preco e que um erro nessas
formulas contaminaria todas as analises sem que nenhum conferidor percebesse: os
conferidores reapuram o que o estat.py calcula, nao se ele calcula certo.

Este script recalcula com o scipy, a partir das tabelas do step 2 lidas pelo pandas (sem
passar por variaveis.py), e compara com os CSVs que as analises gravaram:

  01  rho e p de bruto, densidade e distintos x rotulo agregado, nos dois ramos
  02  rho e p de cada test smell (bruto e densidade), e o p ajustado de cada recorte
  03  delta e p do Mann-Whitney de confirmados x limpos
  05  rho e p de cada celula code smell x test smell, e o p ajustado da familia

O rho tem que bater na sexta casa. O p do estat.py sai da transformacao z de Fisher e o do
scipy da distribuicao t; a diferenca entre os dois tem que ficar abaixo de TOL_P. O
scipy e dependencia so deste script: as analises continuam sem ela.

Uso:
    python tools/validar_estat.py      # codigo 1 se algo divergir
"""
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

A = os.path.join(c.STEP, "analises")
TOL_RHO = 1e-6
TOL_P = 0.005
TOL_BH = 1e-4     # o CSV grava p com 6 casas, e o BH multiplica esse erro por ate m
CODE = ["blob", "data_class", "feature_envy", "long_method"]
DEPENDEM = ("Eager Test", "Lazy Test")

falhas = []


def confere(rotulo, esperado, obtido, tol):
    if pd.isna(esperado) and pd.isna(obtido):
        return 0.0
    dif = abs(float(esperado) - float(obtido))
    if not dif <= tol:
        falhas.append("%s: analise %.6f, scipy %.6f" % (rotulo, esperado, obtido))
    return dif


def ramo(nome):
    d = pd.read_csv(c.RAMOS[nome], encoding="utf-8-sig")
    sev = d[["cs_%s_sev_media" % s for s in CODE]]
    d["rotulo"] = sev.max(axis=1, skipna=True)
    d["densidade"] = d["ts_n_total"] / d["n_metodos_teste"].replace(0, np.nan)
    return d


def spearman(x, y):
    m = x.notna() & y.notna()
    if m.sum() < 10 or x[m].nunique() < 2:
        return np.nan, np.nan, int(m.sum())
    r = stats.spearmanr(x[m], y[m])
    return r.statistic, r.pvalue, int(m.sum())


def bh(ps):
    ps = np.asarray(ps, dtype=float)
    out = np.full(len(ps), np.nan)
    ok = ~np.isnan(ps)
    out[ok] = stats.false_discovery_control(ps[ok])
    return out


def analise01():
    ex = pd.read_csv(os.path.join(A, "01-correlacao-agregada", "dados", "exploracao.csv"))
    ex = ex[(ex.code_smell == "agregado") & (ex.analise == "simples")]
    maior = 0.0
    for nome in c.RAMOS:
        d = ramo(nome)
        for desf, col in (("bruto", "ts_n_total"), ("densidade", "densidade"),
                          ("distintos", "ts_n_distintos")):
            rho, p, n = spearman(d[col], d.rotulo)
            linha = ex[(ex.ramo == nome) & (ex.desfecho == desf)].iloc[0]
            confere("01 %s %s rho" % (nome, desf), linha.rho, rho, TOL_RHO)
            maior = max(maior, confere("01 %s %s p" % (nome, desf), linha.p, p, TOL_P))
    return "01: 6 correlacoes; maior diferenca de p %.4f" % maior


def analise02():
    pt = pd.read_csv(os.path.join(A, "02-por-test-smell", "dados", "por_test_smell.csv"))
    d = ramo("deterministico")
    fam = pt[pt.recorte != "sensibilidade_caminho_exato"].copy()
    maior, rhos = 0.0, []
    for i, r in fam.iterrows():
        sub = d
        if r.recorte == "sem_nome_divergente":
            sub = d[d.n_testes_nome_divergente == 0]
        x = sub[c.coluna_ts(r.test_smell)]
        if r.desfecho == "densidade":
            x = x / sub.n_metodos_teste.replace(0, np.nan)
        rho, p, n = spearman(x, sub.rotulo)
        rhos.append(p)
        if n != r.n:
            falhas.append("02 %s %s: N analise %d, scipy %d" % (r.test_smell, r.desfecho, r.n, n))
        confere("02 %s %s rho" % (r.test_smell, r.desfecho), r.rho, rho, TOL_RHO)
        maior = max(maior, confere("02 %s %s p" % (r.test_smell, r.desfecho), r.p, p, TOL_P))
    # BH aplicado aos p do proprio CSV, uma familia por recorte: confere so o ajuste
    for recorte, grupo_ in fam.groupby("recorte"):
        for (_, r), a in zip(grupo_.iterrows(), bh(grupo_.p.values)):
            confere("02 %s %s %s p_ajustado" % (recorte, r.test_smell, r.desfecho),
                    r.p_ajustado, a, TOL_BH)
    return ("02: %d correlacoes e o BH de cada recorte; maior diferenca de p %.4f"
            % (len(fam), maior))


def grupo(estratos):
    e = {x for x in str(estratos).split("|") if x and x != "nan"}
    if "positivo_confiavel" in e:
        return "confirmado"
    if e and e <= {"negativo_1_review", "negativo_confiavel"}:
        return "limpo"
    return None


def analise03():
    ext = pd.read_csv(os.path.join(A, "03-extremos", "dados", "extremos.csv"))
    maior = 0.0
    for nome in c.RAMOS:
        d = ramo(nome)
        d["grupo"] = d.estratos.map(grupo)
        for desf, col in (("bruto", "ts_n_total"), ("densidade", "densidade"),
                          ("distintos", "ts_n_distintos")):
            a = d.loc[d.grupo == "confirmado", col].dropna()
            b = d.loc[d.grupo == "limpo", col].dropna()
            u = stats.mannwhitneyu(a, b, alternative="two-sided", use_continuity=False,
                                   method="asymptotic")
            delta = (2 * u.statistic - len(a) * len(b)) / (len(a) * len(b))
            linha = ext[(ext.ramo == nome) & (ext.desfecho == desf)].iloc[0]
            confere("03 %s %s delta" % (nome, desf), linha.delta, delta, TOL_RHO)
            maior = max(maior, confere("03 %s %s p" % (nome, desf), linha.p, u.pvalue, 1e-4))
    return "03: 6 Mann-Whitney; maior diferenca de p %.6f" % maior


def analise05():
    cz = pd.read_csv(os.path.join(A, "05-code-x-test-smell", "dados", "cruzado.csv"))
    fam = cz[cz.recorte == "principal"]
    d = ramo("deterministico")
    maior = 0.0
    for _, r in fam.iterrows():
        sub = d[d.n_testes_nome_divergente == 0] if r.filtro_nome_divergente else d
        x = sub[c.coluna_ts(r.test_smell)] / sub.n_metodos_teste.replace(0, np.nan)
        rho, p, n = spearman(x, sub["cs_%s_sev_media" % r.code_smell.replace(" ", "_")])
        rot = "05 %s x %s" % (r.code_smell, r.test_smell)
        if n != r.n:
            falhas.append("%s: N analise %d, scipy %d" % (rot, r.n, n))
        confere(rot + " rho", r.rho, rho, TOL_RHO)
        maior = max(maior, confere(rot + " p", r.p, p, TOL_P))
    adj = bh(fam.p.values)
    for (_, r), a in zip(fam.iterrows(), adj):
        confere("05 %s x %s p_ajustado" % (r.code_smell, r.test_smell), r.p_ajustado, a, TOL_BH)
    validos = int(fam.p.notna().sum())
    return ("05: %d celulas (%d com p) e o BH da familia; maior diferenca de p %.4f"
            % (len(fam), validos, maior))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import scipy
    print("estat.py contra scipy %s, pandas %s" % (scipy.__version__, pd.__version__))
    for f in (analise01, analise02, analise03, analise05):
        print("  " + f())
    if falhas:
        print("\n%d divergencias:" % len(falhas))
        for x in falhas:
            print("  " + x)
        sys.exit(1)
    print("\nestat.py confere com o scipy em todas as analises")


if __name__ == "__main__":
    main()
