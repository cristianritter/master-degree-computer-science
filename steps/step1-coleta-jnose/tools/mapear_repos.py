"""Gera o dados/repos_map.csv: liga cada repositorio do MLCQ ao seu espelho no GitHub.

O MLCQ aponta para repositorios de terceiros num commit especifico. Como esses
repositorios mudam (ou somem), o experimento usa espelhos sob a conta do autor,
criados no commit de interesse. Este script reconstroi essa ligacao.

O casamento e feito em tres passadas, nesta ordem:

  1. por hash   - o HEAD do espelho e igual ao commit_hash do MLCQ. E o criterio
                  mais forte, e resolve nomes que nao se parecem em nada
                  (SAP/iot-starterkit -> test-smells-cloud-platform-iot-starterkit)
                  e colisoes de nome (alibaba/atlas x apache/atlas, que por nome
                  disputariam o mesmo test-smells-atlas).
  2. por nome   - test-smells-<repo>, mais as resolucoes registradas em
                  proveniencia/matched.json e proveniencia/fuzzy.json.
  3. por sufixo - o espelho termina em -<repo> e e o unico candidato
                  (apache/fop -> test-smells-xmlgraphics-fop).

Status resultante:
  HASH_OK            espelho encontrado e no commit esperado -> entra na analise
  NOME_HASH_DIVERGE  espelho encontrado, mas noutro commit  -> fica de fora
  SEM_REPO           nenhum espelho                          -> fica de fora

Uso:
    python mapear_repos.py            # regera o CSV a partir de dados/proveniencia
    python mapear_repos.py --conferir # so compara com o CSV atual, sem escrever

A lista de repositorios do GitHub e seus HEADs vem de dados/proveniencia/, capturada
quando o mapeamento foi feito. Isso e proposital: refazer as chamadas a API hoje
traria HEADs diferentes se algum espelho tiver recebido commits depois, e o
experimento precisa continuar reproduzindo o mesmo recorte.
"""
import argparse
import collections
import csv
import io
import json
import os
import re
import sys

STEP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(os.path.dirname(os.path.dirname(STEP)), "MLCQ", "MLCQCodeSmellSamples.xlsx")
PROV = os.path.join(STEP, "dados", "proveniencia")
SAIDA = os.path.join(STEP, "dados", "repos_map.csv")

CABECALHO = ["mlcq_repo", "commit_esperado", "github_repo", "head_atual", "status"]


def repos_do_mlcq(xlsx=XLSX):
    """Extrai {owner/repo: commit_hash} da planilha do MLCQ.

    Cada linha da planilha e uma revisao (14739 no total); varios repositorios
    aparecem muitas vezes. Vale o commit da primeira ocorrencia, que e o mesmo em
    todas - o MLCQ fixa um commit por repositorio.
    """
    import openpyxl

    wb = openpyxl.load_workbook(xlsx, read_only=True)
    linhas = wb["MLCQ"].iter_rows(values_only=True)
    cab = list(next(linhas))
    i_repo, i_hash = cab.index("repository"), cab.index("commit_hash")
    pares = {}
    for linha in linhas:
        if not linha or not linha[i_repo]:
            continue
        achado = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", str(linha[i_repo]).strip())
        if achado:
            pares.setdefault(achado.group(1), str(linha[i_hash]).strip())
    return pares


def carregar_proveniencia():
    def ler(nome):
        with open(os.path.join(PROV, nome), encoding="utf-8") as fh:
            return json.load(fh)

    matched, fuzzy = ler("matched.json"), ler("fuzzy.json")
    with open(os.path.join(PROV, "heads.txt"), encoding="utf-8") as fh:
        heads = dict(l.split() for l in fh if l.split())

    # resolucoes de nome ja decididas quando o mapeamento foi feito
    por_nome = dict(matched)
    por_nome.update(fuzzy.get("auto", {}))
    for repo, candidatos in fuzzy.get("fuzzy", {}).items():
        por_nome.setdefault(repo, candidatos[0])
    return por_nome, heads


def mapear(mlcq, por_nome, heads):
    por_hash = collections.defaultdict(list)
    for espelho, head in heads.items():
        por_hash[head.lower()].append(espelho)
    espelhos = [e for e in heads if e.startswith(("test-smells-", "test-smell-"))]

    def por_sufixo(curto):
        alvo = curto.lower()
        achados = [e for e in espelhos
                   if e.lower().split("test-smells-", 1)[-1].split("test-smell-", 1)[-1] == alvo
                   or e.lower().endswith("-" + alvo)]
        return achados[0] if len(achados) == 1 else ""

    linhas = []
    for repo in sorted(mlcq):
        commit = mlcq[repo]
        candidatos = por_hash.get(commit.lower(), [])
        if len(candidatos) == 1:
            espelho = candidatos[0]
        elif len(candidatos) > 1:
            # varios espelhos no mesmo commit: o nome desempata
            preferido = por_nome.get(repo)
            espelho = preferido if preferido in candidatos else sorted(candidatos)[0]
        else:
            espelho = por_nome.get(repo) or por_sufixo(repo.split("/")[-1])

        head = heads.get(espelho, "") if espelho else ""
        if not espelho:
            status = "SEM_REPO"
        elif head.lower() == commit.lower():
            status = "HASH_OK"
        else:
            status = "NOME_HASH_DIVERGE"
        linhas.append([repo, commit, espelho, head, status])
    return linhas


def como_csv(linhas):
    buf = io.StringIO()
    escritor = csv.writer(buf, lineterminator="\n")
    escritor.writerow(CABECALHO)
    escritor.writerows(linhas)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--conferir", action="store_true",
                    help="compara com o repos_map.csv atual em vez de sobrescreve-lo")
    args = ap.parse_args()

    mlcq = repos_do_mlcq()
    por_nome, heads = carregar_proveniencia()
    linhas = mapear(mlcq, por_nome, heads)
    conteudo = como_csv(linhas)

    contagem = collections.Counter(l[4] for l in linhas)
    print("repositorios no MLCQ: %d" % len(mlcq))
    for status in ("HASH_OK", "NOME_HASH_DIVERGE", "SEM_REPO"):
        print("   %-18s %d" % (status, contagem[status]))

    if args.conferir:
        with open(SAIDA, encoding="utf-8", newline="") as fh:
            atual = fh.read().replace("\r\n", "\n")
        igual = (conteudo == atual)
        print("\n%s o CSV em disco" % ("REPRODUZ" if igual else "DIVERGE DE"))
        return 0 if igual else 1

    with open(SAIDA, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(conteudo)
    print("\nescrito: %s" % SAIDA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
