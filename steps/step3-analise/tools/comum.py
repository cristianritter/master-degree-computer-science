"""Caminhos e leitura das tabelas do step 2, usados por todos os scripts do step 3.

O step 3 nao recoleta nem religa nada: ele le as duas tabelas que o step 2 produziu e
roda analise em cima delas. Por isso este modulo e curto - ele so localiza os arquivos e
reusa o comum.py do step 2 para a lista de smells, em vez de manter uma copia que pode
divergir.

Os dois ramos existem porque "este teste testa esta classe" tem duas respostas
defensaveis, com precisao auditada diferente (step 2, secoes 5 e 6):

  deterministico   730 arquivos, precisao 94,2%   classes com teste dedicado
  ampliado       1.369 arquivos, precisao 10,1%   classes exercitadas por alguma suite
                                   (94,8% sob o construto "exercita", nao "testa")

Nenhum dos dois e "o certo": eles respondem perguntas diferentes, e qual usar e decisao da
analise, nao do dado.
"""
import csv
import importlib.util
import os
import sys

STEP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = os.path.dirname(STEP)
RAIZ = os.path.dirname(STEPS)

STEP2 = os.path.join(STEPS, "step2-binding")
DADOS = os.path.join(STEP, "dados")

RAMOS = {
    "deterministico": os.path.join(STEP2, "dados", "analise_deterministico.csv"),
    "ampliado": os.path.join(STEP2, "dados", "analise_ampliado.csv"),
}

# Precisao auditada de cada ramo (step 2, secao 5), para os relatorios do step 3 poderem
# cita-la sem que alguem precise ir procurar.
PRECISAO = {
    "deterministico": {"estrito": 94.2, "amplo": 94.2},
    "ampliado": {"estrito": 10.1, "amplo": 94.8},
}

ROTULOS = ["sev_media", "any", "any_major", "maioria", "unanime"]


def _step2_comum():
    """Carrega o comum.py do step 2 por caminho: os steps nao sao um pacote instalavel."""
    caminho = os.path.join(STEP2, "tools", "comum.py")
    if not os.path.exists(caminho):
        sys.exit("nao achei o comum.py do step 2 em %s" % caminho)
    spec = importlib.util.spec_from_file_location("comum_step2", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_c2 = _step2_comum()
SMELLS = _c2.SMELLS                    # os 13 test smells habilitados na coleta
CODE_SMELLS = sorted(_c2.CODE_SMELLS)  # blob, data class, feature envy, long method


def coluna_ts(smell):
    return "ts_" + smell.lower().replace(" ", "_")


def coluna_cs(smell, sufixo):
    return "cs_%s_%s" % (smell.replace(" ", "_"), sufixo)


def ler_ramo(ramo):
    """Le a tabela de um ramo. Falha alto se ela nao existir."""
    caminho = RAMOS[ramo]
    if not os.path.exists(caminho):
        sys.exit("%s nao existe. Rode: python %s/tools/gerar_analises.py"
                 % (caminho, STEP2))
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(valor):
    """Converte para float, devolvendo None para campo vazio.

    Vazio NAO e zero: nas colunas cs_* significa 'nao avaliado para este smell', e
    trata-lo como zero inventaria milhares de negativos (step 2, secao 6).
    """
    v = (valor or "").strip()
    if v == "":
        return None
    return float(v)


def dados_de(arquivo_do_script):
    """A pasta dados/ ao lado do script que chamou.

    Cada analise mora na sua pasta com o proprio dados/ e o proprio README, para que o
    artefato nunca fique longe do codigo que o produziu nem do texto que o interpreta.
    """
    return os.path.join(os.path.dirname(os.path.abspath(arquivo_do_script)), "dados")


def escrever_csv(caminho, cabecalho, linhas):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cabecalho)
        w.writerows(linhas)
    return len(linhas)
