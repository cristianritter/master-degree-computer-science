"""Reapura todo numero afirmado no README do step 3.

Mesmo papel do conferir_dados.py no step 2: resultado citado em texto que nao sai de um
comando envelhece em silencio. Aqui o risco e maior, porque as tabelas do step 2 podem ser
regeneradas com outros parametros - e ai o README do step 3 passaria a descrever numeros
que o dado nao produz mais.

Falha com codigo 1 se algum numero divergir.

Uso:
    python conferir_resultados.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c
import estat
from variaveis import pares, rotulo_agregado

falhas = []


def exigir(condicao, descricao, observado):
    marca = "ok  " if condicao else "FALHA"
    print("  [%s] %-62s %s" % (marca, descricao, observado))
    if not condicao:
        falhas.append("%s (observado: %s)" % (descricao, observado))


def perto(a, b, tol=0.001):
    return abs(a - b) <= tol


def conferir_caracterizacao():
    print("\nCARACTERIZACAO (secao 2)")
    print("-" * 24)
    linhas = c.ler_ramo("deterministico")
    exigir(len(linhas) == 730, "ramo deterministico tem 730 arquivos", len(linhas))

    agregado = [rotulo_agregado(r) for r in linhas]
    agregado = [v for v in agregado if v is not None]
    zeros = 100.0 * sum(1 for v in agregado if v == 0) / len(agregado)
    exigir(perto(zeros, 72.1, 0.1), "72,1% de zeros no rotulo agregado", "%.1f%%" % zeros)

    # a coluna de distintos nao pode passar do numero de smells habilitados
    mx = max(int(r["ts_n_distintos"]) for r in linhas)
    exigir(mx <= len(c.SMELLS),
           "ts_n_distintos nao passa dos %d smells habilitados" % len(c.SMELLS), mx)

    lazy = max(c.num(r[c.coluna_ts("Lazy Test")]) for r in linhas)
    exigir(perto(lazy, 1116, 0.5), "maximo de Lazy Test e 1.116", lazy)


def conferir_primeira_rodada():
    print("\nPRIMEIRA RODADA (secao 4)")
    print("-" * 25)

    esperado = {
        # ramo, desfecho -> (rho, p)
        ("deterministico", "bruto"): (0.094, 0.011),
        ("deterministico", "densidade"): (0.050, 0.175),
        ("deterministico", "distintos"): (0.084, 0.022),
        ("ampliado", "bruto"): (0.012, 0.659),
        ("ampliado", "densidade"): (0.001, 0.959),
        ("ampliado", "distintos"): (-0.003, 0.913),
    }
    for (ramo, chave), (rho_esp, p_esp) in sorted(esperado.items()):
        linhas = c.ler_ramo(ramo)
        x, y, _ = pares(linhas, chave, rotulo_agregado)
        rho, p, _, _, n = estat.spearman(x, y)
        exigir(perto(rho, rho_esp) and perto(p, p_esp, 0.002),
               "%s/%s: rho %.3f e p %.3f" % (ramo, chave, rho_esp, p_esp),
               "rho=%.3f p=%.3f N=%d" % (rho, p, n))

    print("\n  correlacoes parciais, controlando n_metodos_teste:")
    for chave, r_esp in (("bruto", 0.062), ("distintos", 0.056)):
        linhas = c.ler_ramo("deterministico")
        x, y, tam = pares(linhas, chave, rotulo_agregado)
        r, p, n = estat.parcial(x, y, tam)
        exigir(perto(r, r_esp), "parcial de %s cai para %.3f" % (chave, r_esp),
               "%.3f (p=%.3f)" % (r, p))

    print("\n  o confundidor:")
    linhas = c.ler_ramo("deterministico")
    validos = [r for r in linhas if rotulo_agregado(r) is not None
               and c.num(r["n_metodos_teste"]) is not None]
    rot = [rotulo_agregado(r) for r in validos]
    for nome, col, esp in (("n_metodos_teste", "n_metodos_teste", 0.078),
                           ("loc_teste", "loc_teste", 0.090)):
        rho, p, _, _, n = estat.spearman(rot, [c.num(r[col]) for r in validos])
        exigir(perto(rho, esp), "code smell x %s: rho %.3f" % (nome, esp),
               "%.3f (p=%.3f)" % (rho, p))

    x, y, tam = pares(linhas, "bruto", rotulo_agregado)
    rho, _, _, _, _ = estat.spearman(x, tam)
    exigir(perto(rho, 0.554), "test smell bruto x tamanho: rho 0,554", "%.3f" % rho)

    # a RQ1 tambem e respondida por smell, em densidade, com BH entre os quatro
    import csv
    caminho = os.path.join(c.STEP, "analises", "01-correlacao-agregada", "dados",
                           "exploracao.csv")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
            fam = [r for r in csv.DictReader(f) if r["p_ajustado"]
                   and r["ramo"] == "deterministico"]
        print("\n  RQ1 por smell, densidade, deterministico:")
        exigir(len(fam) == 4, "4 smells na familia da RQ1", len(fam))
        exigir(all(float(r["p_ajustado"]) > 0.05 for r in fam),
               "nenhum smell sobrevive ao FDR em densidade",
               ", ".join("%s %s" % (r["code_smell"], r["p_ajustado"][:5]) for r in fam))
        exigir(max(float(r["ic_alto"]) for r in fam) < 0.15,
               "teto do IC95% por smell abaixo de 0,15",
               "%.3f" % max(float(r["ic_alto"]) for r in fam))


def conferir_caderno():
    """O caderno da secao 4 declara um total de testes; o CSV tem que conter todos eles."""
    print("\nCADERNO DE TENTATIVAS (secao 4)")
    print("-" * 31)
    caminho = os.path.join(c.STEP, "analises", "01-correlacao-agregada", "dados", "exploracao.csv")
    if not os.path.exists(caminho):
        exigir(False, "exploracao.csv existe", "ausente - rode explorar.py --por-smell --csv")
        return
    import csv
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    simples = sum(1 for r in linhas if r["analise"] == "simples")
    parciais = sum(1 for r in linhas if r["analise"] == "parcial")
    exigir(len(linhas) == 40, "exploracao.csv tem 40 resultados gravados", len(linhas))
    exigir(simples == 30, "30 correlacoes simples", simples)
    exigir(parciais == 6, "6 correlacoes parciais", parciais)

    nominais = [r for r in linhas
                if r["analise"] == "simples" and r["p"] and float(r["p"]) < 0.05]
    print("  significancias nominais (p < 0,05):")
    for r in nominais:
        print("    %-16s %-14s %-11s rho=%6.3f  p=%.3f"
              % (r["ramo"], r["code_smell"], r["desfecho"], float(r["rho"]), float(r["p"])))
    exigir(len(nominais) == 5, "5 significancias nominais entre as simples", len(nominais))
    exigir(all(r["desfecho"] in ("bruto", "distintos") for r in nominais),
           "todas as significancias sao em desfecho sensivel a tamanho",
           ", ".join(sorted({r["desfecho"] for r in nominais})))


def conferir_segunda_rodada():
    """As analises 02 e 03: nenhuma sobrevive ao ajuste para comparacoes multiplas."""
    import csv
    print("")
    print("ANALISES 02 e 03")
    print("-" * 24)

    caminho = os.path.join(c.STEP, "analises", "02-por-test-smell", "dados", "por_test_smell.csv")
    if not os.path.exists(caminho):
        exigir(False, "por_test_smell.csv existe", "ausente - rode por_test_smell.py --csv")
    else:
        with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
            L = list(csv.DictReader(f))
        exigir(len(L) == 52, "analise 1 tem 52 testes", len(L))
        sobrevivem = [r for r in L if float(r["p_ajustado"]) < 0.05]
        exigir(len(sobrevivem) == 0,
               "nenhum test smell sobrevive ao ajuste FDR", len(sobrevivem))
        menor = min(float(r["p_ajustado"]) for r in L)
        exigir(perto(menor, 0.260, 0.001), "menor p ajustado e 0,260", "%.3f" % menor)
        # Eager e Lazy sao os que dependem da classe de producao: sao os mais proximos de
        # zero, que e o achado negativo com mais conteudo da secao
        for smell, esp in (("Eager Test", -0.020), ("Lazy Test", 0.038)):
            r = [x for x in L if x["test_smell"] == smell and x["desfecho"] == "densidade"
                 and x["recorte"] == "todas"][0]
            exigir(perto(float(r["rho"]), esp), "%s em densidade: rho %.3f" % (smell, esp),
                   r["rho"][:6])

    caminho = os.path.join(c.STEP, "analises", "03-extremos", "dados", "extremos.csv")
    if not os.path.exists(caminho):
        exigir(False, "extremos.csv existe", "ausente - rode extremos.py --csv")
        return
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        L = list(csv.DictReader(f))
    exigir(len(L) == 6, "analise 2 tem 6 testes", len(L))
    det = {r["desfecho"]: r for r in L if r["ramo"] == "deterministico"}
    exigir(int(det["bruto"]["n_positivo"]) == 136 and int(det["bruto"]["n_negativo"]) == 526,
           "deterministico: 136 confirmados e 526 limpos",
           "%s e %s" % (det["bruto"]["n_positivo"], det["bruto"]["n_negativo"]))
    # o padrao da analise 01 se repete: separa nos desfechos sensiveis a tamanho, nao na
    # densidade
    sig = sorted("%s/%s" % (r["ramo"], r["desfecho"]) for r in L
                 if float(r["p_ajustado"]) < 0.05)
    exigir(sig == ["deterministico/bruto", "deterministico/distintos"],
           "so bruto e distintos do deterministico sobrevivem ao FDR", ", ".join(sig) or "nenhum")
    exigir(float(det["densidade"]["p"]) > 0.05,
           "na densidade, confirmado x limpo nao separa",
           "p=%s delta=%s" % (det["densidade"]["p"][:5], det["densidade"]["delta"][:5]))
    # o efeito detectavel citado no README, pela mesma formula da analise 04
    n1, n2 = 136, 526
    det_delta = (1.959964 + 0.841621) * math.sqrt((n1 + n2 + 1.0) / (3.0 * n1 * n2))
    exigir(perto(det_delta, 0.156), "delta detectavel de 136 x 526 e 0,156", "%.3f" % det_delta)

    # os grupos de arquivo citados no README da analise 00
    from variaveis import grupo_arquivo
    import collections
    for ramo, esp in (("deterministico", {"confirmado": 136, "limpo": 526, "so_disputado": 67,
                                          None: 1}),
                      ("ampliado", {"confirmado": 267, "limpo": 985, "so_disputado": 117})):
        cont = dict(collections.Counter(grupo_arquivo(r) for r in c.ler_ramo(ramo)))
        exigir(cont == esp, "grupos de arquivo do ramo %s" % ramo,
               ", ".join("%s=%d" % (k, v) for k, v in sorted(cont.items(), key=str)))
    linhas = c.ler_ramo("deterministico")
    for estrato, pct in (("negativo_1_review", 72.9), ("negativo_confiavel", 18.8),
                         ("positivo_confiavel", 18.6), ("disputado", 15.1)):
        tem = 100.0 * sum(1 for r in linhas if estrato in r["estratos"].split("|")) / len(linhas)
        exigir(perto(tem, pct, 0.05), "%.1f%% dos arquivos tem %s" % (pct, estrato),
               "%.1f%%" % tem)


def conferir_disputados():
    """A analise 04: inconclusiva por poder, nao nula. O verificador precisa distinguir."""
    import csv
    print("")
    print("ANALISE 04 - disputados")
    print("-" * 23)
    caminho = os.path.join(c.STEP, "analises", "04-disputados", "dados", "disputados.csv")
    if not os.path.exists(caminho):
        exigir(False, "disputados.csv existe", "ausente - rode disputados.py --csv")
        return
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        L = list(csv.DictReader(f))
    exigir(len(L) == 6, "analise 04 tem 6 testes", len(L))
    det = {r["desfecho"]: r for r in L if r["ramo"] == "deterministico"}
    exigir(int(det["bruto"]["n_confirmado"]) == 136 and int(det["bruto"]["n_disputado"]) == 67,
           "deterministico: 136 confirmados e 67 so disputados",
           "%s e %s" % (det["bruto"]["n_confirmado"], det["bruto"]["n_disputado"]))
    nominais = [r for r in L if float(r["p"]) < 0.05]
    exigir(len(nominais) == 0, "nenhum resultado com p < 0,05", len(nominais))
    # o ponto da analise: TODOS os deltas ficam abaixo do detectavel - inconclusiva
    abaixo = [r for r in L if abs(float(r["delta"])) < float(r["delta_detectavel"])]
    exigir(len(abaixo) == 6,
           "todos os 6 deltas ficam abaixo do detectavel (inconclusiva, nao nula)",
           "%d de 6" % len(abaixo))
    # o que seria preciso para responder (README da analise 04)
    dd = lambda n1, n2: (1.959964 + 0.841621) * math.sqrt((n1 + n2 + 1.0) / (3.0 * n1 * n2))
    exigir(perto(dd(136, 10 ** 9), 0.139), "piso do detectavel com 136 confirmados e 0,139",
           "%.3f" % dd(136, 10 ** 9))
    exigir(dd(408, 201) <= 0.15 < dd(340, 167),
           "delta 0,15 pede ~408 confirmados e ~201 so disputados",
           "%.3f com 408 x 201" % dd(408, 201))


def conferir_cruzado():
    """A analise 05: a grade 4 x 13. Nenhuma celula sobrevive, nenhuma passa do detectavel."""
    import csv
    print("")
    print("ANALISE 05 - code smell x test smell")
    print("-" * 36)
    caminho = os.path.join(c.STEP, "analises", "05-code-x-test-smell", "dados", "cruzado.csv")
    if not os.path.exists(caminho):
        exigir(False, "cruzado.csv existe", "ausente - rode cruzado.py --csv")
        return
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        L = list(csv.DictReader(f))
    principal = [r for r in L if r["recorte"] == "principal"]
    sens = [r for r in L if r["recorte"] == "sensibilidade_sem_filtro"]
    exigir(len(principal) == 52, "analise 05 tem 52 testes na familia", len(principal))
    exigir(len(sens) == 8, "8 celulas de sensibilidade (Eager/Lazy sem filtro)", len(sens))
    sobrevivem = [r for r in principal if float(r["p_ajustado"]) < 0.05]
    exigir(len(sobrevivem) == 0, "nenhuma celula sobrevive ao ajuste FDR", len(sobrevivem))
    menor = min(float(r["p_ajustado"]) for r in principal)
    exigir(perto(menor, 0.104, 0.001), "menor p ajustado e 0,104", "%.3f" % menor)
    acima = [r for r in principal if abs(float(r["rho"])) >= float(r["r_detectavel"])]
    exigir(sorted("%s x %s" % (r["code_smell"], r["test_smell"]) for r in acima)
           == ["blob x Duplicate Assert", "feature envy x Verbose Test"],
           "so 2 celulas alcancam o r detectavel, nenhuma sobrevive ao FDR",
           ", ".join("%s x %s" % (r["code_smell"], r["test_smell"]) for r in acima))
    nominais = [r for r in principal if float(r["p"]) < 0.05]
    exigir(len(nominais) == 6, "6 significancias nominais, nenhuma ajustada", len(nominais))
    # a sensibilidade sem filtro quase nao difere da familia filtrada
    dc = {r["test_smell"]: float(r["rho"]) for r in sens if r["code_smell"] == "data class"}
    exigir(perto(dc["Eager Test"], 0.127) and perto(dc["Lazy Test"], 0.119),
           "sem filtro, data class x Eager/Lazy: 0,127 e 0,119",
           "%.3f e %.3f" % (dc["Eager Test"], dc["Lazy Test"]))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    conferir_caracterizacao()
    conferir_primeira_rodada()
    conferir_segunda_rodada()
    conferir_disputados()
    conferir_cruzado()
    conferir_caderno()

    print()
    if falhas:
        print("%d NUMERO(S) DIVERGENTE(S):" % len(falhas))
        for f in falhas:
            print("  - %s" % f)
        print("\nO README do step 3 descreve um dado que nao existe mais.")
        sys.exit(1)
    print("todos os numeros do README conferem")


if __name__ == "__main__":
    main()
