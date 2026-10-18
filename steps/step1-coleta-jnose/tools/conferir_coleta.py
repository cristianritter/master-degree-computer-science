"""Reapura todo numero afirmado no README do step 1.

Mesmo papel do conferir_dados.py no step 2 e do conferir_resultados.py no step 3: numero
citado em texto que nao sai de um comando envelhece em silencio, e numero digitado a mao
nao e reproduzivel. Le so o que a coleta deixou em disco - dados/repos_map.csv,
reports/run_log.csv, reports/byclasstest/, reports/bytestsmells/ e o log do
validar_filtro.py -, sem clonar nada e sem subir o JNose.

Falha com codigo 1 se algum numero divergir.

Uso:
    python conferir_coleta.py
"""
import collections
import csv
import glob
import os
import re
import struct
import sys

STEP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(STEP, "reports")

falhas = []


def exigir(condicao, descricao, observado):
    marca = "ok  " if condicao else "FALHA"
    print("  [%s] %-62s %s" % (marca, descricao, observado))
    if not condicao:
        falhas.append("%s (observado: %s)" % (descricao, observado))


def ler(caminho, **kw):
    with open(caminho, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh, **kw))


def repositorios():
    print("\nSELECAO DOS REPOSITORIOS (secao 2)")
    m = ler(os.path.join(STEP, "dados", "repos_map.csv"))
    st = collections.Counter(r["status"] for r in m)
    print("  repositorios no MLCQ: %d  %s" % (len(m), dict(st)))
    exigir(len(m) == 522, "522 repositorios no MLCQ", len(m))
    exigir(st == {"HASH_OK": 451, "NOME_HASH_DIVERGE": 10, "SEM_REPO": 61},
           "451 HASH_OK, 10 NOME_HASH_DIVERGE, 61 SEM_REPO", dict(st))


def execucao():
    print("\nEXECUCAO DA COLETA (secoes 3, 4 e 6)")
    log = ler(os.path.join(REPORTS, "run_log.csv"))
    st = collections.Counter(r["status"] for r in log)
    print("  tentativas: %d  %s" % (len(log), dict(st)))
    exigir(len(log) == 481, "481 tentativas no run_log", len(log))

    final = {}
    for r in log:
        final[r["mlcq_repo"]] = r                # a ultima tentativa de cada repositorio
    ok = [r for r in final.values() if r["status"] == "OK"]
    print("  estado final: %d de %d repositorios OK (%.0f%%)"
          % (len(ok), len(final), 100 * len(ok) / len(final)))
    exigir(len(ok) == len(final) == 451, "estado final: 451 de 451 OK", len(ok))

    horas = sum(float(r["segundos"] or 0) for r in log) / 3600
    print("  tempo total de execucao: %.1f h" % horas)
    exigir(abs(horas - 34.7) < 0.05, "tempo total ~34,7 h", "%.1f h" % horas)
    mais_lenta = max(float(r["segundos"]) for r in ok)
    print("  analise bem-sucedida mais lenta: %.0f s" % mais_lenta)
    exigir(mais_lenta == 420, "analise OK mais lenta: 420 s", mais_lenta)

    occ = sum(int(r["linhas_bytestsmells"] or 0) for r in ok)
    cls = sum(int(r["linhas_byclasstest"] or 0) for r in ok)
    print("  ocorrencias de smell: %d   classes de teste: %d" % (occ, cls))
    exigir(occ == 2059905, "2.059.905 ocorrencias de test smell", occ)
    exigir(cls == 107535, "107.535 classes de teste", cls)

    junit = collections.Counter(r["junit"] for r in ok)
    print("  versao de JUnit: %s" % dict(junit))
    exigir(junit == {"JUnit4": 398, "JUnit5": 36, "JUnit3": 17},
           "JUnit4 398, JUnit5 36, JUnit3 17", dict(junit))

    removidos = {r["mlcq_repo"]: int(re.match(r"(\d+) arquivo", r["detalhe"]).group(1))
                 for r in ok if re.match(r"\d+ arquivo", r["detalhe"] or "")}
    print("  arquivos sem classe removidos: %d em %d repositorios"
          % (sum(removidos.values()), len(removidos)))
    exigir((sum(removidos.values()), len(removidos)) == (46, 12),
           "46 arquivos removidos em 12 repositorios",
           "%d em %d" % (sum(removidos.values()), len(removidos)))
    return removidos


def validacao_do_filtro(removidos_no_lote):
    print("\nVALIDACAO DO FILTRO CONTRA O ORACULO (secao 4)")
    caminho = os.path.join(REPORTS, "logs", "validar_filtro.txt")
    if not os.path.exists(caminho):
        exigir(False, "log do validar_filtro.py existe",
               "ausente - rode: python tools/validar_filtro.py > reports/logs/validar_filtro.txt")
        return
    linhas = open(caminho, encoding="utf-8", errors="replace").read().splitlines()
    val = {}
    for l in linhas:
        m = re.match(r"^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S.*)$", l)
        if m:
            val[m.group(1)] = {"oraculo": int(m.group(2)), "filtro": int(m.group(3)),
                               "sem_junit": int(m.group(4))}
    coincidem = any("coincidem em todos" in l for l in linhas)
    exigir(len(val) == 12 and coincidem, "filtro e oraculo coincidem nos 12 repositorios",
           "%d repositorios, coincidem=%s" % (len(val), coincidem))

    # O que o lote removeu esta no run_log; o que o validador chama de oraculo e o que
    # causaria o NPE. A diferenca, por repositorio, e o que foi removido sem precisar.
    oraculo = sum(v["oraculo"] for v in val.values())
    total = sum(removidos_no_lote.get(r, 0) for r in val)
    sem_junit_removidos = total - oraculo
    fecha = [r for r, v in val.items()
             if removidos_no_lote.get(r) == v["oraculo"] + v["sem_junit"]]
    so_oraculo = [r for r, v in val.items()
                  if r not in fecha and removidos_no_lote.get(r) == v["oraculo"]]
    print("  removidos pelo lote: %d = %d que causavam o NPE + %d sem import de JUnit"
          % (total, oraculo, sem_junit_removidos))
    print("  repositorios em que removidos = oraculo + sem_junit: %d" % len(fecha))
    for r in so_oraculo:
        print("  %s: removidos so os %d do oraculo; %d sem JUnit ficaram no clone"
              % (r, val[r]["oraculo"], val[r]["sem_junit"]))
    exigir((total, oraculo, sem_junit_removidos) == (46, 25, 21),
           "dos 46 removidos, 25 causavam o NPE e 21 nao tinham JUnit",
           "%d = %d + %d" % (total, oraculo, sem_junit_removidos))
    exigir(len(fecha) == 11 and so_oraculo == ["spring-projects/spring-boot"]
           and val["spring-projects/spring-boot"]["sem_junit"] == 11,
           "11 repositorios fecham; no spring-boot ficaram 11 sem JUnit",
           "%d fecham, so oraculo: %s" % (len(fecha), ", ".join(so_oraculo)))


def classe_aninhada():
    print("\nLIMITACAO: CLASSE ANINHADA (secao 5)")
    linhas = div = 0
    repos_div = set()
    for caminho in sorted(glob.glob(os.path.join(REPORTS, "byclasstest", "*.csv"))):
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                linhas += 1
                path = (r.get("PathFile") or "").strip()
                base = re.split(r"[\\/]", path)[-1]
                base = base[:-5] if base.endswith(".java") else base
                if (r.get("TestFileName") or "").strip() != base:
                    div += 1
                    repos_div.add(r["App"])
    print("  linhas com nome divergente: %d de %d (%.1f%%), em %d repositorios"
          % (div, linhas, 100 * div / linhas, len(repos_div)))
    exigir((div, linhas, len(repos_div)) == (6842, 107535, 320),
           "6.842 de 107.535 linhas, em 320 repositorios",
           "%d de %d, %d repos" % (div, linhas, len(repos_div)))


def tamanho_dos_reports():
    print("\nESTRUTURA (secao 6)")
    gz = sorted(glob.glob(os.path.join(REPORTS, "bytestsmells", "*.csv.gz")))
    comprimido = sum(os.path.getsize(p) for p in gz)
    # o trailer do gzip guarda o tamanho original (mod 2^32), sem precisar descomprimir
    original = 0
    for p in gz:
        with open(p, "rb") as fh:
            fh.seek(-4, 2)
            original += struct.unpack("<I", fh.read(4))[0]
    print("  bytestsmells: %d arquivos, %.1f GB descomprimido, %.0f MB comprimido"
          % (len(gz), original / 1e9, comprimido / 1e6))
    exigir(len(gz) == 451, "451 CSVs comprimidos em bytestsmells", len(gz))
    exigir(round(original / 1e9, 1) == 1.4 and round(comprimido / 1e6) == 167,
           "1,4 GB descomprimido, 167 MB comprimido",
           "%.1f GB, %.0f MB" % (original / 1e9, comprimido / 1e6))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    repositorios()
    removidos = execucao()
    validacao_do_filtro(removidos)
    classe_aninhada()
    tamanho_dos_reports()
    print()
    if falhas:
        print("%d NUMERO(S) DIVERGENTE(S):" % len(falhas))
        for f in falhas:
            print("  - %s" % f)
        sys.exit(1)
    print("todos os numeros do README conferem")


if __name__ == "__main__":
    main()
