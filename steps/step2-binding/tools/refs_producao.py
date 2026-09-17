r"""Estrategia 3 do binding: liga teste a producao por referencia estatica no codigo.

    dados/refs_producao.csv   1 linha por par (producao, teste) com evidencia no codigo
    dados/refs_log.csv        1 linha por repositorio processado (retomavel)

Por que existe: caminho_exato e convencao juntas ligam 17,7% das amostras, e quase nao se
somam (15,8% + 1,7%) - erram nos mesmos casos. Com isso o estrato positivo_confiavel fica
com 44 amostras e feature envy com 4, o que nao sustenta analise por smell. O gargalo do
artigo e a cobertura do binding, nao a regra de rotulo.

A ligacao aqui nao depende de o teste se chamar XTest nem de o jnose-core ter resolvido o
nome da classe (que esta errado em 6,4% das linhas). Ela pergunta uma coisa so: este
arquivo de teste referencia este tipo de producao?

Tres evidencias, gravadas na coluna evidencia, da mais forte para a mais fraca:

  import_fqn     o teste tem "import <pacote>.<Tipo>;" exato. Nao ha ambiguidade.
  wildcard       o teste tem "import <pacote>.*;" e menciona o identificador <Tipo>.
  mesmo_pacote   teste e producao declaram o mesmo package e o teste menciona <Tipo>.
                 Java nao exige import nesse caso, entao e ligacao legitima - mas e a
                 unica das tres que depende de casar identificador solto, e por isso a
                 mais sujeita a falso positivo (um <Tipo> homonimo importado de outro
                 pacote, por exemplo).

A mencao ao identificador e buscada no codigo SEM comentarios nem literais de string,
reusando o _sem_comentarios() do jnose_batch.py do step 1 - a mesma funcao que ja foi
validada la contra o oraculo de JavaParser. Reusar em vez de reescrever evita ter duas
heuristicas de texto diferentes no mesmo experimento.

O que esta estrategia NAO afirma: que o teste testa aquela classe. Referenciar e condicao
necessaria, nao suficiente - um teste pode instanciar uma classe so como fixture. E por
isso que a evidencia vai numa coluna e que auditar_binding.py sorteia pares para
conferencia manual: o artigo precisa reportar a precisao medida, nao presumida.

Uso:
    python refs_producao.py                 # todos os HASH_OK ainda nao processados
    python refs_producao.py --refazer       # ignora o log e reprocessa tudo
    python refs_producao.py storm hadoop    # so os repositorios cujo nome casar
    python refs_producao.py --limite 5      # piloto

Retomavel: repositorios ja no refs_log.csv sao pulados. Interromper e reexecutar e seguro.
Os clones sao temporarios e removidos depois de cada repositorio.
"""
import argparse
import collections
import csv
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

CLONES = os.environ.get("JNOSE_PROJECTS",
                        os.path.join(os.path.expanduser("~"), ".jnose_projects"))

SAIDA = os.path.join(c.DADOS, "refs_producao.csv")
LOG = os.path.join(c.DADOS, "refs_log.csv")

CAB_SAIDA = ["github_repo", "production_path", "test_path", "evidencia"]
CAB_LOG = ["github_repo", "status", "n_producao", "n_testes", "n_pares", "segundos", "detalhe"]

PACOTE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)
IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)(\.\*)?\s*;", re.M)

jb = None   # jnose_batch do step 1, carregado em carregar_step1()


def carregar_step1():
    """Importa o jnose_batch.py do step 1 para reusar _sem_comentarios, clone e rmtree.

    Mesmo padrao que o validar_filtro.py do step 1 usa: o script e carregado por caminho
    porque os steps nao sao um pacote Python instalavel.
    """
    global jb
    caminho = os.path.join(c.STEP1, "tools", "jnose_batch.py")
    if not os.path.exists(caminho):
        sys.exit("nao achei o jnose_batch.py do step 1 em %s" % caminho)
    spec = importlib.util.spec_from_file_location("jb", caminho)
    jb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jb)


def ler_fonte(caminho):
    """Le um .java tolerando encoding: os repositorios do lote tem de tudo."""
    with open(caminho, "rb") as fh:
        bruto = fh.read()
    for enc in ("utf-8", "latin-1"):
        try:
            return bruto.decode(enc)
        except UnicodeDecodeError:
            continue
    return bruto.decode("utf-8", errors="replace")


def analisar_teste(caminho):
    """Devolve (pacote, imports_exatos, pacotes_wildcard, identificadores) de um arquivo de teste."""
    fonte = ler_fonte(caminho)
    # package e import sao lidos do fonte cru: eles nunca aparecem dentro de comentario de
    # forma que importe, e _sem_comentarios pode reescrever espacos.
    pacote_m = PACOTE.search(fonte)
    pacote = pacote_m.group(1) if pacote_m else ""

    exatos, wildcards = set(), set()
    for alvo, estrela in IMPORT.findall(fonte):
        if estrela:
            wildcards.add(alvo)
        else:
            exatos.add(alvo)

    # Para a mencao de identificador, comentarios e literais precisam sair: um nome de
    # classe citado no javadoc nao e referencia.
    limpo = jb._sem_comentarios(fonte)
    identificadores = set(re.findall(r"[A-Za-z_$][\w$]*", limpo))
    return pacote, exatos, wildcards, identificadores


def pacote_de(caminho):
    fonte = ler_fonte(caminho)
    m = PACOTE.search(fonte)
    return m.group(1) if m else ""


def clone_esparso(repo, dest, caminhos):
    """Clona so os arquivos .java de que este repositorio precisa, e devolve o HEAD.

    O step 1 clonava inteiro porque o JNose precisa varrer o projeto. Aqui sabemos
    exatamente quais arquivos vamos abrir - as classes de teste do test_classes.csv e os
    arquivos de producao anotados - entao clone parcial mais sparse-checkout evita baixar
    o resto. Em test-smells-SapMachine (fork do OpenJDK) a diferenca medida foi de
    mais de 20 min e >1 GB para 19 s e 39 MB.

    Duas pegadinhas:

      - --filter=blob:none deixa o repositorio dependente do remoto para buscar blobs
        depois (promisor remote), e o checkout dispara essa busca. O http.sslBackend tem
        que ficar gravado na config do CLONE, nao passado com -c na linha do clone, senao
        o fetch seguinte falha com erro de certificado.
      - --no-cone porque os caminhos sao arquivos avulsos espalhados, nao diretorios; no
        modo cone o git so aceita prefixos de diretorio.

    Os caminhos vem com barra inicial dos nossos CSVs, o que em padrao gitignore ancora na
    raiz do repositorio - exatamente o que queremos.
    """
    if os.path.exists(dest) and not jb.rmtree(dest):
        raise RuntimeError("nao consegui remover clone anterior: " + dest)
    url = "https://github.com/cristianritter/%s.git" % repo
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")

    # encoding explicito em toda conversa com o git: em modo texto o Python usaria a
    # pagina de codigo do Windows (cp1252), e repositorios com nome de arquivo fora dela
    # - alibaba/atlas tem caminhos em chines - falham ao passar a lista pelo stdin.
    def git(*args, **kw):
        return subprocess.run(["git"] + list(args), check=True, timeout=3600, env=env,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", **kw)

    git("-c", "http.sslBackend=schannel", "clone", "--depth", "1", "--filter=blob:none",
        "--no-checkout", "-q", url, dest)
    git("-C", dest, "config", "http.sslBackend", "schannel")
    git("-C", dest, "sparse-checkout", "init", "--no-cone")
    subprocess.run(["git", "-C", dest, "sparse-checkout", "set", "--stdin"],
                   input=("\n".join(caminhos) + "\n").encode("utf-8"), check=True,
                   timeout=3600, env=env, capture_output=True)
    git("-C", dest, "checkout", "-q")
    return git("-C", dest, "rev-parse", "HEAD").stdout.strip()


def processar(repo, producoes, testes, dest, commit_esperado=None):
    """Clona o repositorio e devolve os pares (production_path, test_path, evidencia)."""
    head = clone_esparso(repo, dest, list(testes) + list(producoes))
    if commit_esperado and head != commit_esperado:
        # O step 1 ja conferiu isto, mas o espelho pode ter recebido commits depois. Se
        # divergir, os caminhos do MLCQ nao valem mais e o par seria ficticio.
        raise RuntimeError("HEAD %s difere do esperado %s" % (head[:12], commit_esperado[:12]))

    # tipo de producao: nome simples + pacote declarado no proprio arquivo
    alvos = []
    faltando = 0
    for rel in producoes:
        fisico = os.path.join(dest, rel.lstrip("/").replace("/", os.sep))
        if not os.path.exists(fisico):
            # O HASH_OK garante o mesmo commit, entao o arquivo deveria existir. Se nao
            # existe, e informacao: entra no detalhe do log em vez de virar um par perdido.
            faltando += 1
            continue
        nome = os.path.basename(rel)[:-5]
        alvos.append((rel, nome, pacote_de(fisico)))

    pares = []
    for rel in testes:
        fisico = os.path.join(dest, rel.lstrip("/").replace("/", os.sep))
        if not os.path.exists(fisico):
            continue
        pacote_t, exatos, wildcards, ids = analisar_teste(fisico)
        for prod_rel, nome, pacote_p in alvos:
            fqn = "%s.%s" % (pacote_p, nome) if pacote_p else nome
            if fqn in exatos:
                pares.append((prod_rel, rel, "import_fqn"))
            elif nome in ids and pacote_p and pacote_p in wildcards:
                pares.append((prod_rel, rel, "wildcard"))
            elif nome in ids and pacote_p and pacote_p == pacote_t:
                pares.append((prod_rel, rel, "mesmo_pacote"))
    return pares, faltando


def ja_feitos():
    if not os.path.exists(LOG):
        return set()
    with open(LOG, encoding="utf-8-sig") as fh:
        return {r["github_repo"] for r in csv.DictReader(fh) if r["status"] == "OK"}


def anexar(caminho, cabecalho, linhas):
    novo = not os.path.exists(caminho)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "a", newline="", encoding="utf-8-sig" if novo else "utf-8") as fh:
        w = csv.writer(fh)
        if novo:
            w.writerow(cabecalho)
        for linha in linhas:
            w.writerow(linha)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("filtro", nargs="*", help="so repositorios cujo nome contenha isto")
    ap.add_argument("--limite", type=int, help="processa no maximo N repositorios")
    ap.add_argument("--refazer", action="store_true", help="ignora o log e reprocessa")
    args = ap.parse_args()

    carregar_step1()

    mapa = c.ler_mapa()
    commit_de = {m["github_repo"]: m["head_atual"] for m in mapa.values()}

    prod_por_repo = collections.defaultdict(set)
    for r in c.ler_csv(os.path.join(c.DADOS, "production_files.csv")):
        if r["repo_status"] == "HASH_OK":
            prod_por_repo[r["github_repo"]].add(r["production_path"])

    testes_por_repo = collections.defaultdict(list)
    for r in c.ler_csv(os.path.join(c.DADOS, "test_classes.csv")):
        testes_por_repo[r["github_repo"]].append(r["path"])

    feitos = set() if args.refazer else ja_feitos()
    if args.refazer and os.path.exists(SAIDA):
        os.remove(SAIDA)

    alvo = sorted(prod_por_repo)
    if args.filtro:
        alvo = [r for r in alvo if any(f.lower() in r.lower() for f in args.filtro)]
    alvo = [r for r in alvo if r not in feitos]
    if args.limite:
        alvo = alvo[:args.limite]

    print("%d repositorios a processar (%d ja no log)" % (len(alvo), len(feitos)))
    os.makedirs(CLONES, exist_ok=True)
    total = 0

    for i, repo in enumerate(alvo, 1):
        producoes = sorted(prod_por_repo[repo])
        testes = testes_por_repo.get(repo, [])
        dest = os.path.join(CLONES, repo)
        t0 = time.time()
        print("[%d/%d] %s  (%d producao, %d testes)" % (i, len(alvo), repo,
                                                        len(producoes), len(testes)))
        if not testes:
            anexar(LOG, CAB_LOG, [[repo, "OK", len(producoes), 0, 0, 0,
                                   "projeto sem classe de teste"]])
            continue
        try:
            pares, faltando = processar(repo, producoes, testes, dest, commit_de.get(repo))
            anexar(SAIDA, CAB_SAIDA, [[repo, p, t, e] for p, t, e in pares])
            detalhe = "%d arquivos de producao ausentes no clone" % faltando if faltando else ""
            anexar(LOG, CAB_LOG, [[repo, "OK", len(producoes), len(testes), len(pares),
                                   int(time.time() - t0), detalhe]])
            total += len(pares)
            print("      %d pares  (%.0fs)%s" % (len(pares), time.time() - t0,
                                                 "  " + detalhe if detalhe else ""))
        except Exception as e:                                    # noqa: BLE001
            # Um repositorio que falha nao pode derrubar o lote: fica no log com ERRO e
            # e reprocessado numa proxima execucao.
            anexar(LOG, CAB_LOG, [[repo, "ERRO", len(producoes), len(testes), 0,
                                   int(time.time() - t0), str(e)[:300]]])
            print("      ERRO: %s" % str(e)[:200])
        finally:
            jb.rmtree(dest)

    print("\n%d pares gravados nesta execucao em %s" % (total, SAIDA))
    print("rode agora: python tools/binding.py   (para incorporar a estrategia)")


if __name__ == "__main__":
    main()
