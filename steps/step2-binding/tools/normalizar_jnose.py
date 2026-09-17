"""Normaliza a saida do JNose (step 1) em CSVs com caminho relativo e nome de classe corrigido.

    dados/test_classes.csv                107.535 linhas - 1 por classe de teste
    dados/test_smell_occurrences.csv.gz 2.059.905 linhas - 1 por ocorrencia de smell

Tres coisas acontecem aqui, e a segunda e a que muda numeros.

1. Caminhos absolutos da maquina de coleta viram caminhos relativos ao repositorio, no
   mesmo formato do campo path do MLCQ. E o que permite o binding por caminho exato.

2. O nome da classe e recomputado a partir do basename do PathFile, corrigindo o defeito
   documentado no README do step 1 (secao 5): o flowClass do jnose-core nao para na
   primeira classe, entao em arquivo com classe aninhada o nome reportado e o do helper.
   Sao 6.842 de 107.535 linhas (6,4%), em 320 dos 451 repositorios.

   A correcao recupera a IDENTIDADE da classe, e o TestFileName original fica preservado
   na coluna nome_jnose. O que ela NAO recupera sao os valores de smell dessas linhas: o
   ProductionFileName foi resolvido a partir do nome errado, e por isso fica vazio em
   93,8% delas, derrubando Eager Test 28x e Lazy Test 23x. Por isso existe a coluna
   nome_divergente - ela marca exatamente as linhas cujos smells dependentes de codigo de
   producao nao sao confiaveis, e qualquer analise que envolva Eager/Lazy Test tem que
   filtrar ou estratificar por ela. Corrigir de verdade exigiria consertar o jnose-core e
   reprocessar as ~35 h de coleta.

3. As 8 colunas de smell nao habilitadas na coleta sao descartadas. Elas estao zeradas em
   todas as 107.535 linhas (conferido), e um zero estrutural lido como "smell ausente"
   seria um erro silencioso.

O campo methodCode do bytestsmells (o codigo-fonte do metodo de teste, responsavel por
quase todo o 1,4 GB do step 1) nao e copiado; methodCodeHash e os demais hashes ficam,
o que preserva a capacidade de deduplicar e de voltar ao step 1 quando o codigo for
necessario.

Uso:
    python normalizar_jnose.py                # as duas tabelas
    python normalizar_jnose.py --so-classes   # so test_classes.csv (rapido)
"""
import argparse
import collections
import csv
import glob
import gzip
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))   # methodCode chega a ser enorme

CAB_CLASSES = [
    "github_repo", "path", "nome_arquivo", "nome_jnose", "nome_divergente",
    "production_path", "tem_production", "loc", "n_metodos",
] + [c.coluna(s) for s in c.SMELLS] + ["n_smells_distintos", "n_smells_total"]

CAB_OCORRENCIAS = [
    "github_repo", "path", "nome_arquivo", "production_path", "junit",
    "loc", "n_metodos", "smell", "metodo", "linha_inicio", "linha_fim",
    "method_name_hash", "method_name_full_hash", "method_code_hash", "full_hash",
]


def _num(v):
    """Converte um campo de contagem do JNose em int. Vazio conta como 0."""
    v = (v or "").strip()
    return int(v) if v else 0


def _basename(rel):
    return os.path.basename(rel)[:-5] if rel and rel.endswith(".java") else os.path.basename(rel or "")


def normalizar_classes():
    arquivos = sorted(glob.glob(os.path.join(c.BYCLASSTEST, "*.csv")))
    if not arquivos:
        sys.exit("nao achei CSVs em %s (rode o step 1)" % c.BYCLASSTEST)

    linhas = []
    st = collections.Counter()
    chaves = set()

    for caminho in arquivos:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                st["linhas"] += 1
                repo = r["App"]
                rel = c.caminho_relativo(r.get("PathFile"))
                if rel is None:
                    st["caminho_irreconhecivel"] += 1
                    continue

                # O step 1 nao tem duplicatas (conferido: 107.535 chaves para 107.535
                # linhas). Se aparecer uma, e sinal de recoleta parcial e o binding
                # contaria a mesma classe duas vezes - falha alto.
                if (repo, rel.lower()) in chaves:
                    sys.exit("classe de teste duplicada: %s %s" % (repo, rel))
                chaves.add((repo, rel.lower()))

                nome_arquivo = _basename(rel)
                nome_jnose = (r.get("TestFileName") or "").strip()
                divergente = nome_jnose != nome_arquivo
                st["nome_divergente"] += divergente

                prod = c.caminho_relativo(r.get("ProductionFileName"))
                if (r.get("ProductionFileName") or "").strip() and prod is None:
                    st["production_irreconhecivel"] += 1
                st["tem_production"] += bool(prod)

                valores = [_num(r.get(s)) for s in c.SMELLS]
                linhas.append([
                    repo, rel, nome_arquivo, nome_jnose, int(divergente),
                    prod or "", int(bool(prod)), _num(r.get("LOC")),
                    _num(r.get("numberMethods")),
                ] + valores + [sum(1 for v in valores if v > 0), sum(valores)])

    n = c.escrever_csv(os.path.join(c.DADOS, "test_classes.csv"), CAB_CLASSES,
                       sorted(linhas, key=lambda x: (x[0], x[1])))
    print("test_classes.csv      %9d linhas" % n)
    print("  com production_path  %9d  (%.1f%%)" % (st["tem_production"],
                                                    100 * st["tem_production"] / n))
    print("  nome_divergente      %9d  (%.1f%%)  <- classe aninhada, ver docstring"
          % (st["nome_divergente"], 100 * st["nome_divergente"] / n))
    for k in ("caminho_irreconhecivel", "production_irreconhecivel"):
        if st[k]:
            print("  %-20s %9d" % (k, st[k]))
    repos = len({x[0] for x in linhas})
    print("  repositorios com >=1 classe de teste: %d" % repos)
    return repos


def normalizar_ocorrencias():
    arquivos = sorted(glob.glob(os.path.join(c.BYTESTSMELLS, "*.csv.gz")) +
                      glob.glob(os.path.join(c.BYTESTSMELLS, "*.csv")))
    if not arquivos:
        sys.exit("nao achei CSVs em %s" % c.BYTESTSMELLS)

    destino = os.path.join(c.DADOS, "test_smell_occurrences.csv.gz")
    os.makedirs(c.DADOS, exist_ok=True)
    t0 = time.time()
    n = 0
    fora = collections.Counter()

    with gzip.open(destino, "wt", newline="", encoding="utf-8") as saida:
        w = csv.writer(saida)
        w.writerow(CAB_OCORRENCIAS)
        for i, caminho in enumerate(arquivos, 1):
            abrir = gzip.open if caminho.endswith(".gz") else open
            with abrir(caminho, "rt", encoding="utf-8", errors="replace") as fh:
                for r in csv.DictReader(fh, delimiter=";"):
                    rel = c.caminho_relativo(r.get("pathFile"))
                    if rel is None:
                        fora["caminho_irreconhecivel"] += 1
                        continue
                    smell = (r.get("testSmellName") or "").strip()
                    if smell not in c.SMELLS:
                        # Ocorrencia de smell que a coleta nao habilitou nao deveria
                        # existir; se existir, e melhor saber do que agregar por acidente.
                        fora["smell_inesperado:" + smell] += 1
                        continue
                    w.writerow([
                        r.get("projectName"), rel, _basename(rel),
                        c.caminho_relativo(r.get("productionFile")) or "",
                        r.get("junitVersion"), _num(r.get("loc")), _num(r.get("qtdMethods")),
                        smell, r.get("testSmellMethod"),
                        r.get("testSmellLineBegin"), r.get("testSmellLineEnd"),
                        r.get("methodNameHash"), r.get("methodNameFullHash"),
                        r.get("methodCodeHash"), r.get("FullHash"),
                    ])
                    n += 1
            if i % 50 == 0:
                print("  ... %d/%d repos, %d ocorrencias, %.0fs"
                      % (i, len(arquivos), n, time.time() - t0))

    print("test_smell_occurrences.csv.gz %9d linhas  (%.0fs, %.0f MB)"
          % (n, time.time() - t0, os.path.getsize(destino) / 1e6))
    for k, v in fora.items():
        print("  descartado %-30s %d" % (k, v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-classes", action="store_true",
                    help="pula a tabela de ocorrencias (2 milhoes de linhas, alguns minutos)")
    args = ap.parse_args()

    normalizar_classes()
    if not args.so_classes:
        print()
        normalizar_ocorrencias()


if __name__ == "__main__":
    main()
