"""Mede o que o detector de Unknown Test faz com a coleta, classe a classe.

A coleta do estudo (reports/) roda a configuracao padrao do JNose menos o Unknown Test. A
configuracao padrao inteira foi rodada tambem, nos mesmos 451 repositorios
(jnose_batch.py --config-padrao, em reports-config-padrao/). A unica diferenca entre as
duas e esse detector, e o JNose e deterministico; logo, nos 20 smells em comum, toda
diferenca entre elas e efeito dele.

O efeito esperado, pelo codigo do jnose-core 0.9.4, e um so: classes que tem algum metodo
sem corpo saem com TODOS os smells zerados, porque a excecao do detector descarta a
analise da classe inteira. O script confere que e so isso:

  - as duas coletas tem as mesmas classes (PathFile), com os mesmos TestFileName,
    ProductionFileName, LOC e numberMethods
  - nos 20 smells em comum, toda classe que difere esta zerada na configuracao padrao
  - a coluna Unknown Test da coleta do estudo e zero em todas as classes

e mede quantas classes, repositorios e ocorrencias o detector apaga. Sai com codigo 1 se
aparecer qualquer diferenca de outro tipo.

Uso:
    python efeito_unknown_test.py
"""
import collections
import csv
import glob
import os
import sys

STEP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESTUDO = os.path.join(STEP, "reports", "byclasstest")
PADRAO = os.path.join(STEP, "reports-config-padrao", "byclasstest")

UNKNOWN = "Unknown Test"
NAO_SMELL = {"App", "TestFileName", "PathFile", "ProductionFileName", "LOC", "numberMethods"}
CAMPOS = ["TestFileName", "ProductionFileName", "LOC", "numberMethods"]


def ler(caminho):
    with open(caminho, encoding="utf-8", errors="replace") as fh:
        leitor = csv.DictReader(fh, delimiter=";")
        return leitor.fieldnames or [], {r["PathFile"]: r for r in leitor}


def conta(linha, smells):
    return sum(int(linha[s] or 0) for s in smells)


def medir():
    """Devolve (totais, repositorios afetados, divergencias que nao sao do Unknown Test)."""
    repos_e = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ESTUDO, "*.csv")))
    repos_p = sorted(os.path.basename(p) for p in glob.glob(os.path.join(PADRAO, "*.csv")))
    problemas = []
    if repos_e != repos_p:
        problemas.append("repositorios diferentes: %d no estudo, %d na config padrao"
                         % (len(repos_e), len(repos_p)))

    tot = collections.Counter()
    repos_afetados = set()
    for nome in sorted(set(repos_e) & set(repos_p)):
        cab, e = ler(os.path.join(ESTUDO, nome))
        _, p = ler(os.path.join(PADRAO, nome))
        smells = [s for s in cab if s not in NAO_SMELL and s != UNKNOWN]
        tot["repos"] += 1
        tot["classes"] += len(e)
        for k in set(e) | set(p):
            if k not in e or k not in p:
                problemas.append("%s: classe so de um lado: %s" % (nome, k))
                continue
            if conta(e[k], [UNKNOWN]):
                problemas.append("%s: Unknown Test diferente de zero no estudo: %s" % (nome, k))
            campos = [f for f in CAMPOS if e[k][f] != p[k][f]]
            if campos:
                problemas.append("%s: campos %s diferentes: %s" % (nome, campos, k))
            occ_e = conta(e[k], smells)
            tot["ocorrencias"] += occ_e
            if all(e[k][s] == p[k][s] for s in smells):
                continue
            if conta(p[k], smells + [UNKNOWN]) == 0:
                tot["zeradas"] += 1
                tot["ocorrencias_apagadas"] += occ_e
                repos_afetados.add(nome)
            else:
                problemas.append("%s: smells diferentes sem a classe estar zerada: %s" % (nome, k))
    return tot, repos_afetados, problemas


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tot, repos_afetados, problemas = medir()
    print("configuracao padrao (21 smells) x coleta do estudo (20), nos 20 smells em comum")
    print("  repositorios: %d   classes de teste: %d   ocorrencias no estudo: %d"
          % (tot["repos"], tot["classes"], tot["ocorrencias"]))
    print("  classes zeradas pelo Unknown Test: %d (%.2f%%), em %d repositorios"
          % (tot["zeradas"], 100.0 * tot["zeradas"] / tot["classes"], len(repos_afetados)))
    print("  ocorrencias que a configuracao padrao perderia: %d (%.2f%%)"
          % (tot["ocorrencias_apagadas"],
             100.0 * tot["ocorrencias_apagadas"] / tot["ocorrencias"]))
    for p in problemas[:20]:
        print("  DIVERGE " + p)
    if problemas:
        print("  %d divergencia(s) que nao sao efeito do Unknown Test" % len(problemas))
        sys.exit(1)
    print("  nenhuma outra diferenca: o Unknown Test e a unica fonte de divergencia")


if __name__ == "__main__":
    main()
