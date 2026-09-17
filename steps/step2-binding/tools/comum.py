r"""Caminhos, leitura do repos_map e normalizacao de caminho, usados por todos os scripts do step 2.

A normalizacao de caminho e o centro do step: os dois lados do estudo falam de
arquivos, mas com prefixos diferentes.

  MLCQ    /server/src/main/net/com/alibaba/cobar/net/NIOReactor.java
  JNose   C:\Users\crist\.jnose_projects\test-smells-cobar\server\src\main\...\NIOReactor.java

Reduzidos a um caminho relativo a raiz do repositorio, os dois coincidem exatamente -
e coincidem porque o status HASH_OK garante que espelho e MLCQ estao no mesmo commit.

Por isso o binding e feito por caminho, nunca por nome de classe: 2.956 basenames de
teste aparecem em mais de um arquivo dentro do mesmo repositorio (AppTest ocorre 159
vezes em maven-plugins), e casar por nome inventaria ligacoes que nao existem.
"""
import csv
import os
import sys

STEP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = os.path.dirname(STEP)
RAIZ = os.path.dirname(STEPS)

STEP1 = os.path.join(STEPS, "step1-coleta-jnose")
XLSX = os.path.join(RAIZ, "MLCQ", "MLCQCodeSmellSamples.xlsx")
MAPA = os.path.join(STEP1, "dados", "repos_map.csv")
BYCLASSTEST = os.path.join(STEP1, "reports", "byclasstest")
BYTESTSMELLS = os.path.join(STEP1, "reports", "bytestsmells")

DADOS = os.path.join(STEP, "dados")

# Os 13 smells habilitados na coleta. Os CSVs do JNose trazem 21 colunas de smell; as 8
# restantes nao foram habilitadas e estao zeradas em todas as 107.535 linhas - conferido,
# nao assumido (ver README, secao 2). Sao descartadas na normalizacao para que ninguem
# leia um zero estrutural como ausencia observada de smell.
SMELLS = [
    "Assertion Roulette", "Conditional Test Logic", "Dependent Test", "Duplicate Assert",
    "Eager Test", "Exception Catching Throwing", "General Fixture", "Lazy Test",
    "Magic Number Test", "Mystery Guest", "Redundant Assertion", "Resource Optimism",
    "Verbose Test",
]
SMELLS_DESABILITADOS = [
    "Sleepy Test", "Unknown Test", "EmptyTest", "IgnoredTest", "Sensitive Equality",
    "Default Test", "Constructor Initialization", "Print Statement",
]

# Os 4 code smells do MLCQ, com a granularidade em que cada um foi anotado.
CODE_SMELLS = {
    "blob": "class",
    "data class": "class",
    "feature envy": "function",
    "long method": "function",
}

# Ordem da escala de severidade do MLCQ. Virar numero e o que permite agregar; a
# escolha de COMO agregar nao e feita aqui (ver normalizar_mlcq.py).
SEVERIDADES = ["none", "minor", "major", "critical"]
RANK = {s: i for i, s in enumerate(SEVERIDADES)}

# Apendice do MLCQ, secao 2.2, fase 4: as ultimas 5115 revisoes (26.07.2019-13.09.2019)
# foram alocadas SO para amostras que alguem ja havia marcado com severidade > none.
# Conferido nos dados: das 1227 amostras com revisao a partir desta data, 1227 (100%)
# ja eram positivas antes dela, e nenhuma era negativa. O corte por data e portanto uma
# operacionalizacao exata do desenho amostral - melhor que contar revisores, que e so
# uma consequencia dele.
CORTE_CROSSCHECK = "2019-07-26"

MARCA_CLONES = ".jnose_projects/"


def coluna(smell):
    """Assertion Roulette -> ts_assertion_roulette. Evita depender de espacos no cabecalho."""
    return "ts_" + smell.lower().replace(" ", "_")


def caminho_relativo(absoluto):
    r"""Reduz um caminho do JNose ao caminho relativo a raiz do repositorio.

    Devolve com barra inicial e barras normais, no mesmo formato do campo path do MLCQ:
        C:\...\.jnose_projects\test-smells-cobar\server\src\...  ->  /server/src/...

    Devolve None se o caminho nao tiver a marca da pasta de clones. Nao ha nenhum caso
    assim nos dados do step 1 (conferido: 0 de 49.903 productionFile), mas um None
    silencioso viraria uma ligacao perdida sem rastro, entao quem chama contabiliza.
    """
    if not absoluto:
        return None
    p = absoluto.replace("\\", "/")
    i = p.lower().find(MARCA_CLONES)
    if i < 0:
        return None
    resto = p[i + len(MARCA_CLONES):]           # test-smells-cobar/server/src/...
    corte = resto.find("/")                      # remove o nome do diretorio do clone
    return resto[corte:] if corte >= 0 else None


def normalizar_mlcq_path(path):
    """Uniformiza o campo path do MLCQ: barras normais e barra inicial garantida."""
    p = (path or "").replace("\\", "/")
    return p if p.startswith("/") else "/" + p


def repo_do_mlcq(url):
    """git@github.com:alibaba/atlas.git -> alibaba/atlas"""
    u = (url or "").strip()
    for prefixo in ("git@github.com:", "https://github.com/", "http://github.com/"):
        if u.startswith(prefixo):
            u = u[len(prefixo):]
    return u[:-4] if u.endswith(".git") else u


def ler_mapa(caminho=MAPA):
    """Devolve {mlcq_repo: linha do repos_map} do step 1."""
    if not os.path.exists(caminho):
        sys.exit("repos_map.csv nao encontrado em %s (rode o step 1 primeiro)" % caminho)
    with open(caminho, encoding="utf-8") as fh:
        return {r["mlcq_repo"]: r for r in csv.DictReader(fh)}


def escrever_csv(caminho, cabecalho, linhas):
    """Escreve um artefato do step e devolve quantas linhas saiu.

    Virgula como separador e UTF-8 com BOM, para o Excel abrir sem o assistente de
    importacao. Os CSVs do JNose (ponto e virgula, sem BOM) sao entrada, nao saida.
    """
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    n = 0
    with open(caminho, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(cabecalho)
        for linha in linhas:
            w.writerow(linha)
            n += 1
    return n


def ler_csv(caminho):
    if not os.path.exists(caminho):
        sys.exit("%s nao encontrado - rode antes o script que o gera" % caminho)
    with open(caminho, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))
