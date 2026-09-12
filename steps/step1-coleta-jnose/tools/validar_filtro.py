"""Confere o filtro de arquivos do jnose_batch contra um oraculo independente.

O jnose_batch remove do clone, antes da analise, os arquivos que fariam o JNose
estourar um NullPointerException (ver README, secao "O defeito que travava a
coleta"). Esse filtro e uma heuristica em Python: le o texto do arquivo, ignora
comentarios e literais, e procura uma class/interface no nivel de topo.

Heuristica de texto erra. Este script compara o filtro com o AchaNulos.java, que
usa o MESMO javaparser-core de dentro do jar do JNose e replica a travessia do
flowClass no de no - ou seja, decide pelo AST, nao por regex. Se os dois
divergirem em algum repositorio, o filtro precisa ser corrigido.

Para cada repositorio imprime:
  oraculo   arquivos que o JavaParser diz que deixariam TestClass.name nulo
  filtro    o que o remover_testes_sem_classe() removeria hoje
  sem_junit arquivos sem class/interface de topo mas sem import de JUnit; o
            isTestFile os rejeita, entao remove-los seria inofensivo mas inutil

Uso:
    python validar_filtro.py                     # os 12 repositorios recuperados
    python validar_filtro.py apache/storm ...    # repositorios especificos
    python validar_filtro.py --todos             # todos os HASH_OK (lento, ~450 clones)
"""
import argparse
import csv
import importlib.util
import os
import shutil
import subprocess
import sys
import zipfile

STEP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(STEP, "tools")
MAPA = os.path.join(STEP, "dados", "repos_map.csv")

JNOSE_DIR = os.environ.get("JNOSE_DIR",
                           r"C:\Users\crist\Documents\Mestrado PPGCC\jnose-tests-smell")
JNOSE_JAR = os.path.join(JNOSE_DIR, "jnose-2.5.0.jar")
JAVA_BIN = os.path.dirname(os.environ.get("JAVA_EXE",
                                          r"C:\Program Files\Java\jdk-26.0.2\bin\java.exe"))
JAVA = os.path.join(JAVA_BIN, "java.exe")
JAVAC = os.path.join(JAVA_BIN, "javac.exe")

# os 12 que precisaram do filtro para concluir
RECUPERADOS = [
    "apache/bahir-flink", "apache/openejb", "apache/sis", "apache/storm", "apache/tomee",
    "eclipse/xtext-core", "facebook/buck", "oracle/visualvm", "spring-projects/spring-boot",
    "spring-projects/spring-data-gemfire", "spring-projects/spring-framework",
    "spring-projects/spring-integration",
]

jb = None  # o jnose_batch, carregado em preparar()


def preparar(trabalho):
    """Extrai o javaparser de dentro do jar do JNose e compila o oraculo."""
    global jb
    spec = importlib.util.spec_from_file_location("jb", os.path.join(TOOLS, "jnose_batch.py"))
    jb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jb)

    if not os.path.exists(JNOSE_JAR):
        sys.exit("jar do JNose nao encontrado em %s (defina JNOSE_DIR)" % JNOSE_JAR)
    with zipfile.ZipFile(JNOSE_JAR) as z:
        nome = next(n for n in z.namelist() if "javaparser-core" in n and n.endswith(".jar"))
        z.extract(nome, trabalho)
    jp = os.path.join(trabalho, nome.replace("/", os.sep))

    classes = os.path.join(trabalho, "classes")
    os.makedirs(classes, exist_ok=True)
    subprocess.run([JAVAC, "-cp", jp, "-d", classes, os.path.join(TOOLS, "AchaNulos.java")],
                   check=True, capture_output=True, text=True)
    return jp + os.pathsep + classes


def candidatos(dest):
    for raiz, dirs, arquivos in os.walk(dest):
        dirs[:] = [d for d in dirs if d not in jb.IGNORAR_DIRS]
        for nome in arquivos:
            if nome.endswith(".java") and jb.NOME_DE_TESTE.match(nome[:-5].lower()):
                yield os.path.join(raiz, nome)


def rel(dest, caminho):
    return os.path.relpath(caminho, dest).replace(os.sep, "/")


def pelo_oraculo(classpath, dest):
    saida = subprocess.run([JAVA, "-cp", classpath, "AchaNulos", dest],
                           capture_output=True, text=True, timeout=1800).stdout
    return {l.strip().replace("\\", "/") for l in saida.splitlines() if l.strip()}


def pelo_filtro(dest):
    return {rel(dest, c) for c in candidatos(dest) if jb.nome_ficaria_nulo(c)}


def sem_import_junit(dest):
    achados = set()
    for caminho in candidatos(dest):
        try:
            with open(caminho, encoding="utf-8", errors="ignore") as fh:
                texto = fh.read()
        except OSError:
            continue
        if not jb.IMPORTA_JUNIT.search(texto) and \
                not jb._declara_classe_ou_interface(jb._sem_comentarios(texto)):
            achados.add(rel(dest, caminho))
    return achados


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repos", nargs="*", help="repositorios MLCQ (owner/nome)")
    ap.add_argument("--todos", action="store_true", help="todos os HASH_OK do repos_map")
    ap.add_argument("--trabalho", default=os.path.join(STEP, ".validacao"),
                    help="pasta temporaria para clones e classes")
    args = ap.parse_args()

    with open(MAPA, encoding="utf-8") as fh:
        mapa = {r["mlcq_repo"]: r for r in csv.DictReader(fh)}

    if args.todos:
        alvos = [k for k, r in mapa.items() if r["status"] == "HASH_OK"]
    else:
        alvos = args.repos or RECUPERADOS
    faltando = [a for a in alvos if a not in mapa]
    if faltando:
        sys.exit("nao estao no repos_map: %s" % ", ".join(faltando))

    os.makedirs(args.trabalho, exist_ok=True)
    classpath = preparar(args.trabalho)

    print("%-36s %8s %7s %10s  %s" % ("repo", "oraculo", "filtro", "sem_junit", "veredito"))
    divergencias = []
    for mlcq in alvos:
        espelho = mapa[mlcq]["github_repo"]
        dest = os.path.join(args.trabalho, espelho)
        shutil.rmtree(dest, ignore_errors=True)
        url = "https://github.com/cristianritter/%s.git" % espelho
        clone = subprocess.run(["git", "-c", "http.sslBackend=schannel", "clone", "--depth", "1",
                                "-q", url, dest], capture_output=True, text=True, timeout=3600)
        if clone.returncode != 0:
            print("%-36s  CLONE FALHOU: %s" % (mlcq, clone.stderr.strip()[:60]))
            continue
        try:
            o, p, sj = pelo_oraculo(classpath, dest), pelo_filtro(dest), sem_import_junit(dest)
            if o != p:
                divergencias.append((mlcq, sorted(o - p), sorted(p - o)))
            print("%-36s %8d %7d %10d  %s"
                  % (mlcq, len(o), len(p), len(sj), "identicos" if o == p else "DIVERGEM"))
        finally:
            shutil.rmtree(dest, ignore_errors=True)
        sys.stdout.flush()

    print()
    for mlcq, so_oraculo, so_filtro in divergencias:
        print("DIVERGENCIA em %s" % mlcq)
        for f in so_oraculo:
            print("   o filtro deixaria passar: %s" % f)
        for f in so_filtro:
            print("   o filtro removeria a mais: %s" % f)
    if not divergencias:
        print("Filtro e oraculo coincidem em todos os repositorios verificados.")
    return 1 if divergencias else 0


if __name__ == "__main__":
    sys.exit(main())
