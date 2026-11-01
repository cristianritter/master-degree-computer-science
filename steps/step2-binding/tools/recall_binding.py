"""Recall do binding, parte automatica: arquivos de producao sem ligacao.

    dados/recall_semref_amostra.csv   a amostra sorteada (semente fixa)
    dados/recall_semref.csv           1 linha por arquivo sorteado: o que a varredura achou
    dados/recall_semref_log.csv       1 linha por repositorio processado (retomavel)

A auditoria de precisao decidiu que um teste que nao cita a classe nao a tem como alvo.
Com essa definicao, um arquivo de producao sem nenhuma ligacao (motivo_sem_ligacao =
sem_ligacao_resolvida: nenhum teste do repositorio o referencia, segundo refs_producao.py)
so pode ter um teste dedicado perdido se a propria extracao de referencias falhou. Isso
da para medir sem julgamento humano: sortear arquivos desse grupo e procurar referencia
a eles com uma varredura mais larga que a original.

A varredura e mais larga em dois eixos:

  quais arquivos   todo .java do repositorio com "test" no caminho ou terminado em IT, no
                   commit da coleta - nao so as classes que o JNose reconheceu como teste
                   (test_classes.csv), que foi o universo do refs_producao.py;
  que referencia   alem de import exato, wildcard e mesmo pacote (as tres do
                   refs_producao.py), tambem import static da classe, import de classe
                   aninhada nela e o nome qualificado escrito no codigo.

Uma referencia achada aqui, vinda de um teste que o JNose analisou, e uma ligacao que o
binding perdeu. Referencia vinda de arquivo fora do universo do JNose nao e: esse arquivo
nao tem medida de test smell e nao entraria no estudo de todo jeito.

Uso:
    python recall_binding.py --sortear          # grava a amostra (recusa sobrescrever)
    python recall_binding.py --varrer           # clona e varre; retomavel
    python recall_binding.py --apurar           # resume o que a varredura achou
"""
import argparse
import collections
import csv
import math
import os
import random
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c
import refs_producao as rp

AMOSTRA = os.path.join(c.DADOS, "recall_semref_amostra.csv")
SAIDA = os.path.join(c.DADOS, "recall_semref.csv")
LOG = os.path.join(c.DADOS, "recall_semref_log.csv")

TAMANHO = 100
SEMENTE = 42


CAB_SAIDA = ["github_repo", "production_path", "pacote", "arquivos_varridos",
             "n_referencias", "referencias"]
CAB_LOG = ["github_repo", "status", "n_amostra", "arquivos_varridos", "segundos", "detalhe"]

RE_PACOTE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)
RE_IMPORT = re.compile(r"^\s*import\s+(static\s+)?([\w.]+?)(\.\*)?\s*;", re.M)


def eh_teste(caminho):
    nome = caminho.rsplit("/", 1)[-1]
    return caminho.endswith(".java") and ("test" in caminho.lower() or nome.endswith("IT.java"))


def sortear():
    if os.path.exists(AMOSTRA):
        sys.exit("%s ja existe - a amostra e sorteada uma vez so." % AMOSTRA)
    sem = [r for r in c.ler_csv(os.path.join(c.DADOS, "production_files.csv"))
           if r["motivo_sem_ligacao"] == "sem_ligacao_resolvida"]
    # ordem estavel antes do sorteio: a semente sozinha nao basta se a ordem do CSV mudar
    sem.sort(key=lambda r: (r["github_repo"], r["production_path"]))
    escolhidos = random.Random(SEMENTE).sample(sem, TAMANHO)
    escolhidos.sort(key=lambda r: (r["github_repo"], r["production_path"]))
    n = c.escrever_csv(AMOSTRA, ["github_repo", "production_path"],
                       ([r["github_repo"], r["production_path"]] for r in escolhidos))
    print("%s: %d de %d arquivos sem ligacao (semente %d)" % (AMOSTRA, n, len(sem), SEMENTE))


def referencias(fonte_teste, nome, pacote):
    """As formas pelas quais este teste referencia <pacote>.<nome>, ou lista vazia."""
    fqn = "%s.%s" % (pacote, nome) if pacote else nome
    achadas = []
    for estatico, alvo, estrela in RE_IMPORT.findall(fonte_teste):
        if not estatico and not estrela and alvo == fqn:
            achadas.append("import_fqn")
        elif estatico and (alvo == fqn or alvo.startswith(fqn + ".")):
            achadas.append("import_static")
        elif not estatico and alvo.startswith(fqn + "."):
            achadas.append("import_aninhada")
    limpo = c.sem_comentarios(fonte_teste)
    menciona = re.search(r"(?<![\w$.])%s\b" % re.escape(nome), limpo) is not None
    pac_t = RE_PACOTE.search(fonte_teste)
    pac_t = pac_t.group(1) if pac_t else ""
    wild = {alvo for est, alvo, estrela in RE_IMPORT.findall(fonte_teste) if estrela and not est}
    if menciona and pacote and pacote in wild:
        achadas.append("wildcard")
    if menciona and pacote and pac_t == pacote:
        achadas.append("mesmo_pacote")
    if pacote and re.search(r"\b%s\b" % re.escape(fqn), limpo):
        achadas.append("fqn_no_codigo")
    return sorted(set(achadas))


def git(*args, cwd=None, entrada=None):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(["git"] + list(args), cwd=cwd, input=entrada, env=env,
                          capture_output=True, check=True, timeout=3600).stdout


def varrer_repo(repo, producoes, commit, dest):
    url = "https://github.com/cristianritter/%s.git" % repo
    if os.path.exists(dest) and not rp.jb.rmtree(dest):
        raise RuntimeError("nao consegui remover clone anterior: " + dest)
    git("-c", "http.sslBackend=schannel", "clone", "--depth", "1", "--filter=blob:none",
        "--no-checkout", "-q", url, dest)
    git("-C", dest, "config", "http.sslBackend", "schannel")
    head = git("-C", dest, "rev-parse", "HEAD").decode().strip()
    if commit and head != commit:
        raise RuntimeError("HEAD %s difere do esperado %s" % (head[:12], commit[:12]))
    arvore = git("-C", dest, "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only",
                 "HEAD").decode("utf-8", errors="replace").splitlines()
    testes = ["/" + p for p in arvore if eh_teste("/" + p)]
    git("-C", dest, "sparse-checkout", "init", "--no-cone")
    git("-C", dest, "sparse-checkout", "set", "--stdin",
        entrada=("\n".join(testes + list(producoes)) + "\n").encode("utf-8"))
    git("-C", dest, "checkout", "-q")

    fontes = {}
    for rel in testes:
        fisico = os.path.join(dest, rel.lstrip("/").replace("/", os.sep))
        if os.path.exists(fisico):
            fontes[rel] = rp.ler_fonte(fisico)
    linhas = []
    for prod in producoes:
        fisico = os.path.join(dest, prod.lstrip("/").replace("/", os.sep))
        if not os.path.exists(fisico):
            raise RuntimeError("arquivo de producao ausente no commit: %s" % prod)
        nome = os.path.basename(prod)[:-5]
        pacote = rp.pacote_de(fisico)
        achados = []
        for rel, fonte in fontes.items():
            if rel == prod:
                continue
            formas = referencias(fonte, nome, pacote)
            if formas:
                achados.append("%s [%s]" % (rel, ",".join(formas)))
        linhas.append([repo, prod, pacote, len(fontes), len(achados), " | ".join(achados)])
    return linhas, len(fontes)


def feitos():
    if not os.path.exists(LOG):
        return set()
    return {r["github_repo"] for r in c.ler_csv(LOG) if r["status"] == "OK"}


def varrer():
    rp.carregar_step1()
    commit_de = {m["github_repo"]: m["head_atual"] for m in c.ler_mapa().values()}
    por_repo = collections.defaultdict(list)
    for r in c.ler_csv(AMOSTRA):
        por_repo[r["github_repo"]].append(r["production_path"])
    ja = feitos()
    alvo = [r for r in sorted(por_repo) if r not in ja]
    print("%d repositorios a varrer (%d ja no log)" % (len(alvo), len(ja)))
    os.makedirs(rp.CLONES, exist_ok=True)
    for i, repo in enumerate(alvo, 1):
        t0 = time.time()
        dest = os.path.join(rp.CLONES, "recall-" + repo)
        try:
            linhas, n = varrer_repo(repo, por_repo[repo], commit_de.get(repo), dest)
            rp.anexar(SAIDA, CAB_SAIDA, linhas)
            rp.anexar(LOG, CAB_LOG, [[repo, "OK", len(linhas), n, int(time.time() - t0), ""]])
            print("[%d/%d] %s: %d arquivos de teste, %d com referencia  (%.0fs)" % (
                i, len(alvo), repo, n, sum(1 for l in linhas if l[4]), time.time() - t0),
                flush=True)
        except Exception as e:                                    # noqa: BLE001
            rp.anexar(LOG, CAB_LOG, [[repo, "ERRO", len(por_repo[repo]), 0,
                                      int(time.time() - t0), str(e)[:300]]])
            print("[%d/%d] %s: ERRO %s" % (i, len(alvo), repo, str(e)[:200]), flush=True)
        finally:
            rp.jb.rmtree(dest)


def limite_superior(x, n, conf=0.95):
    """Limite superior de Clopper-Pearson, por bissecao (sem scipy)."""
    if x == n:
        return 1.0
    alvo = (1 - conf) / 2 if x else 1 - conf
    def cauda(p):   # P(X <= x | n, p)
        return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(x + 1))
    lo, hi = x / n, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cauda(mid) > alvo else (lo, mid)
    return hi


def apurar():
    """Separa as referencias achadas em duas: vindas de um teste que o JNose analisou
    (test_classes.csv) - perda do binding, o teste tem medida e poderia entrar no estudo -
    e vindas de arquivo fora desse universo (teste jtreg, utilitario de teste, classe sem
    padrao de nome do JNose), que nao tem medida de test smell e nao entraria de todo jeito."""
    amostra = c.ler_csv(AMOSTRA)
    saida = {(r["github_repo"], r["production_path"]): r for r in c.ler_csv(SAIDA)}         if os.path.exists(SAIDA) else {}
    faltam = [a for a in amostra if (a["github_repo"], a["production_path"]) not in saida]
    if faltam:
        print("!! %d arquivos ainda sem varredura (rode --varrer)" % len(faltam))
    jnose = {(r["github_repo"], r["path"]) for r in c.ler_csv(os.path.join(c.DADOS, "test_classes.csv"))}
    total = sum(1 for r in c.ler_csv(os.path.join(c.DADOS, "production_files.csv"))
                if r["motivo_sem_ligacao"] == "sem_ligacao_resolvida")
    n = len(saida)
    perdidos, fora = [], []
    for r in saida.values():
        refs = [x for x in r["referencias"].split(" | ") if x]
        caminhos = [x.split(" [")[0] for x in refs]
        if any((r["github_repo"], t) in jnose for t in caminhos):
            perdidos.append(r)
        elif refs:
            fora.append(r)
    print("arquivos varridos: %d de %d sorteados (universo: %d sem ligacao)"
          % (n, len(amostra), total))
    if not n:
        return
    for rotulo, grupo in (("referenciados por teste que o JNose analisou (perda do binding)", perdidos),
                          ("referenciados so por arquivo fora do universo do JNose", fora)):
        ls = limite_superior(len(grupo), n)
        print("%s: %d  (%.1f%%; limite superior 95%%: %.1f%%, ~%d arquivos no universo)"
              % (rotulo, len(grupo), 100 * len(grupo) / n, 100 * ls, round(ls * total)))
    for rotulo, grupo in (("PERDA DO BINDING", perdidos), ("FORA DO JNOSE", fora)):
        for r in grupo:
            print("\n[%s] %s %s" % (rotulo, r["github_repo"], r["production_path"]))
            for ref in r["referencias"].split(" | ")[:6]:
                t = ref.split(" [")[0]
                print("    %s%s" % (ref, "" if (r["github_repo"], t) in jnose else "   (fora do JNose)"))


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sortear", action="store_true")
    g.add_argument("--varrer", action="store_true")
    g.add_argument("--apurar", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if args.sortear:
        sortear()
    elif args.varrer:
        varrer()
    else:
        apurar()


if __name__ == "__main__":
    main()
