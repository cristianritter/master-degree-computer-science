"""Roda os repositorios do MLCQ pelo JNose, um por vez, exportando os CSVs.

Contorna dois bugs do JNose 2.5.0:
  - aba Projects quebrada (github-api x Jackson): o projeto e inserido direto no jnose.db
  - config de smells so em memoria: reaplicada a cada execucao
"""
import csv
import gzip
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import zipfile

import requests

# Caminhos da maquina, ajustaveis por variavel de ambiente (ver README).
BASE = os.environ.get("JNOSE_URL", "http://localhost:8080")
JNOSE_DIR = os.environ.get("JNOSE_DIR",
                           r"C:\Users\crist\Documents\Mestrado PPGCC\jnose-tests-smell")
JAVA = os.environ.get("JAVA_EXE", r"C:\Program Files\Java\jdk-26.0.2\bin\java.exe")
DB = os.path.join(JNOSE_DIR, "jnose.db")
# onde os clones sao feitos; precisa de espaco para o maior repo do lote
PROJECTS = os.environ.get("JNOSE_PROJECTS",
                          os.path.join(os.path.expanduser("~"), ".jnose_projects"))

# entradas e saidas ficam sempre relativas a pasta do step, nao a uma pasta fixa
STEP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(STEP, "reports")
MAP = os.path.join(STEP, "dados", "repos_map.csv")
LOG = os.path.join(REPORTS, "run_log.csv")

# A configuracao padrao do JNose (TestSmellDetectorConfig liga os 21 smells) menos o Unknown
# Test. O detector de Unknown Test do jnose-core 0.9.4 (UnknownTest.java, linha 58) chama
# getBody().get() sem checar se o metodo tem corpo; em metodo abstrato isso lanca
# NoSuchElementException, e o JNose descarta a analise da CLASSE INTEIRA, de todos os
# smells. O efeito e medido rodando a configuracao padrao inteira (--config-padrao, abaixo)
# e comparando com esta (tools/efeito_unknown_test.py; README, secao 4).
SMELLS_ON = [
    "cbAssertionRoulette", "cbConditionalTestLogic", "cbConstructorInitialization",
    "cbDefaultTest", "cbDependentTest", "cbDuplicateAssert", "cbEagerTest", "cbEmptyTest",
    "cbExceptionCatchingThrowing", "cbGeneralFixture", "cbIgnoredTest", "cbLazyTest",
    "cbMagicNumberTest", "cbMysteryGuest", "cbPrintStatement", "cbRedundantAssertion",
    "cbResourceOptimism", "cbSensitiveEquality", "cbSleepyTest", "cbVerboseTest",
]

# --config-padrao: os 21 smells, com o Unknown Test, gravando em reports-config-padrao/.
# Serve so para medir o defeito; a coleta do estudo e a de reports/.
if "--config-padrao" in sys.argv:
    sys.argv.remove("--config-padrao")
    SMELLS_ON = sorted(SMELLS_ON + ["cbUnknownTest"])
    REPORTS = os.path.join(STEP, "reports-config-padrao")
    LOG = os.path.join(REPORTS, "run_log.csv")

PAGES = ["bytestsmells", "byclasstest"]

# de quantos em quantos repositorios o JNose e reciclado, para nao acumular memoria
RESTART_A_CADA = 15

# tempo maximo por analise; JNOSE_TIMEOUT permite alongar no repasse dos projetos grandes
TIMEOUT_ANALISE = int(os.environ.get("JNOSE_TIMEOUT", "1200"))

JSTACK = os.path.join(os.path.dirname(JAVA), "jstack.exe")
JNOSE_LOGS = os.path.join(REPORTS, "console-jnose")

# Janela usada para decidir que a analise morreu. O JNose engole a excecao do
# getFilesTest e deixa a porcentagem parada em 25: a tela de um projeto morto e
# identica a de um projeto processando, entao a unica forma de distinguir e olhar
# o processo. A analise mais lenta que deu certo levou 420s no total, entao uma
# janela de alguns minutos sem CPU nem thread de analise nao tem falso positivo.
MORTO_JANELA = int(os.environ.get("JNOSE_JANELA_MORTO", "180"))
MORTO_CPU_MIN = 2.0


class AnaliseMorta(TimeoutError):
    """A thread de analise do JNose morreu; esperar mais nao adianta."""


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def powershell(cmd, timeout=120):
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                          capture_output=True, text=True, timeout=timeout).stdout.strip()


def jnose_pid():
    saida = powershell("(Get-CimInstance Win32_Process -Filter \"Name='java.exe'\""
                       " | Select-Object -First 1).ProcessId", timeout=60)
    return int(saida) if saida.isdigit() else None


def cpu_segundos(pid):
    """Tempo de CPU acumulado do JVM. None se nao der para ler."""
    saida = powershell("(Get-Process -Id %d -ErrorAction SilentlyContinue).CPU" % pid, timeout=60)
    try:
        return float(saida.replace(",", "."))  # o PowerShell usa virgula em pt-BR
    except ValueError:
        return None


def analise_viva(pid):
    """Ainda existe thread do JNose rodando a analise? Sem isso o pct nunca muda."""
    try:
        dump = subprocess.run([JSTACK, str(pid)], capture_output=True, text=True,
                              timeout=180).stdout
    except (OSError, subprocess.SubprocessError):
        return True  # sem dump nao da para afirmar que morreu
    return "arieslab" in dump


# ---------------------------------------------------------------- JNose HTTP
def ajax(session, url, timeout=900, **kw):
    base = url.split("/")[-1].split(";")[0].split("?")[0]
    headers = {"Wicket-Ajax": "true", "Wicket-Ajax-BaseURL": base}
    return session.post(url, headers=headers, timeout=timeout, **kw)


def apply_config(session):
    """Reaplica a selecao de smells, que o JNose guarda so em memoria."""
    html = session.get(BASE + "/config", timeout=60).text
    action = re.search(r'action="\./config([^"]*)"', html).group(1)
    session.post(BASE + "/config" + action, data=[(c, "on") for c in SMELLS_ON],
                 timeout=120, allow_redirects=False)
    html = session.get(BASE + "/config", timeout=60).text
    on = set(re.findall(r'<input wicket:id="(cb\w+)" type="checkbox" checked', html))
    if on != set(SMELLS_ON):
        raise RuntimeError("config divergente: sobrando=%s faltando=%s"
                           % (on - set(SMELLS_ON), set(SMELLS_ON) - on))
    log("config aplicada: %d smells ligados" % len(on))


# ------------------------------------------------------------------ jnose.db
def db_reset_to(project=None):
    """Deixa a tabela Projeto com no maximo um projeto: o da vez."""
    con = sqlite3.connect(DB)
    con.execute("delete from Projeto")
    if project:
        con.execute(
            "insert into Projeto (id,dateUpdate,junitVersion,name,path,stars,url)"
            " values (?,?,?,?,?,?,?)",
            (1001, "2019-01-01 00:00:00.000", project["junit"], project["name"],
             project["path"], 0, project["url"]))
    con.execute("update Projeto_SEQ set next_val=5000")
    con.commit()
    con.close()


# O oraculo que decide quais arquivos derrubariam o JNose (ver remover_testes_sem_classe).
# Roda com o javaparser-core de dentro do proprio jar do JNose: a decisao sai do mesmo
# parser que o JNose usa, nao de uma heuristica de texto.
JAVAC = os.path.join(os.path.dirname(JAVA), "javac.exe")
JNOSE_JAR = os.path.join(JNOSE_DIR, "jnose-2.5.0.jar")
ORACULO_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AchaNulos.java")
ORACULO_DIR = os.path.join(STEP, ".oraculo")
_classpath_oraculo = None


def _sem_comentarios(texto):
    """Remove comentarios e literais, preservando as chaves que delimitam escopo."""
    saida, i, n = [], 0, len(texto)
    while i < n:
        par = texto[i:i + 2]
        if par == "//":
            j = texto.find("\n", i)
            i = n if j < 0 else j
        elif par == "/*":
            j = texto.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif texto[i] in "\"'":
            # literal de Java nao atravessa quebra de linha; se atravessar, nao era
            # literal (arquivo de template, por exemplo) e a aspa vale como texto
            aspa, j = texto[i], i + 1
            while j < n and texto[j] != aspa and texto[j] != "\n":
                j += 2 if texto[j] == "\\" else 1
            if j < n and texto[j] == aspa:
                i = j + 1
            else:
                saida.append(texto[i])
                i += 1
        else:
            saida.append(texto[i])
            i += 1
    return "".join(saida)


def classpath_oraculo():
    """Extrai o javaparser do jar do JNose e compila o AchaNulos.java, uma vez por execucao."""
    global _classpath_oraculo
    if _classpath_oraculo is None:
        with zipfile.ZipFile(JNOSE_JAR) as z:
            nome = next(n for n in z.namelist()
                        if "javaparser-core" in n and n.endswith(".jar"))
            z.extract(nome, ORACULO_DIR)
        jp = os.path.join(ORACULO_DIR, nome.replace("/", os.sep))
        classes = os.path.join(ORACULO_DIR, "classes")
        os.makedirs(classes, exist_ok=True)
        subprocess.run([JAVAC, "-cp", jp, "-d", classes, ORACULO_SRC],
                       check=True, capture_output=True, text=True)
        _classpath_oraculo = jp + os.pathsep + classes
    return _classpath_oraculo


def remover_testes_sem_classe(dest):
    """Tira do clone os arquivos que o JNose aceitaria como teste sem achar classe neles.

    O JNose escolhe o arquivo pelo nome e aceita como teste qualquer um que importe
    JUnit, sem verificar se achou uma classe. Quando nao achou, o getFilesTest estoura
    um NullPointerException que aborta a analise do projeto INTEIRO, nao so do arquivo -
    e em silencio, deixando a tela parada em 25%. Quem decide quais sao esses arquivos e
    o AchaNulos.java, que replica isTestFile + flowClass sobre o AST do JavaParser.
    Esses arquivos nao tem classe de teste para analisar (sao anotacoes de @Category/@Tag,
    enums ou arquivos vazios), entao remove-los nao tira nada da coleta.
    """
    saida = subprocess.run([JAVA, "-cp", classpath_oraculo(), "AchaNulos", dest],
                           capture_output=True, text=True, timeout=1800, check=True).stdout
    removidos = []
    for linha in saida.splitlines():
        relativo = linha.strip()
        if not relativo:
            continue
        os.remove(os.path.join(dest, relativo))   # falhar aqui e melhor que analisar errado
        removidos.append(relativo)
    return removidos


def detect_junit(path):
    """Qual API de teste o projeto usa. Nunca devolve None: e o valor que o JNose filtra."""
    hits = {"JUnit5": 0, "JUnit4": 0, "JUnit3": 0}
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in (".git", "target", "build", "node_modules")]
        for name in files:
            if not name.endswith(".java"):
                continue
            try:
                with open(os.path.join(root, name), encoding="utf-8", errors="ignore") as fh:
                    src = fh.read()
            except OSError:
                continue
            if "org.junit.jupiter" in src:
                hits["JUnit5"] += 1
            elif "import org.junit." in src:
                hits["JUnit4"] += 1
            elif "junit.framework" in src:
                hits["JUnit3"] += 1
    for version in ("JUnit5", "JUnit4", "JUnit3"):
        if hits[version]:
            return version
    return "JUnit4"


# --------------------------------------------------------------------- fluxo
def analyze(session, page, timeout_s=None):
    """Dispara a analise da pagina e devolve (csv_bytes, porcentagem_final)."""
    timeout_s = timeout_s or TIMEOUT_ANALISE
    html = session.get(BASE + "/" + page, timeout=60).text
    # o pageId do Wicket incrementa a cada pagina aberta na sessao, entao e lido da propria URL
    found = re.search(r'"u":"\./' + page + r'([^"?]*)\?(\d+)-(\d+)\.0-processarTodos"', html)
    if not found:
        raise RuntimeError(page + ": botao Analyze nao encontrado")
    path = BASE + "/" + page + found.group(1)
    page_id = found.group(2)
    ajax(session, "%s?%s-%s.0-processarTodos" % (path, page_id, found.group(3)), timeout=120)

    # O link de resultado so ganha href quando o projeto chega a 100%. Bater nele
    # re-renderiza a pagina (o que ja devolve o renderCount corrente) enquanto processa,
    # e responde 302 para a ResultPage quando termina.
    deadline = time.time() + timeout_s
    render_count, pct = 1, 0
    pid = jnose_pid()
    marco_t, marco_cpu = time.time(), cpu_segundos(pid) if pid else None
    while time.time() < deadline:
        resp = session.get("%s?%s-%d.-lvProjetos-0-lkResultado" % (path, page_id, render_count),
                           allow_redirects=False, timeout=300)
        body = resp.text
        if resp.status_code == 302:
            # pode ser a ResultPage (analise concluida) ou apenas um re-render da propria pagina
            body = session.get(resp.headers["Location"], timeout=300).text
            href = re.search(r'href="\./page\?([^"]*lkEsportCSV)"', body)
            if href:
                return session.get(BASE + "/wicket/page?" + href.group(1), timeout=600).content, pct
        got_pct = re.search(r'lbPorcentagem" id="[^"]*">(\d+)', body)
        if got_pct:
            pct = int(got_pct.group(1))
        got_rc = re.search(r'href="\./' + page + r'\?' + page_id + r'-(\d+)\.-lvProjetos-0-lkResultado"',
                           body)
        render_count = int(got_rc.group(1)) if got_rc else render_count + 1

        # o JVM ocioso e sem thread de analise significa que o JNose ja desistiu
        if pid and time.time() - marco_t >= MORTO_JANELA:
            cpu_agora = cpu_segundos(pid)
            gasto = None if None in (cpu_agora, marco_cpu) else cpu_agora - marco_cpu
            if gasto is not None and gasto < MORTO_CPU_MIN and not analise_viva(pid):
                raise AnaliseMorta(
                    "%s: analise morreu (pct=%d, %.1fs de CPU em %ds, sem thread do JNose)"
                    % (page, pct, gasto, MORTO_JANELA))
            marco_t, marco_cpu = time.time(), cpu_agora

        time.sleep(5)
    raise TimeoutError("%s: nao concluiu em %ds (ultimo pct=%d)" % (page, timeout_s, pct))


def rmtree(path):
    """Remove a arvore e devolve se conseguiu. Nunca levanta: limpeza nao pode derrubar o lote.

    Trata os somente-leitura que o git deixa em .git/objects e os arquivos que o JNose
    ainda mantem abertos logo apos uma analise.
    """
    def limpar(func, alvo, _exc):
        os.chmod(alvo, 0o700)
        func(alvo)

    for tentativa in range(4):
        if not os.path.exists(path):
            return True
        try:
            shutil.rmtree(path, onerror=limpar)
        except OSError:
            pass
        if not os.path.exists(path):
            return True
        time.sleep(3 * (tentativa + 1))
    return not os.path.exists(path)


def parar_jnose():
    """Derruba o JVM do JNose e comprime o console que ele deixou."""
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"Name='java.exe'\""
                    " | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                   capture_output=True, timeout=120)
    time.sleep(5)
    comprimir_consoles()


def comprimir_consoles():
    """Comprime os consoles ja fechados: no lote inteiro passam de 150 MB em texto."""
    if not os.path.isdir(JNOSE_LOGS):
        return
    for nome in sorted(os.listdir(JNOSE_LOGS)):
        if not nome.endswith((".out", ".err")):
            continue
        caminho = os.path.join(JNOSE_LOGS, nome)
        try:
            with open(caminho, "rb") as fh, gzip.open(caminho + ".gz", "wb") as gz:
                shutil.copyfileobj(fh, gz)
            os.remove(caminho)
        except OSError:
            continue  # ainda aberto pelo JVM: fica para o proximo restart


def restart_jnose(session):
    """Reinicia o JNose e reaplica a config. Usado quando uma analise trava.

    Sem isso as threads do JNose seguem rodando sobre o clone anterior, segurando
    arquivos e disputando CPU com os proximos repositorios.
    """
    log("  reiniciando o JNose")
    parar_jnose()
    # O JNose so reporta a falha do getFilesTest pelo LOGGER, que vai para o console.
    # Sem guardar essa saida a analise morre sem deixar rastro nenhum.
    os.makedirs(JNOSE_LOGS, exist_ok=True)
    marca = os.path.join(JNOSE_LOGS, time.strftime("%Y%m%d-%H%M%S"))
    log("  console do JNose em %s.{out,err}" % marca)
    # -Xmx limita o heap: sem isso o JVM cresce ao longo do lote ate sufocar a maquina
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Start-Process -FilePath '%s' -ArgumentList '-Xmx2g',"
                    "'-Djavax.net.ssl.trustStoreType=WINDOWS-ROOT','-jar','jnose-2.5.0.jar'"
                    " -WorkingDirectory '%s' -WindowStyle Hidden"
                    " -RedirectStandardOutput '%s.out' -RedirectStandardError '%s.err'"
                    % (JAVA, JNOSE_DIR, marca, marca)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    for _ in range(40):
        time.sleep(5)
        try:
            if session.get(BASE + "/config", timeout=10, allow_redirects=False).status_code:
                break
        except requests.RequestException:
            continue
    else:
        raise RuntimeError("JNose nao voltou depois do restart")
    session.cookies.clear()
    apply_config(session)


def clone(github_repo, dest):
    if os.path.exists(dest) and not rmtree(dest):
        raise RuntimeError("nao consegui remover clone anterior: " + dest)
    url = "https://github.com/cristianritter/%s.git" % github_repo
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    subprocess.run(["git", "-c", "http.sslBackend=schannel", "clone", "--depth", "1", "-q",
                    url, dest], check=True, timeout=3600, env=env)
    head = subprocess.run(["git", "-C", dest, "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    return head, url


# ---------------------------------------------------------------------- main
def load_done():
    if not os.path.exists(LOG):
        return set()
    # TIMEOUT entra junto: repetir um repo que trava o JNose so queima o lote de novo.
    # Eles ficam listados no run_log.csv para tratamento a parte.
    with open(LOG, encoding="utf-8") as fh:
        return {r["mlcq_repo"] for r in csv.DictReader(fh) if r["status"] in ("OK", "TIMEOUT", "MORTO")}


def append_log(row):
    novo = not os.path.exists(LOG)
    os.makedirs(REPORTS, exist_ok=True)
    with open(LOG, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if novo:
            writer.writerow(["mlcq_repo", "github_repo", "commit_esperado", "commit_clonado",
                             "junit", "status", "linhas_bytestsmells", "linhas_byclasstest",
                             "segundos", "detalhe"])
        writer.writerow(row)


def main():
    # argumento: um numero limita a quantidade, um texto filtra pelo nome do repo
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    limite = int(arg) if arg.isdigit() else 0
    with open(MAP, encoding="utf-8") as fh:
        alvos = [r for r in csv.DictReader(fh) if r["status"] == "HASH_OK"]
    concluidos = load_done()
    fila = [r for r in alvos if r["mlcq_repo"] not in concluidos]
    if arg == "--pendentes":
        # repassa tudo que nao terminou OK, usando o ultimo status registrado de cada repo
        ultimo = {}
        if os.path.exists(LOG):
            with open(LOG, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    ultimo[r["mlcq_repo"]] = r["status"]
        fila = [r for r in alvos if ultimo.get(r["mlcq_repo"], "") != "OK"]
    elif arg and not limite:
        # filtro explicito por nome ignora o run_log: serve justamente para repetir pendencias
        fila = [r for r in alvos if arg.lower() in r["mlcq_repo"].lower()]
    if limite:
        fila = fila[:limite]
    log("%d repos elegiveis, %d ja concluidos, processando %d"
        % (len(alvos), len(concluidos), len(fila)))

    session = requests.Session()
    try:
        session.get(BASE + "/config", timeout=15, allow_redirects=False)
    except requests.RequestException:
        log("JNose fora do ar; subindo")
        restart_jnose(session)
    apply_config(session)

    for i, row in enumerate(fila, 1):
        mlcq, gh, esperado = row["mlcq_repo"], row["github_repo"], row["commit_esperado"]
        dest = os.path.join(PROJECTS, gh)
        safe = mlcq.replace("/", "__")
        inicio = time.time()
        log("(%d/%d) %s -> %s" % (i, len(fila), mlcq, gh))
        if i > 1 and i % RESTART_A_CADA == 1:
            # o JNose nao libera memoria entre analises; reciclar evita sufocar a maquina
            try:
                restart_jnose(session)
            except Exception as falha:  # noqa: BLE001
                log("  aviso: restart periodico falhou: %s" % falha)
        try:
            head, url = clone(gh, dest)
            if head.lower() != esperado.lower():
                append_log([mlcq, gh, esperado, head, "", "MISMATCH", "", "",
                            int(time.time() - inicio),
                            "HEAD do clone diferente do commit da planilha"])
                log("  MISMATCH - pulando")
                continue
            sem_classe = remover_testes_sem_classe(dest)
            if sem_classe:
                log("  %d candidato(s) a teste sem classe removido(s): %s"
                    % (len(sem_classe), ", ".join(sem_classe[:3])
                       + (" ..." if len(sem_classe) > 3 else "")))
            junit = detect_junit(dest)
            db_reset_to({"name": gh, "path": dest, "url": url, "junit": junit})
            linhas = {}
            for page in PAGES:
                data, pct = analyze(session, page)
                # bytestsmells traz o codigo de cada metodo e passa de 1 GB no lote: sai
                # comprimido daqui mesmo, para o artefato versionado ser o que o script grava
                if page == "bytestsmells":
                    saida = os.path.join(REPORTS, page, safe + ".csv.gz")
                    abrir = lambda c: gzip.open(c, "wb")
                else:
                    saida = os.path.join(REPORTS, page, safe + ".csv")
                    abrir = lambda c: open(c, "wb")
                os.makedirs(os.path.dirname(saida), exist_ok=True)
                with abrir(saida) as fh:
                    fh.write(data)
                linhas[page] = max(data.count(b"\n") - 1, 0)
                log("  %s: %d linhas (%d%%)" % (page, linhas[page], pct))
            append_log([mlcq, gh, esperado, head, junit, "OK", linhas["bytestsmells"],
                        linhas["byclasstest"], int(time.time() - inicio),
                        "%d arquivo(s) sem classe removido(s)" % len(sem_classe)
                        if sem_classe else ""])
        except Exception as erro:  # noqa: BLE001 - o lote nao pode parar por um repo
            if isinstance(erro, AnaliseMorta):
                status = "MORTO"
            elif isinstance(erro, TimeoutError):
                status = "TIMEOUT"
            else:
                status = "ERRO"
            append_log([mlcq, gh, esperado, "", "", status, "", "",
                        int(time.time() - inicio),
                        ("%s: %s" % (type(erro).__name__, erro))[:300]])
            log("  %s: %s: %s" % (status, type(erro).__name__, erro))
            if status in ("TIMEOUT", "MORTO"):
                # as threads do JNose seguem rodando sobre o clone travado: so o restart libera
                try:
                    restart_jnose(session)
                except Exception as falha:  # noqa: BLE001
                    log("  aviso: restart do JNose falhou: %s" % falha)
        finally:
            try:
                db_reset_to(None)
            except sqlite3.Error as falha:
                log("  aviso: nao consegui limpar a tabela Projeto: %s" % falha)
            if not rmtree(dest):
                log("  aviso: nao consegui apagar " + dest)
    parar_jnose()
    log("fim")


if __name__ == "__main__":
    main()
