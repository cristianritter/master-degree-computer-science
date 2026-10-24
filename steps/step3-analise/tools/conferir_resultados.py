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

    # concentracao por repositorio: ameaca declarada (arquivos do mesmo repo nao sao
    # independentes)
    import collections
    por_repo = collections.Counter(r["github_repo"] for r in linhas)
    dez = 100.0 * sum(v for _, v in por_repo.most_common(10)) / len(linhas)
    um = sum(1 for v in por_repo.values() if v == 1)
    exigir((len(por_repo), um) == (246, 113) and perto(dez, 20.5, 0.05),
           "246 repositorios, 113 com um unico arquivo, top 10 com 20,5%",
           "%d, %d, %.1f%%" % (len(por_repo), um, dez))


def conferir_primeira_rodada():
    print("\nPRIMEIRA RODADA (secao 4)")
    print("-" * 25)

    esperado = {
        # ramo, desfecho -> (rho, p)
        ("deterministico", "bruto"): (0.087, 0.019),
        ("deterministico", "densidade"): (0.044, 0.238),
        ("deterministico", "distintos"): (0.072, 0.051),
        ("ampliado", "bruto"): (0.008, 0.775),
        ("ampliado", "densidade"): (-0.004, 0.888),
        ("ampliado", "distintos"): (-0.013, 0.641),
    }
    for (ramo, chave), (rho_esp, p_esp) in sorted(esperado.items()):
        linhas = c.ler_ramo(ramo)
        x, y, _ = pares(linhas, chave, rotulo_agregado)
        rho, p, _, _, n = estat.spearman(x, y)
        exigir(perto(rho, rho_esp) and perto(p, p_esp, 0.002),
               "%s/%s: rho %.3f e p %.3f" % (ramo, chave, rho_esp, p_esp),
               "rho=%.3f p=%.3f N=%d" % (rho, p, n))

    print("\n  correlacoes parciais, controlando n_metodos_teste:")
    for chave, r_esp in (("bruto", 0.052), ("distintos", 0.042)):
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
    exigir(perto(rho, 0.560), "test smell bruto x tamanho: rho 0,560", "%.3f" % rho)

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
    # o total do caderno e a soma das linhas de resultado de cada analise
    import csv
    por = []
    # a 06 repete o p de Fisher da 01; o teste novo dela e o TOST
    for pasta, nome, col in (("01-correlacao-agregada", "exploracao.csv", "p"),
                             ("02-por-test-smell", "por_test_smell.csv", "p"),
                             ("03-extremos", "extremos.csv", "p"),
                             ("04-disputados", "disputados.csv", "p"),
                             ("05-code-x-test-smell", "cruzado.csv", "p"),
                             ("06-robustez", "robustez.csv", "p_tost")):
        with open(os.path.join(c.STEP, "analises", pasta, "dados", nome), "r",
                  encoding="utf-8-sig", newline="") as f:
            # linha com p nan nao e teste: a variavel e constante no ramo (estat.calculaveis)
            por.append(sum(1 for r in csv.DictReader(f) if r[col] not in ("", "nan")))
    print("  testes registrados nos CSVs das analises: %s = %d"
          % (" + ".join(map(str, por)), sum(por)))
    # as linhas do caderno separam a rodada original das sensibilidades de caminho_exato
    for pasta, nome in (("02-por-test-smell", "por_test_smell.csv"),
                        ("05-code-x-test-smell", "cruzado.csv")):
        with open(os.path.join(c.STEP, "analises", pasta, "dados", nome), "r",
                  encoding="utf-8-sig", newline="") as f:
            rec = [r["recorte"] for r in csv.DictReader(f)]
        exato = rec.count("sensibilidade_caminho_exato")
        print("    %s: %d sem a sensibilidade caminho_exato, %d com ela"
              % (pasta, len(rec) - exato, exato))
    exigir(sum(por) == 235, "235 testes no caderno", sum(por))

    # as faixas numeradas da tabela do caderno, na ordem das linhas dela
    def contar(pasta, nome, recortes, col="p"):
        with open(os.path.join(c.STEP, "analises", pasta, "dados", nome), "r",
                  encoding="utf-8-sig", newline="") as f:
            return sum(1 for r in csv.DictReader(f) if r[col] not in ("", "nan")
                       and (recortes is None or r["recorte"] in recortes))
    exato = {"sensibilidade_caminho_exato"}
    linhas = [
        ("01", contar("01-correlacao-agregada", "exploracao.csv", None)),
        ("02", contar("02-por-test-smell", "por_test_smell.csv", {"todas", "sem_nome_divergente"})),
        ("03", contar("03-extremos", "extremos.csv", None)),
        ("04", contar("04-disputados", "disputados.csv", None)),
        ("05", contar("05-code-x-test-smell", "cruzado.csv", {"principal", "sensibilidade_sem_filtro"})),
        ("02 caminho_exato", contar("02-por-test-smell", "por_test_smell.csv", exato)),
        ("05 caminho_exato", contar("05-code-x-test-smell", "cruzado.csv", exato)),
        ("06", contar("06-robustez", "robustez.csv", None, "p_tost")),
    ]
    inicio, faixas = 1, []
    for nome, n in linhas:
        faixas.append("%s: %d a %d (%d)" % (nome, inicio, inicio + n - 1, n))
        inicio += n
    print("  faixas do caderno: " + "; ".join(faixas))
    exigir(inicio - 1 == sum(por), "as faixas do caderno cobrem os %d testes" % sum(por), inicio - 1)

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
    exigir(len(nominais) == 3, "3 significancias nominais entre as simples", len(nominais))
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
            todas = list(csv.DictReader(f))
        # na familia entra so o que e teste de fato: p nan e smell constante no ramo
        L = [r for r in todas if r["recorte"] != "sensibilidade_caminho_exato"
             and r["p"] != "nan"]
        sem_teste = sorted({r["test_smell"] for r in todas if r["p"] == "nan"})
        exigir(sem_teste == ["Default Test"], "so o Default Test fica sem teste (constante)",
               ", ".join(sem_teste) or "nenhum")
        exigir(len(L) == 76, "analise 02 tem 76 testes", len(L))
        # uma familia por recorte (todas, sem_nome_divergente): o BH de cada uma tem que
        # reproduzir o p_ajustado gravado, recalculado aqui sobre os p do proprio CSV
        for recorte in ("todas", "sem_nome_divergente"):
            fam = [r for r in L if r["recorte"] == recorte]
            refeito = estat.benjamini_hochberg([float(r["p"]) for r in fam])
            difere = max(abs(a - float(r["p_ajustado"])) for a, r in zip(refeito, fam))
            exigir(len(fam) == 38 and difere < 1e-4,
                   "familia %s: 38 testes, BH dentro dela" % recorte,
                   "%d testes, diferenca %.6f" % (len(fam), difere))
            print("    familia %s: %d testes, %.1f falsos positivos esperados a alfa 0,05 sem ajuste"
                  % (recorte, len(fam), 0.05 * len(fam)))
        sobrevivem = [r for r in L if float(r["p_ajustado"]) < 0.05]
        exigir(len(sobrevivem) == 0,
               "nenhum test smell sobrevive ao ajuste FDR", len(sobrevivem))
        menor = min(float(r["p_ajustado"]) for r in L)
        exigir(perto(menor, 0.379, 0.001), "menor p ajustado e 0,379", "%.3f" % menor)
        # Eager e Lazy sao os que dependem da classe de producao: nao se destacam, ficam na
        # metade de baixo das celulas de densidade; as maiores sao de smells internos ao teste
        for smell, esp in (("Eager Test", -0.020), ("Lazy Test", 0.038)):
            r = [x for x in L if x["test_smell"] == smell and x["desfecho"] == "densidade"
                 and x["recorte"] == "todas"][0]
            exigir(perto(float(r["rho"]), esp), "%s em densidade: rho %.3f" % (smell, esp),
                   r["rho"][:6])
        dens = sorted((abs(float(x["rho"])), x["test_smell"]) for x in L
                      if x["desfecho"] == "densidade" and x["recorte"] == "todas")
        posto = {s: i + 1 for i, (_, s) in enumerate(dens)}
        print("  densidade, todas as linhas, posto de |rho| entre %d: Eager %d, Lazy %d; maiores %s"
              % (len(dens), posto["Eager Test"], posto["Lazy Test"],
                 ", ".join("%s %.3f" % (s, v) for v, s in dens[-2:][::-1])))
        exigir(len(dens) == 19 and max(posto["Eager Test"], posto["Lazy Test"]) <= 10
               and [s for _, s in dens[-2:]] == ["Exception Catching Throwing", "Magic Number Test"],
               "Eager e Lazy na metade de baixo; as maiores sao Magic Number e ECT",
               "Eager %d, Lazy %d de %d" % (posto["Eager Test"], posto["Lazy Test"], len(dens)))
        # sensibilidade: so onde a classe do JNose e a do binding (caminho_exato). Eager e
        # Lazy continuam perto de zero, entao o "perto de zero" nao e artefato da convencao
        sens = {r["test_smell"]: r for r in todas if r["recorte"] == "sensibilidade_caminho_exato"}
        exigir(len(sens) == 3 and all(int(r["n"]) == 649 for r in sens.values()),
               "sensibilidade caminho_exato: 3 smells, N = 649",
               ", ".join("%s N=%s" % (k, r["n"]) for k, r in sens.items()))
        for smell, esp in (("Eager Test", -0.032), ("Lazy Test", 0.024), ("General Fixture", 0.016)):
            exigir(perto(float(sens[smell]["rho"]), esp) and float(sens[smell]["p"]) > 0.05,
                   "%s so caminho_exato: rho %.3f, sem significancia" % (smell, esp),
                   "%s (p=%s)" % (sens[smell]["rho"][:6], sens[smell]["p"][:5]))

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
    # o efeito detectavel citado no README sai do proprio extremos.csv
    exigir(perto(float(det["densidade"]["delta_detectavel"]), 0.156),
           "delta detectavel da densidade (135 x 524) e 0,156",
           det["densidade"]["delta_detectavel"][:6])

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
    # o que seria preciso para responder: sai do poder_necessario.csv do disputados.py
    caminho = os.path.join(c.STEP, "analises", "04-disputados", "dados", "poder_necessario.csv")
    if not os.path.exists(caminho):
        exigir(False, "poder_necessario.csv existe", "ausente - rode disputados.py --csv")
        return
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        nec = [r for r in csv.DictReader(f) if r["ramo"] == "deterministico"]
    obtido = [(r["cenario"], r["n_confirmado"], r["n_disputado"], round(float(r["delta_detectavel"]), 3))
              for r in nec]
    exigir(obtido == [("observado", "136", "67", 0.242), ("mais_disputados", "136", "200", 0.18),
                      ("mais_disputados", "136", "500", 0.157), ("piso", "136", "", 0.139),
                      ("para_delta_0.15", "354", "174", 0.15)],
           "cenarios de poder da analise 04 (67, 200, 500, infinito, 354 x 174)",
           "; ".join("%s %s/%s %.3f" % x for x in obtido))


def conferir_cruzado():
    """A analise 05: a grade 4 x 20. Nenhuma celula sobrevive ao FDR."""
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
    principal = [r for r in L if r["recorte"] == "principal" and r["p"] != "nan"]
    sens = [r for r in L if r["recorte"] == "sensibilidade_sem_filtro"]
    exigir(len(principal) == 76, "analise 05 tem 76 testes na familia (4 celulas do Default Test sem teste)",
           len(principal))
    exigir(len(sens) == 8, "8 celulas de sensibilidade (Eager/Lazy sem filtro)", len(sens))
    exato = [r for r in L if r["recorte"] == "sensibilidade_caminho_exato"]
    exigir(len(exato) == 8, "8 celulas de sensibilidade (Eager/Lazy so caminho_exato)", len(exato))
    fam = {(r["code_smell"], r["test_smell"]): float(r["rho"]) for r in principal}
    dif = max(abs(float(r["rho"]) - fam[(r["code_smell"], r["test_smell"])]) for r in exato)
    exigir(dif < 0.01, "caminho_exato muda Eager/Lazy em menos de 0,01 na grade",
           "maior diferenca %.3f" % dif)
    sobrevivem = [r for r in principal if float(r["p_ajustado"]) < 0.05]
    exigir(len(sobrevivem) == 0, "nenhuma celula sobrevive ao ajuste FDR", len(sobrevivem))
    menor = min(float(r["p_ajustado"]) for r in principal)
    exigir(perto(menor, 0.153, 0.001), "menor p ajustado e 0,153", "%.3f" % menor)
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


def conferir_robustez():
    """A analise 06: o nulo da 01 sob equivalencia, bootstrap por repositorio e recorte."""
    import csv
    print("")
    print("ANALISE 06 - robustez")
    print("-" * 21)
    caminho = os.path.join(c.STEP, "analises", "06-robustez", "dados", "robustez.csv")
    if not os.path.exists(caminho):
        exigir(False, "robustez.csv existe", "ausente - rode robustez.py --csv")
        return
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        L = list(csv.DictReader(f))
    exigir(len(L) == 12, "robustez.csv tem 12 linhas", len(L))

    def linha(ramo, recorte, desfecho):
        return [r for r in L if r["ramo"] == ramo and r["recorte"] == recorte
                and r["desfecho"] == desfecho][0]

    det = linha("deterministico", "todas", "densidade")
    sem = linha("deterministico", "sem_nome_divergente", "densidade")
    amp = linha("ampliado", "todas", "densidade")
    for nome, r in (("todas", det), ("sem aninhada", sem)):
        print("  determ. %-13s N=%s repos=%s rho=%.3f IC90 [%.3f, %.3f] TOST p=%.3f "
              "boot [%.3f, %.3f]" % (nome, r["n"], r["n_repos"], float(r["rho"]),
                                     float(r["ic90_baixo"]), float(r["ic90_alto"]),
                                     float(r["p_tost"]), float(r["boot_ic95_baixo"]),
                                     float(r["boot_ic95_alto"])))
    exigir(det["n"] == "726" and det["n_repos"] == "245", "densidade: 726 arquivos em 245 repos",
           "%s e %s" % (det["n"], det["n_repos"]))
    exigir(perto(float(det["maior_efeito_compativel"]), 0.105),
           "os dados excluem rho acima de 0,105", det["maior_efeito_compativel"])
    exigir(perto(float(det["p_tost"]), 0.065) and float(det["p_tost"]) > 0.05,
           "TOST na margem 0,10 nao alcanca equivalencia (p = 0,065)", det["p_tost"])
    exigir(perto(float(det["boot_ic95_baixo"]), -0.028) and perto(float(det["boot_ic95_alto"]), 0.119),
           "bootstrap por repositorio [-0,028, 0,119]",
           "%s, %s" % (det["boot_ic95_baixo"], det["boot_ic95_alto"]))
    exigir(sem["n"] == "677" and perto(float(sem["rho"]), 0.041),
           "sem classe aninhada: 677 arquivos, rho 0,041", "%s, %s" % (sem["n"], sem["rho"]))
    exigir(perto(float(sem["p_tost"]), 0.063), "sem aninhada: TOST p 0,063", sem["p_tost"])
    exigir(float(amp["p_tost"]) < 0.001 and perto(float(amp["ic90_baixo"]), -0.048)
           and perto(float(amp["ic90_alto"]), 0.041),
           "ampliado equivalente a zero: IC90 [-0,048, 0,041], TOST p < 0,001",
           "%s, %s, %s" % (amp["ic90_baixo"], amp["ic90_alto"], amp["p_tost"]))
    bruto = linha("deterministico", "todas", "bruto")
    exigir(float(bruto["boot_ic95_baixo"]) > 0, "bruto: IC do bootstrap acima de zero",
           bruto["boot_ic95_baixo"])


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
    conferir_robustez()
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
