"""Gera a folha de fatos do artigo: todo numero que o texto cita, com a origem de cada um.

O artigo nao digita numero. Cada valor citado vira uma macro em fatos.tex, e o LaTeX usa a
macro; folha-de-fatos.md e a mesma lista em forma legivel, com a origem de cada valor.

Os valores sao RECALCULADOS aqui a partir dos dados versionados, por codigo proprio, e nao
copiados dos READMEs dos steps. Isso faz da folha uma segunda apuracao: o
conferir_cobertura.py exige que cada numero dela case com a saida dos comandos dos steps,
entao um numero que este script calcule diferente do step aparece como divergencia.

Fontes, todas lidas do disco, sem rede:
  step 1   dados/repos_map.csv, reports/run_log.csv, reports-config-padrao/ (Unknown Test)
  step 2   mlcq_samples.csv, mlcq_reviews.csv, test_classes.csv, binding.csv,
           auditoria_binding_auto.csv, test_smell_occurrences.csv.gz, as duas tabelas,
           as planilhas do censo humano (conferidas com auditoria_humana.py --json)
  step 3   os CSVs que cada analise grava em analises/*/dados/

Uso:
    python artigo/tools/folha_de_fatos.py              # imprime os fatos
    python artigo/tools/folha_de_fatos.py --gravar     # grava folha-de-fatos.md e fatos.tex
    python artigo/tools/folha_de_fatos.py --conferir   # codigo 1 se os arquivos estao velhos
"""
import argparse
import collections
import csv
import glob
import gzip
import importlib.util
import json
import math
import os
import re
import subprocess
import sys

ARTIGO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(ARTIGO)
S1 = os.path.join(RAIZ, "steps", "step1-coleta-jnose")
S2 = os.path.join(RAIZ, "steps", "step2-binding")
S3 = os.path.join(RAIZ, "steps", "step3-analise")
D2 = os.path.join(S2, "dados")
A3 = os.path.join(S3, "analises")

MD = os.path.join(ARTIGO, "folha-de-fatos.md")
LATEX = os.path.join(ARTIGO, "latex")
TEX = os.path.join(LATEX, "fatos.tex")

Z_ALFA, Z_PODER = 1.959964, 0.841621   # bicaudal 0,05 e poder 80%, como nos steps 2 e 3


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


c2 = carregar("comum_step2", os.path.join(S2, "tools", "comum.py"))


def ler(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    return None if v in ("", None) else float(v)


# ---------------------------------------------------------------------------------------
# o registro dos fatos

Fato = collections.namedtuple("Fato", "secao chave valor casas tipo descricao fonte")
FATOS = []
SECAO = [""]


def secao(nome):
    SECAO[0] = nome


def fato(chave, valor, descricao, fonte, casas=0, tipo="n"):
    """tipo: n (numero), pct (porcentagem, valor ja em %), x (fator multiplicativo)."""
    assert re.fullmatch(r"[A-Za-z]+", chave), "macro LaTeX so aceita letras: %s" % chave
    assert chave not in {f.chave for f in FATOS}, "chave repetida: %s" % chave
    FATOS.append(Fato(SECAO[0], chave, valor, casas, tipo, descricao, fonte))


def formatar(f, idioma):
    v = round(f.valor, f.casas) if f.casas else int(round(f.valor))
    if v == 0:
        v = abs(v)                 # -0.000 sai como 0.000
    if f.casas:
        txt = "%.*f" % (f.casas, v)
    else:
        txt = "{:,}".format(v)
    txt = txt.replace("-", "−" if idioma == "pt" else "-")
    if idioma == "pt":
        txt = txt.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    elif txt.startswith("-"):
        txt = "$-$" + txt[1:]
    sufixo = {"pct": "%" if idioma == "pt" else "\\%", "x": "×" if idioma == "pt" else "$\\times$"}
    return txt + sufixo.get(f.tipo, "")


def r_detectavel(n):
    return math.tanh((Z_ALFA + Z_PODER) / math.sqrt(n - 3))


# ---------------------------------------------------------------------------------------
# step 1 - coleta

def coleta():
    secao("Coleta (step 1)")
    m = ler(os.path.join(S1, "dados", "repos_map.csv"))
    st = collections.Counter(r["status"] for r in m)
    fonte = "steps/step1-coleta-jnose/dados/repos_map.csv"
    fato("reposMlcq", len(m), "repositórios referenciados pelo MLCQ", fonte)
    fato("reposHashOk", st["HASH_OK"], "espelho no commit exato do MLCQ (analisados)", fonte)
    fato("reposHashDiverge", st["NOME_HASH_DIVERGE"], "espelho existe, mas em outro commit", fonte)
    fato("reposSemEspelho", st["SEM_REPO"], "sem espelho", fonte)

    log = ler(os.path.join(S1, "reports", "run_log.csv"))
    final = {r["mlcq_repo"]: r for r in log}
    ok = [r for r in final.values() if r["status"] == "OK"]
    fonte = "steps/step1-coleta-jnose/reports/run_log.csv"
    fato("reposColetados", len(ok), "repositórios com coleta concluída", fonte)
    fato("horasColeta", sum(float(r["segundos"] or 0) for r in log) / 3600,
         "horas de processamento da coleta, somando todas as tentativas", fonte, 1)
    junit = collections.Counter(r["junit"] for r in ok)
    fato("reposJunitQuatro", junit["JUnit4"], "repositórios detectados como JUnit 4", fonte)
    fato("reposJunitCinco", junit["JUnit5"], "repositórios detectados como JUnit 5", fonte)
    fato("reposJunitTres", junit["JUnit3"], "repositórios detectados como JUnit 3", fonte)
    removidos = {r["mlcq_repo"]: int(re.match(r"(\d+) arquivo", r["detalhe"]).group(1))
                 for r in ok if re.match(r"\d+ arquivo", r["detalhe"] or "")}
    fato("arquivosRemovidosNpe", sum(removidos.values()),
         "arquivos removidos antes da análise por derrubarem o JNose (NPE)", fonte)
    fato("reposRemovidosNpe", len(removidos), "repositórios com arquivo removido", fonte)

    tc = ler(os.path.join(D2, "test_classes.csv"))
    fonte = "steps/step2-binding/dados/test_classes.csv"
    fato("classesTeste", len(tc), "classes de teste analisadas pelo JNose", fonte)
    fato("reposComTeste", len({r["github_repo"] for r in tc}),
         "repositórios com pelo menos uma classe de teste", fonte)
    fato("smellsHabilitados", len(c2.SMELLS),
         "test smells habilitados (padrão do JNose menos o Unknown Test)",
         "steps/step2-binding/tools/comum.py (SMELLS)")
    soma = collections.Counter()
    for r in tc:
        for s in c2.SMELLS:
            soma[s] += int(r[c2.coluna(s)])
    total = sum(soma.values())
    fato("ocorrencias", total, "ocorrências de test smell", fonte)
    fato("pctAssertionRoulette", 100 * soma["Assertion Roulette"] / total,
         "parte das ocorrências que é Assertion Roulette", fonte, 1, "pct")
    fato("pctMagicNumber", 100 * soma["Magic Number Test"] / total,
         "parte das ocorrências que é Magic Number Test", fonte, 1, "pct")
    fato("ocorrenciasDefaultTest", soma["Default Test"],
         "ocorrências de Default Test na coleta inteira", fonte)

    div = [r for r in tc if r["nome_divergente"] == "1"]
    fato("classesAninhadas", len(div),
         "classes cujo nome reportado é o de uma classe aninhada (defeito do flowClass)", fonte)
    fato("pctClassesAninhadas", 100 * len(div) / len(tc), "idem, em porcentagem", fonte, 1, "pct")
    fato("reposAninhadas", len({r["github_repo"] for r in div}),
         "repositórios com classe aninhada", fonte)
    por1k = {}
    for g, linhas in (("bate", [r for r in tc if r["nome_divergente"] == "0"]), ("diverge", div)):
        por1k[g] = {s: 1000 * sum(int(r[c2.coluna(s)]) for r in linhas) / len(linhas)
                    for s in ("Eager Test", "Lazy Test")}
    fato("quedaEager", por1k["bate"]["Eager Test"] / por1k["diverge"]["Eager Test"],
         "queda de Eager Test por classe nas linhas aninhadas", fonte, 0, "x")
    fato("quedaLazy", por1k["bate"]["Lazy Test"] / por1k["diverge"]["Lazy Test"],
         "queda de Lazy Test por classe nas linhas aninhadas", fonte, 0, "x")

    eu = carregar("efeito_unknown_test", os.path.join(S1, "tools", "efeito_unknown_test.py"))
    tot, afetados, problemas = eu.medir()
    assert not problemas, problemas
    fonte = "steps/step1-coleta-jnose/tools/efeito_unknown_test.py"
    fato("unknownClasses", tot["zeradas"],
         "classes que o detector de Unknown Test zeraria", fonte)
    fato("pctUnknownClasses", 100 * tot["zeradas"] / len(tc), "idem, em porcentagem", fonte, 2, "pct")
    fato("unknownRepos", len(afetados), "repositórios afetados", fonte)
    fato("unknownOcorrencias", tot["ocorrencias_apagadas"],
         "ocorrências dos outros smells que ele apagaria", fonte)
    fato("pctUnknownOcorrencias", 100 * tot["ocorrencias_apagadas"] / total,
         "idem, em porcentagem", fonte, 2, "pct")
    return tc


def contagem_de_metodos(tc):
    """O n_metodos do JNose e getMembers().size() da ultima classe visitada pelo flowClass:
    conta campos, construtores, classes internas e helpers, e nas linhas aninhadas e o do
    helper. O sinal medivel e uma classe com mais metodos com smell do que n_metodos."""
    secao("Coleta (step 1)")
    com_smell = collections.defaultdict(set)
    por_classe = {"Default Test", "General Fixture", "Constructor Initialization"}
    with gzip.open(os.path.join(D2, "test_smell_occurrences.csv.gz"), "rt",
                   encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["smell"] in por_classe:
                continue
            # Lazy Test registra o grupo de metodos que chamam o mesmo metodo de producao
            com_smell[(r["github_repo"], r["path"])].update(
                m.strip() for m in r["metodo"].split(","))
    fonte = "steps/step2-binding/dados/test_smell_occurrences.csv.gz e test_classes.csv"
    for flag, chave, desc in (("1", "Aninhadas", "aninhadas"), ("0", "Normais", "sem aninhada")):
        linhas = [r for r in tc if r["nome_divergente"] == flag]
        excede = sum(1 for r in linhas
                     if len(com_smell[(r["github_repo"], r["path"])]) > int(r["n_metodos"] or 0))
        fato("excedeMetodos" + chave, excede,
             "classes %s com mais métodos com smell do que o n_metodos do JNose" % desc, fonte)
        if flag == "1":
            fato("pctExcedeMetodos" + chave, 100 * excede / len(linhas),
                 "idem, em porcentagem das classes %s" % desc, fonte, 1, "pct")


# ---------------------------------------------------------------------------------------
# step 2 - MLCQ, binding e auditoria

def mlcq():
    secao("MLCQ (step 2)")
    samples = ler(os.path.join(D2, "mlcq_samples.csv"))
    reviews = ler(os.path.join(D2, "mlcq_reviews.csv"))
    fonte = "steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv"
    fato("amostrasMlcq", len({s["sample_id"] for s in samples}), "amostras do MLCQ", fonte)
    fato("unidadesMlcq", len(samples), "unidades de rótulo (amostra, smell)", fonte)
    por_amostra = collections.Counter(s["sample_id"] for s in samples)
    fato("amostrasUmSmell", sum(1 for n in por_amostra.values() if n == 1),
         "amostras julgadas para um só dos dois smells da granularidade", fonte)
    fato("revisoesMlcq", len(reviews), "revisões do MLCQ", fonte)
    fato("escalaMax", max(c2.RANK.values()), "maior código da escala de severidade (critical)",
         "steps/step2-binding/tools/comum.py (SEVERIDADES)")
    fato("revisoresMlcq", len({r["reviewer_id"] for r in reviews}), "revisores distintos", fonte)
    um = sum(1 for s in samples if int(s["n_revisores"]) == 1)
    fato("unidadesUmRevisor", um, "unidades com um único revisor", fonte)
    fato("pctUnidadesUmRevisor", 100 * um / len(samples), "idem, em porcentagem", fonte, 1, "pct")

    # a selecao do crosscheck, e o experimento natural do "none" isolado (step 2, secao 3)
    pre, cross, vistos = collections.defaultdict(list), collections.defaultdict(list), set()
    for r in sorted(reviews, key=lambda r: int(r["review_id"])):
        k = (r["sample_id"], r["smell"], r["reviewer_id"])
        if k in vistos:
            continue
        vistos.add(k)
        (cross if r["is_crosscheck"] == "1" else pre)[k[:2]].append(int(r["severidade_num"]))
    com_cross = {u[0] for u in cross}
    fato("amostrasCrosscheck", len(com_cross),
         "amostras levadas ao crosscheck (todas já sinalizadas antes)", fonte)
    carona = [u for u in cross if u in pre and max(pre[u]) == 0]
    vira = sum(1 for u in carona
               if sum(1 for x in pre[u] + cross[u] if x > 0) > len(pre[u] + cross[u]) / 2)
    fato("noneRevisados", len(carona),
         "unidades com none isolado revisadas de novo por causa do outro smell", fonte)
    fato("pctNoneSeSustenta", 100 * (len(carona) - vira) / len(carona),
         "em que o none isolado coincide com a maioria final", fonte, 1, "pct")

    multi = [s for s in samples if int(s["n_reviews"]) >= 2 and s["pos_any"] == "1"]
    disputadas = sum(1 for s in multi if s["pos_unanime"] != "1")
    fato("pctDisputadas", 100 * disputadas / len(multi),
         "positivas com 2+ revisores em que algum revisor disse none", fonte, 1, "pct")
    est = collections.Counter(s["estrato"] for s in samples)
    for e, chave in (("negativo_1_review", "estratoNegUm"), ("negativo_confiavel", "estratoNegConf"),
                     ("positivo_confiavel", "estratoPosConf"), ("disputado", "estratoDisputado"),
                     ("positivo_1_review", "estratoPosUm")):
        fato(chave, est[e], "unidades no estrato %s" % e, fonte)


def binding():
    secao("Binding e auditoria (step 2)")
    b = ler(os.path.join(D2, "binding.csv"))
    fato("paresBinding", len(b), "pares (produção, teste) no binding",
         "steps/step2-binding/dados/binding.csv")
    aud = ler(os.path.join(D2, "auditoria_binding_auto.csv"))
    fonte = "steps/step2-binding/dados/auditoria_binding_auto.csv"
    fato("paresAuditados", len(aud), "pares auditados", fonte)
    fato("paresPorEstratoAuditoria",
         max(collections.Counter(r["estrato_auditoria"] for r in aud).values()),
         "pares sorteados por estrato amostrado (os de censo têm menos)", fonte)
    g = open(os.path.join(S2, "tools", "gerar_analises.py"), encoding="utf-8").read()
    fato("maxTestes", int(re.search(r'"--max-testes", "(\d+)"', g).group(1)),
         "teto de classes de teste por arquivo de produção no ramo ampliado",
         "steps/step2-binding/tools/gerar_analises.py")

    estratos = sorted({r["estrato_auditoria"] for r in aud})
    peso = {r["estrato_auditoria"]: float(r["peso_no_universo"]) for r in aud}
    prec = {}
    for e in estratos:
        L = [r for r in aud if r["estrato_auditoria"] == e]
        A = [r for r in L if (r.get("correto_amplo") or "").strip()]
        pe = sum(1 for r in L if r["correto"] == "s") / len(L)
        pa = sum(1 for r in A if r["correto_amplo"] == "s") / len(A) if A else pe
        prec[e] = (pe, pa, len(L), round(peso[e] * len(b)))

    det = ["caminho_exato", "convencao/caminho_espelhado", "convencao/so_basename"]
    for nome, grupo, chave in (("deterministico", det, "Det"), ("ampliado", estratos, "Amp")):
        W = sum(peso[e] for e in grupo)
        pe = sum(prec[e][0] * peso[e] for e in grupo) / W
        pa = sum(prec[e][1] * peso[e] for e in grupo) / W
        fato("precisao" + chave, 100 * pe,
             "precisão do binding no ramo %s (\"o teste tem a classe como alvo\")" % nome,
             fonte, 1, "pct")
        if nome == "ampliado":
            fato("precisaoAmpAmplo", 100 * pa,
                 "precisão no ramo ampliado sob \"o teste exercita a classe\"", fonte, 1, "pct")
        # IC95% estratificado (Wald, com correcao de populacao finita: estrato em censo
        # tem variancia zero)
        var = 0.0
        for e in grupo:
            p, _, n, N = prec[e]
            fpc = max(0.0, (N - n) / N) if N else 0.0
            var += (peso[e] / W) ** 2 * fpc * p * (1 - p) / max(n - 1, 1)
        meia = 1.959964 * math.sqrt(var)
        fato("precisao%sBaixo" % chave, 100 * (pe - meia),
             "limite inferior do IC95%% estratificado da precisão (%s)" % nome, fonte, 1, "pct")
        fato("precisao%sAlto" % chave, 100 * min(1.0, pe + meia),
             "limite superior do IC95%% estratificado da precisão (%s)" % nome, fonte, 1, "pct")
    fato("precisaoCaminhoExato", 100 * prec["caminho_exato"][0],
         "precisão do estrato caminho_exato", fonte, 1, "pct")


# ---------------------------------------------------------------------------------------
# a amostra de analise e os resultados (step 3)

def amostra():
    secao("Amostra de análise (step 2, tabelas derivadas)")
    for ramo, chave in (("deterministico", "Det"), ("ampliado", "Amp")):
        L = ler(os.path.join(D2, "analise_%s.csv" % ramo))
        fonte = "steps/step2-binding/dados/analise_%s.csv" % ramo
        fato("arquivos" + chave, len(L), "arquivos de produção no ramo %s" % ramo, fonte)
        fato("repos" + chave, len({r["github_repo"] for r in L}),
             "repositórios no ramo %s" % ramo, fonte)
        testes = {(r["github_repo"], t) for r in L for t in r["test_paths"].split("|")}
        fato("classesTeste" + chave, len(testes), "classes de teste ligadas no ramo %s" % ramo, fonte)
        rot = [max(v) for v in ([num(r["cs_%s_sev_media" % s.replace(" ", "_")])
                                 for s in sorted(c2.CODE_SMELLS)] for r in L)
               if any(x is not None for x in v) for v in [[x for x in v if x is not None]]]
        pos = sum(1 for x in rot if x > 0)
        fato("rotuloPositivo" + chave, pos, "arquivos com rótulo agregado acima de zero (%s)" % ramo, fonte)
        fato("pctRotuloPositivo" + chave, 100 * pos / len(rot), "idem, em porcentagem", fonte, 1, "pct")
        fato("comAninhada" + chave, sum(1 for r in L if num(r["n_testes_nome_divergente"])),
             "arquivos com algum teste de classe aninhada (%s)" % ramo, fonte)
        if ramo == "deterministico":
            fato("arquivosUmaAmostraDet", sum(1 for r in L if r["n_amostras"] == "1"),
                 "arquivos com uma única amostra do MLCQ (determinístico)", fonte)
        fato("rDetectavel" + chave, r_detectavel(len(L)),
             "menor r detectável com 80%% de poder, N do ramo %s" % ramo,
             "fórmula de poder do step 2 (poder_analise.py)", 3)


def resultados():
    secao("Resultados (step 3)")
    ex = ler(os.path.join(A3, "01-correlacao-agregada", "dados", "exploracao.csv"))
    fonte = "steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv"

    def linha(ramo, analise, desfecho, code="agregado"):
        return [r for r in ex if r["ramo"] == ramo and r["code_smell"] == code
                and r["analise"] == analise and r["desfecho"] == desfecho][0]

    for ramo, chave in (("deterministico", "Det"), ("ampliado", "Amp")):
        for desf, nome in (("densidade", "Densidade"), ("bruto", "Bruto"), ("distintos", "Distintos")):
            r = linha(ramo, "simples", desf)
            fato("rho%s%s" % (nome, chave), float(r["rho"]),
                 "Spearman %s × rótulo agregado (%s)" % (desf, ramo), fonte, 3)
            fato("p%s%s" % (nome, chave), float(r["p"]), "p bicaudal, idem", fonte, 3)
            if ramo == "deterministico":
                fato("ic%sBaixo" % nome, float(r["ic_baixo"]), "IC95%%, limite inferior (%s)" % desf, fonte, 3)
                fato("ic%sAlto" % nome, float(r["ic_alto"]), "IC95%%, limite superior (%s)" % desf, fonte, 3)
                fato("parcial%s" % nome, float(linha(ramo, "parcial", desf)["rho"]),
                     "Spearman parcial %s × rótulo, controlando n_metodos" % desf, fonte, 3)
    det = "deterministico"
    fato("rhoBrutoTamanho", float(linha(det, "simples", "bruto")["rho_com_tamanho"]),
         "Spearman contagem bruta × tamanho do teste (n_metodos)", fonte, 3)
    fato("rhoDensidadeTamanho", float(linha(det, "simples", "densidade")["rho_com_tamanho"]),
         "Spearman densidade × tamanho do teste", fonte, 3)
    fato("rhoRotuloMetodos", float(linha(det, "confundidor", "code smell x n_metodos_teste")["rho"]),
         "Spearman rótulo × n_metodos do teste", fonte, 3)
    fato("rhoRotuloLoc", float(linha(det, "confundidor", "code smell x loc_teste")["rho"]),
         "Spearman rótulo × LOC do teste", fonte, 3)

    pt = ler(os.path.join(A3, "02-por-test-smell", "dados", "por_test_smell.csv"))
    fonte = "steps/step3-analise/analises/02-por-test-smell/dados/por_test_smell.csv"
    fam = [r for r in pt if r["recorte"] in ("todas", "sem_nome_divergente") and r["p"] != "nan"]
    fato("testesPorSmell", len(fam), "testes da análise por test smell (duas famílias)", fonte)
    fato("nominaisPorSmell", sum(1 for r in fam if float(r["p"]) < 0.05),
         "desses, com p < 0,05 sem ajuste", fonte)
    fato("menorPajPorSmell", min(float(r["p_ajustado"]) for r in fam),
         "menor p ajustado por BH na análise por test smell", fonte, 3)

    ext = ler(os.path.join(A3, "03-extremos", "dados", "extremos.csv"))
    fonte = "steps/step3-analise/analises/03-extremos/dados/extremos.csv"
    for desf, nome in (("bruto", "Bruto"), ("densidade", "Densidade")):
        r = [x for x in ext if x["ramo"] == det and x["desfecho"] == desf][0]
        fato("delta%sExtremos" % nome, float(r["delta"]),
             "r bisserial confirmados × limpos, %s (determinístico)" % desf, fonte, 3)
        fato("paj%sExtremos" % nome, float(r["p_ajustado"]), "p ajustado, idem", fonte, 3)
        if desf == "bruto":
            fato("nConfirmados", int(r["n_positivo"]), "arquivos confirmados (determinístico)", fonte)
            fato("nLimpos", int(r["n_negativo"]), "arquivos limpos (determinístico)", fonte)

    di = ler(os.path.join(A3, "04-disputados", "dados", "disputados.csv"))
    r = [x for x in di if x["ramo"] == det and x["desfecho"] == "densidade"][0]
    fonte = "steps/step3-analise/analises/04-disputados/dados/disputados.csv"
    fato("deltaDisputados", float(r["delta"]), "r bisserial confirmados × só disputados, densidade", fonte, 3)
    fato("deltaDetectavelDisputados", float(r["delta_detectavel"]),
         "menor r bisserial detectável com 80% de poder, idem", fonte, 3)
    fato("nDisputados", int(r["n_disputado"]), "arquivos só disputados (determinístico)", fonte)

    cz = ler(os.path.join(A3, "05-code-x-test-smell", "dados", "cruzado.csv"))
    fonte = "steps/step3-analise/analises/05-code-x-test-smell/dados/cruzado.csv"
    prin = [r for r in cz if r["recorte"] == "principal" and r["p"] != "nan"]
    fato("testesGrade", len(prin), "testes da grade code smell × test smell", fonte)
    fato("menorPajGrade", min(float(r["p_ajustado"]) for r in prin),
         "menor p ajustado por BH na grade", fonte, 3)
    fato("acimaDetectavelGrade", sum(1 for r in prin if abs(float(r["rho"])) >= float(r["r_detectavel"])),
         "células da grade com |rho| acima do r detectável", fonte)

    rb = ler(os.path.join(A3, "06-robustez", "dados", "robustez.csv"))
    fonte = "steps/step3-analise/analises/06-robustez/dados/robustez.csv"
    rob = carregar("robustez", os.path.join(A3, "06-robustez", "robustez.py"))
    fato("margemEquivalencia", rob.MARGEM, "margem do TOST: |rho| de efeito pequeno (Cohen)",
         "steps/step3-analise/analises/06-robustez/robustez.py", 2)
    fato("replicasBootstrap", rob.REPLICAS, "réplicas do bootstrap por repositório",
         "steps/step3-analise/analises/06-robustez/robustez.py")

    def rob_linha(ramo, recorte, desfecho):
        return [r for r in rb if r["ramo"] == ramo and r["recorte"] == recorte
                and r["desfecho"] == desfecho][0]

    for ramo, chave in (("deterministico", "Det"), ("ampliado", "Amp")):
        r = rob_linha(ramo, "todas", "densidade")
        fato("maiorEfeito" + chave, float(r["maior_efeito_compativel"]),
             "maior |rho| compatível com os dados, densidade (limite do IC90%%, %s)" % ramo,
             fonte, 3)
        fato("bootBaixo" + chave, float(r["boot_ic95_baixo"]),
             "IC95%% do bootstrap por repositório, limite inferior, densidade (%s)" % ramo, fonte, 3)
        fato("bootAlto" + chave, float(r["boot_ic95_alto"]),
             "IC95%% do bootstrap por repositório, limite superior, densidade (%s)" % ramo, fonte, 3)
    r = rob_linha(det, "todas", "densidade")
    fato("pTostDensidadeDet", float(r["p_tost"]),
         "p do TOST na margem, densidade (determinístico)", fonte, 3)
    fato("icNoventaBaixo", float(r["ic90_baixo"]), "IC90%, limite inferior, densidade (determinístico)", fonte, 3)
    s = rob_linha(det, "sem_nome_divergente", "densidade")
    fato("rhoSemAninhadaDet", float(s["rho"]),
         "Spearman densidade × rótulo sem arquivos com classe aninhada (determinístico)", fonte, 3)
    fato("nSemAninhadaDet", int(s["n"]), "N desse recorte", fonte)
    fato("pSemAninhadaDet", float(s["p"]), "p bicaudal, idem", fonte, 3)

    total = 0
    for pasta, nome, col in (("01-correlacao-agregada", "exploracao.csv", "p"),
                             ("02-por-test-smell", "por_test_smell.csv", "p"),
                             ("03-extremos", "extremos.csv", "p"),
                             ("04-disputados", "disputados.csv", "p"),
                             ("05-code-x-test-smell", "cruzado.csv", "p"),
                             ("06-robustez", "robustez.csv", "p_tost")):
        total += sum(1 for r in ler(os.path.join(A3, pasta, "dados", nome))
                     if r[col] not in ("", "nan"))
    fato("testesTotal", total, "testes estatísticos rodados no step 3 (caderno)",
         "soma das linhas com p nos CSVs das análises 01 a 05 e com p_tost na 06")


# ---------------------------------------------------------------------------------------
# o censo humano do binding (PROTOCOLO-AUDITORIA-HUMANA.md)

PENDENTES = []      # (chave, descricao): macros que o artigo ja usa e o dado ainda nao tem


def censo():
    """Recalcula o censo humano por codigo proprio e confere com auditoria_humana.py: as
    duas contas tem que dar o mesmo numero, ou a folha nao e gerada."""
    secao("Censo humano do binding (step 2)")
    av1 = ler(os.path.join(D2, "auditoria_humana_avaliador1.csv"))
    av2 = ler(os.path.join(D2, "auditoria_humana_avaliador2.csv"))
    fonte2 = "steps/step2-binding/dados/auditoria_humana_avaliador2.csv"
    fonte1 = "steps/step2-binding/dados/auditoria_humana_avaliador1.csv"
    fato("paresSegundoAvaliador", len(av2), "pares julgados também pelo avaliador 2", fonte2)
    base = ler(os.path.join(D2, "auditoria_binding.csv"))
    estrato = {str(i): r["estrato_auditoria"] for i, r in enumerate(base, 1)}
    peso = {r["estrato_auditoria"]: float(r["peso_no_universo"]) for r in base}
    por = collections.Counter(estrato[r["par"]] for r in av2)
    assert len(set(por.values())) == 1, "subamostra do avaliador 2 desbalanceada: %s" % por
    fato("paresPorEstratoSegundo", next(iter(por.values())),
         "pares por estrato na subamostra do avaliador 2", fonte2)
    fato("estratosAuditoria", len(por), "estratos da auditoria do binding", fonte2)

    v = lambda x: (x or "").strip().lower() if (x or "").strip().lower() in ("s", "n", "?") else ""
    incompletos = [r["par"] for r in av1 if not (v(r["correto_estrito"]) and v(r["correto_amplo"]))]
    assert not incompletos, "censo do avaliador 1 incompleto: %s" % incompletos[:10]
    segundo_pronto = av2 and all(v(r["correto_estrito"]) and v(r["correto_amplo"]) for r in av2)

    def kappa(pares):
        d = [(a, b) for a, b in pares if a in ("s", "n") and b in ("s", "n")]
        po = sum(a == b for a, b in d) / len(d)
        pa, pb = (sum(x == "s" for x in lado) / len(d) for lado in zip(*d))
        pe = pa * pb + (1 - pa) * (1 - pb)
        return po, (po - pe) / (1 - pe) if pe < 1 else None

    det = ["caminho_exato", "convencao/caminho_espelhado", "convencao/so_basename"]
    auto = ler(os.path.join(D2, "auditoria_binding_auto.csv"))
    # processo separado: os steps tem cada um seu comum.py, e importar os dois aqui colide
    do_step = json.loads(subprocess.run(
        [sys.executable, os.path.join(S2, "tools", "auditoria_humana.py"), "--json"],
        capture_output=True, check=True, text=True).stdout)

    for crit, sufixo in (("estrito", ""), ("amplo", "Amplo")):
        col = "correto_" + crit
        cons = {r["par"]: v(r["consenso_" + crit]) for r in av2}
        final = {r["par"]: cons.get(r["par"]) or v(r[col]) for r in av1}
        cont = collections.defaultdict(collections.Counter)
        for par, x in final.items():
            cont[estrato[par]][x] += 1
        conta = {}
        for ramo, grupo in (("Det", det), ("Amp", sorted(cont))):
            W = sum(peso[e] for e in grupo)
            dec = [e for e in grupo if cont[e]["s"] + cont[e]["n"]]
            Wd = sum(peso[e] for e in dec)
            p = sum(cont[e]["s"] / (cont[e]["s"] + cont[e]["n"]) * peso[e] for e in dec) / Wd
            tot = lambda e: sum(cont[e].values())
            lo = sum(cont[e]["s"] / tot(e) * peso[e] for e in grupo) / W
            hi = sum((cont[e]["s"] + cont[e]["?"]) / tot(e) * peso[e] for e in grupo) / W
            conta[ramo] = (p, lo, hi)
            nome = {"Det": "determinístico", "Amp": "ampliado"}[ramo]
            fato("precisaoHumana%s%s" % (ramo, sufixo), 100 * p,
                 "precisão humana, ramo %s, critério %s, sobre os pares decididos" % (nome, crit),
                 fonte1, 1, "pct")
            fato("precisaoHumana%s%sInf" % (ramo, sufixo), 100 * lo,
                 "idem, limite inferior: todo '?' contado como n", fonte1, 1, "pct")
            fato("precisaoHumana%s%sSup" % (ramo, sufixo), 100 * hi,
                 "idem, limite superior: todo '?' contado como s", fonte1, 1, "pct")
        fato("interrogacoes%s" % (sufixo or "Estrito"), sum(c["?"] for c in cont.values()),
             "pares com veredito final '?', critério %s" % crit, fonte1)
        if crit == "estrito":
            # todo erro do ramo deterministico tem a assinatura da regra do teste que nao cita
            # a classe (estrito n, amplo ?): o texto afirma isso, entao a folha confere
            erros = [r["par"] for r in av1 if estrato[r["par"]] in det and final[r["par"]] == "n"]
            amplo = {r["par"]: cons_amplo or v(r["correto_amplo"])
                     for r in av1
                     for cons_amplo in [next((v(b["consenso_amplo"]) for b in av2
                                              if b["par"] == r["par"]), "")]}
            assert all(amplo[p] == "?" for p in erros), \
                "erro no ramo deterministico fora da regra do teste sem mencao: %s" % \
                [p for p in erros if amplo[p] != "?"]
            fato("errosHumanosDet", len(erros),
                 "pares do ramo determinístico em que o teste não tem a classe como alvo "
                 "(todos: o teste não cita a classe)", fonte1)

        # o juiz automatizado so preencheu correto_amplo onde as leituras divergem
        col_auto = "correto_amplo" if crit == "amplo" else "correto"
        pha = [(final[str(i)], v(r.get(col_auto)) or v(r["correto"]))
               for i, r in enumerate(auto, 1)]
        po_ha, k_ha = kappa(pha)
        fato("concordanciaHumanoAuto%s" % sufixo, 100 * po_ha,
             "concordância humano final × julgamento automatizado, critério %s" % crit,
             fonte1, 1, "pct")
        fato("kappaHumanoAuto%s" % sufixo, k_ha,
             "kappa humano final × julgamento automatizado, critério %s" % crit, fonte1, 3)

        # segunda apuracao: o step tem que dar o mesmo numero
        st = do_step[crit]
        for ramo, nome in (("Det", "deterministico"), ("Amp", "ampliado")):
            r = st["ramos"][nome]
            assert all(abs(a - b) < 1e-9 for a, b in
                       zip(conta[ramo], (r["precisao"], r["inferior"], r["superior"]))), \
                "precisao %s/%s difere de auditoria_humana.py" % (crit, nome)
        assert abs(st["humano_auto"][1] - po_ha) < 1e-9 and abs(st["humano_auto"][2] - k_ha) < 1e-9, \
            "humano x automatizado %s difere de auditoria_humana.py" % crit

        chave = {"estrito": "Estrito", "amplo": "Amplo"}[crit]
        if segundo_pronto:
            po12, k12 = kappa([(v(a[col]), v(b[col])) for b in av2
                               for a in av1 if a["par"] == b["par"]])
            assert abs(st["humanos"][1] - po12) < 1e-9, "concordancia %s difere" % crit
            fato("concordancia" + chave, 100 * po12,
                 "concordância entre avaliadores, critério %s, antes do consenso" % crit,
                 fonte2, 1, "pct")
            fato("kappa" + chave, k12,
                 "kappa de Cohen entre avaliadores, critério %s, antes do consenso" % crit, fonte2, 3)
        else:
            PENDENTES.append(("concordancia" + chave,
                              "concordância entre avaliadores, critério %s (%%)" % crit))
            PENDENTES.append(("kappa" + chave,
                              "kappa de Cohen entre avaliadores, critério %s" % crit))


# ---------------------------------------------------------------------------------------
# o texto do artigo: nenhum numero digitado

# O que pode aparecer como digito no texto sem vir de macro, e por que. Fica curto de
# proposito: cada entrada e uma afirmacao de que aquele numero nao e dado do estudo.
PERMITIDOS = [
    ("2.5.0", "versao do JNose Test"),
    ("0.9.4", "versao do jnose-core"),
    (r"95\%", "nivel de confianca convencional"),
    (r"90\%", "IC do TOST a 5% unilateral, convencao"),
    (r"80\%", "poder convencional"),
    ("0.05", "alfa convencional"),
    ("2em", "espacamento de layout"),
    (r"0.9\linewidth", "largura de layout"),
]
# comandos cujo argumento nao e texto, as macros de fato e os nomes das RQs
RE_COMANDO = re.compile(r"\\(?:cite|ref|label|begin|end|input|includegraphics)\{[^}]*\}"
                        r"|\\F[A-Za-z]+|\bRQ\d\b")


def conferir_latex():
    """Os .tex de sections/: todo \\F usado existe, e nenhum digito fica fora de macro."""
    problemas = []
    chaves = {f.chave for f in FATOS} | {k for k, _ in PENDENTES}
    for caminho in sorted(glob.glob(os.path.join(LATEX, "sections", "*.tex"))):
        nome = os.path.relpath(caminho, RAIZ)
        with open(caminho, encoding="utf-8") as fh:
            for i, linha in enumerate(fh, 1):
                linha = re.sub(r"(?<!\\)%.*", "", linha)
                for m in re.findall(r"\\F([A-Za-z]+)", linha):
                    if m not in chaves:
                        problemas.append("%s:%d macro inexistente \\F%s" % (nome, i, m))
                resto = RE_COMANDO.sub(" ", linha)
                for txt, _ in PERMITIDOS:
                    resto = resto.replace(txt, " ")
                if re.search(r"\d", resto):
                    problemas.append("%s:%d numero digitado: %s" % (nome, i, linha.strip()[:90]))
    return problemas


# ---------------------------------------------------------------------------------------
# saida

def gerar_md():
    out = ["# Folha de fatos",
           "",
           "Todo número que o artigo cita, com a origem de cada um. **Gerado** por",
           "`python artigo/tools/folha_de_fatos.py --gravar` — não editar à mão. O artigo usa as",
           "macros de `fatos.tex` (coluna *macro*), nunca o número digitado.",
           "",
           "Os valores são recalculados pelo próprio script a partir dos dados versionados; o",
           "`steps/conferir_cobertura.py` exige que cada um case com a saída dos comandos dos",
           "steps, o que faz desta folha uma segunda apuração.",
           ""]
    atual = None
    for f in FATOS:
        if f.secao != atual:
            atual = f.secao
            out += ["## " + atual, "", "| macro | valor | o que é | origem |", "|---|---:|---|---|"]
        out.append("| `\\F%s` | %s | %s | `%s` |" % (f.chave, formatar(f, "pt"), f.descricao, f.fonte))
        if FATOS.index(f) + 1 == len(FATOS) or FATOS[FATOS.index(f) + 1].secao != atual:
            out.append("")
    if PENDENTES:
        out += ["## Pendentes", "",
                "Macros que o artigo já usa e cujo dado ainda não existe: no PDF aparecem como",
                "`[?? chave]`. Saem desta lista quando a planilha do avaliador 2 voltar.", "",
                "| macro | o que será |", "|---|---|"]
        out += ["| `\\F%s` | %s |" % (k, d) for k, d in PENDENTES] + [""]
    return "\n".join(out)


def gerar_tex():
    out = ["% Gerado por artigo/tools/folha_de_fatos.py --gravar. Nao editar a mao.",
           "% Cada macro e um numero do artigo; a origem de cada uma esta em folha-de-fatos.md."]
    atual = None
    for f in FATOS:
        if f.secao != atual:
            atual = f.secao
            out += ["", "% " + atual]
        out.append("\\newcommand{\\F%s}{%s}" % (f.chave, formatar(f, "en")))
    if PENDENTES:
        out += ["", "% Pendentes: o dado ainda nao existe (censo humano do binding)",
                "\\providecommand{\\pendente}[1]{\\textbf{[??~#1]}}"]
        out += ["\\newcommand{\\F%s}{\\pendente{%s}}" % (k, k) for k, _ in PENDENTES]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    ap.add_argument("--conferir", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    tc = coleta()
    contagem_de_metodos(tc)
    mlcq()
    binding()
    amostra()
    resultados()
    censo()

    atual = None
    for f in FATOS:
        if f.secao != atual:
            atual = f.secao
            print("\n" + atual)
        valor = ("%.*f" % (f.casas, abs(f.valor) if round(f.valor, f.casas) == 0 else f.valor)
                 if f.casas else str(int(round(f.valor))))
        print("  %-28s %14s" % (f.chave, valor))
    print("\n%d fatos" % len(FATOS))

    md, tex = gerar_md(), gerar_tex()
    if args.gravar:
        for caminho, txt in ((MD, md), (TEX, tex)):
            with open(caminho, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(txt)
        print("gravados %s e %s" % (os.path.relpath(MD, RAIZ), os.path.relpath(TEX, RAIZ)))
    if args.conferir:
        velhos = []
        for caminho, txt in ((MD, md), (TEX, tex)):
            if not os.path.exists(caminho):
                velhos.append(caminho)
                continue
            with open(caminho, encoding="utf-8") as fh:
                if fh.read().replace("\r\n", "\n") != txt:
                    velhos.append(caminho)
        problemas = conferir_latex()
        for p in problemas:
            print("LATEX: " + p)
        if velhos:
            print("DESATUALIZADOS: %s - rode com --gravar"
                  % ", ".join(os.path.relpath(p, RAIZ) for p in velhos))
        if velhos or problemas:
            sys.exit(1)
        print("folha-de-fatos.md e fatos.tex conferem com os dados, e o texto do artigo "
              "so usa macros")


if __name__ == "__main__":
    main()
