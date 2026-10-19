"""Reapura todo numero afirmado no README do step 1.

Mesmo papel do conferir_dados.py no step 2 e do conferir_resultados.py no step 3: numero
citado em texto que nao sai de um comando envelhece em silencio, e numero digitado a mao
nao e reproduzivel. Le so o que a coleta deixou em disco - dados/repos_map.csv,
reports/run_log.csv, reports/byclasstest/ e reports/bytestsmells/, alem do byclasstest da
configuracao padrao (reports-config-padrao/) -, sem clonar nada e sem subir o JNose.

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
    exigir(len(log) == 455, "455 tentativas no run_log", len(log))

    final = {}
    for r in log:
        final[r["mlcq_repo"]] = r                # a ultima tentativa de cada repositorio
    ok = [r for r in final.values() if r["status"] == "OK"]
    print("  estado final: %d de %d repositorios OK (%.0f%%)"
          % (len(ok), len(final), 100 * len(ok) / len(final)))
    exigir(len(ok) == len(final) == 451, "estado final: 451 de 451 OK", len(ok))

    horas = sum(float(r["segundos"] or 0) for r in log) / 3600
    print("  tempo total de execucao: %.1f h" % horas)
    exigir(abs(horas - 4.4) < 0.05, "tempo total ~4,4 h", "%.1f h" % horas)
    mais_lenta = max(float(r["segundos"]) for r in ok)
    print("  analise bem-sucedida mais lenta: %.0f s" % mais_lenta)
    exigir(mais_lenta == 230, "analise OK mais lenta: 230 s", mais_lenta)

    occ = sum(int(r["linhas_bytestsmells"] or 0) for r in ok)
    cls = sum(int(r["linhas_byclasstest"] or 0) for r in ok)
    print("  ocorrencias de smell: %d   classes de teste: %d" % (occ, cls))
    exigir(occ == 2150044, "2.150.044 ocorrencias de test smell", occ)
    exigir(cls == 107535, "107.535 classes de teste", cls)

    junit = collections.Counter(r["junit"] for r in ok)
    print("  versao de JUnit: %s" % dict(junit))
    exigir(junit == {"JUnit4": 398, "JUnit5": 36, "JUnit3": 17},
           "JUnit4 398, JUnit5 36, JUnit3 17", dict(junit))

    removidos = {r["mlcq_repo"]: int(re.match(r"(\d+) arquivo", r["detalhe"]).group(1))
                 for r in ok if re.match(r"\d+ arquivo", r["detalhe"] or "")}
    print("  arquivos sem classe removidos: %d em %d repositorios"
          % (sum(removidos.values()), len(removidos)))
    exigir((sum(removidos.values()), len(removidos)) == (25, 11),
           "25 arquivos removidos em 11 repositorios",
           "%d em %d" % (sum(removidos.values()), len(removidos)))


def unknown_test():
    print("\nDETECTOR DE UNKNOWN TEST (secao 4)")
    import efeito_unknown_test as eu
    tot, afetados, problemas = eu.medir()
    print("  classes zeradas: %d em %d repositorios, %d ocorrencias perdidas"
          % (tot["zeradas"], len(afetados), tot["ocorrencias_apagadas"]))
    exigir(not problemas, "config padrao difere do estudo so pelo Unknown Test",
           "%d outra(s) divergencia(s)" % len(problemas))
    exigir((tot["zeradas"], len(afetados), tot["ocorrencias_apagadas"]) == (142, 51, 5500),
           "142 classes zeradas em 51 repositorios, 5.500 ocorrencias",
           "%d em %d, %d" % (tot["zeradas"], len(afetados), tot["ocorrencias_apagadas"]))


def classe_aninhada():
    print("\nLIMITACAO: CLASSE ANINHADA (secao 5)")
    linhas = div = 0
    repos_div = set()
    # por grupo (nome bate / diverge): linhas, production vazio e soma de cada smell
    smells = ["Eager Test", "Lazy Test", "General Fixture"]
    grupo = {g: collections.Counter() for g in ("bate", "diverge")}
    for caminho in sorted(glob.glob(os.path.join(REPORTS, "byclasstest", "*.csv"))):
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                linhas += 1
                path = (r.get("PathFile") or "").strip()
                base = re.split(r"[\\/]", path)[-1]
                base = base[:-5] if base.endswith(".java") else base
                g = "bate"
                if (r.get("TestFileName") or "").strip() != base:
                    div += 1
                    repos_div.add(r["App"])
                    g = "diverge"
                grupo[g]["linhas"] += 1
                grupo[g]["sem_producao"] += not (r.get("ProductionFileName") or "").strip()
                for s in smells:
                    grupo[g][s] += int(r.get(s) or 0)
    print("  linhas com nome divergente: %d de %d (%.1f%%), em %d repositorios"
          % (div, linhas, 100 * div / linhas, len(repos_div)))
    exigir((div, linhas, len(repos_div)) == (6842, 107535, 320),
           "6.842 de 107.535 linhas, em 320 repositorios",
           "%d de %d, %d repos" % (div, linhas, len(repos_div)))

    tabela = {}
    for g, c in grupo.items():
        tabela[g] = [c["linhas"], round(100 * c["sem_producao"] / c["linhas"], 1)] + \
                    [round(1000 * c[s] / c["linhas"], 1) for s in smells]
        print("  %-8s linhas=%d  production vazio=%.1f%%  por 1k: Eager=%.1f Lazy=%.1f GF=%.1f"
              % tuple([g] + tabela[g]))
    esperado = {"bate": [100693, 50.9, 1138.9, 1189.0, 280.1],
                "diverge": [6842, 93.8, 40.8, 52.3, 322.3]}
    exigir(tabela == esperado, "tabela da secao 5 (production vazio, smells por 1k)",
           "ok" if tabela == esperado else tabela)
    queda = [round(tabela["bate"][i] / tabela["diverge"][i]) for i in (2, 3)]
    print("  queda na linha aninhada: Eager %dx, Lazy %dx" % tuple(queda))
    exigir(queda == [28, 23], "Eager Test cai 28x e Lazy Test 23x", queda)


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
    exigir(round(original / 1e9, 1) == 1.5 and round(comprimido / 1e6) == 173,
           "1,5 GB descomprimido, 173 MB comprimido",
           "%.1f GB, %.0f MB" % (original / 1e9, comprimido / 1e6))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    repositorios()
    execucao()
    unknown_test()
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
