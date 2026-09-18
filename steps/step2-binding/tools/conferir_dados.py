"""Reapura todos os numeros afirmados no README do step 2, direto das fontes.

Todo numero que aparece no README sai daqui. A razao de existir e a mesma do
validar_filtro.py no step 1: afirmacao empirica em texto de artigo precisa de um comando
que a regenere, senao ninguem - inclusive o autor seis meses depois - sabe se ela ainda
vale depois de uma recoleta.

As checagens 1 a 4 sao PRESSUPOSTOS: se uma delas falhar, algum script do step 2 esta
silenciosamente errado, e o comando termina com codigo 1. As demais sao NUMEROS
DESCRITIVOS que alimentam tabelas do README.

Uso:
    python conferir_dados.py            # tudo
    python conferir_dados.py --secao 3  # so as checagens da secao 3 do README
"""
import argparse
import collections
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

falhas = []


def titulo(t):
    print("\n" + t)
    print("-" * len(t))


def exigir(condicao, descricao, observado):
    """Pressuposto do step: imprime e registra falha sem interromper as outras checagens."""
    marca = "ok  " if condicao else "FALHA"
    print("  [%s] %-58s %s" % (marca, descricao, observado))
    if not condicao:
        falhas.append(descricao)


# ------------------------------------------------------------------ pressupostos
def secao_2():
    titulo("SECAO 2 - pressupostos da normalizacao")

    # 1. as 8 colunas de smell nao habilitadas estao zeradas em todas as linhas
    naozero = collections.Counter()
    linhas = 0
    chaves = collections.Counter()
    for p in sorted(glob.glob(os.path.join(c.BYCLASSTEST, "*.csv"))):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                linhas += 1
                chaves[(r["App"], (r.get("PathFile") or "").lower())] += 1
                for s in c.SMELLS_DESABILITADOS:
                    if (r.get(s) or "0").strip() not in ("0", ""):
                        naozero[s] += 1
    exigir(not naozero, "as 8 colunas de smell desabilitadas estao todas zeradas",
           "nenhuma diferente de zero" if not naozero else dict(naozero))

    # 2. o byclasstest nao tem linhas duplicadas
    dup = sum(v - 1 for v in chaves.values() if v > 1)
    exigir(dup == 0, "byclasstest sem (repo, caminho) duplicado",
           "%d linhas, %d chaves distintas" % (linhas, len(chaves)))

    # 3. todo productionFile do JNose e redutivel a caminho relativo
    irreconheciveis = preenchidos = 0
    for p in sorted(glob.glob(os.path.join(c.BYCLASSTEST, "*.csv"))):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                pf = (r.get("ProductionFileName") or "").strip()
                if pf:
                    preenchidos += 1
                    if c.caminho_relativo(pf) is None:
                        irreconheciveis += 1
    exigir(irreconheciveis == 0, "todo productionFile reduz a caminho relativo",
           "%d preenchidos (%.1f%% de %d), %d irreconheciveis"
           % (preenchidos, 100 * preenchidos / linhas, linhas, irreconheciveis))

    # 4. todo App do byclasstest existe no repos_map do step 1
    mapa = c.ler_mapa()
    espelhos = {m["github_repo"] for m in mapa.values()}
    apps = {k[0] for k in chaves}
    fora = apps - espelhos
    exigir(not fora, "todo App do byclasstest esta no repos_map do step 1",
           "%d Apps distintos, %d fora" % (len(apps), len(fora)))

    csvs = len(glob.glob(os.path.join(c.BYCLASSTEST, "*.csv")))
    print("\n  descritivo:")
    print("    CSVs de byclasstest (repositorios analisados)      %d" % csvs)
    print("    repositorios com >=1 classe de teste               %d" % len(apps))
    print("    repositorios sem nenhuma classe de teste           %d" % (csvs - len(apps)))

    classes = c.ler_csv(os.path.join(c.DADOS, "test_classes.csv"))
    div = sum(1 for t in classes if t["nome_divergente"] == "1")
    print("    nome_divergente (defeito de classe aninhada)       %d  (%.1f%%)"
          % (div, 100 * div / len(classes)))

    # o efeito do defeito: production vazio concentrado nas linhas divergentes
    for rotulo, sub in (("nome bate com o arquivo", [t for t in classes if t["nome_divergente"] == "0"]),
                        ("nome diverge (aninhada)", [t for t in classes if t["nome_divergente"] == "1"])):
        vazio = sum(1 for t in sub if not t["production_path"])
        eager = sum(int(t[c.coluna("Eager Test")]) for t in sub)
        lazy = sum(int(t[c.coluna("Lazy Test")]) for t in sub)
        fixture = sum(int(t[c.coluna("General Fixture")]) for t in sub)
        print("    %-24s %6d linhas  production vazio %5.1f%%  "
              "Eager/1k %7.1f  Lazy/1k %7.1f  Fixture/1k %6.1f"
              % (rotulo, len(sub), 100 * vazio / len(sub),
                 1000 * eager / len(sub), 1000 * lazy / len(sub), 1000 * fixture / len(sub)))


def secao_3():
    titulo("SECAO 3 - o rotulo do MLCQ e circular com o desenho amostral")

    samples = c.ler_csv(os.path.join(c.DADOS, "mlcq_samples.csv"))
    reviews = c.ler_csv(os.path.join(c.DADOS, "mlcq_reviews.csv"))

    # 5. o corte de crosscheck do apendice separa exatamente as amostras ja positivas
    pre = collections.defaultdict(list)
    cross = collections.defaultdict(list)
    for r in reviews:
        (cross if r["is_crosscheck"] == "1" else pre)[r["sample_id"]].append(int(r["severidade_num"]))
    com_cross = set(cross)
    pre_pos = {s for s, v in pre.items() if max(v) >= c.RANK["minor"]}
    exigir(com_cross <= pre_pos,
           "toda amostra crosscheckada ja era positiva antes do corte",
           "%d crosscheckadas, %d delas ja positivas, %d nao"
           % (len(com_cross), len(com_cross & pre_pos), len(com_cross - pre_pos)))
    print("       (apendice do MLCQ, secao 2.2, fase 4 - corte em %s)" % c.CORTE_CROSSCHECK)

    # a tabela: positivos por regra, quebrados por numero de revisores
    print("\n  positivos por numero de revisores (a circularidade):")
    print("    %11s %9s %18s %13s %16s"
          % ("revisores", "amostras", "positivas any>none", "por maioria", "severidade media"))
    por_n = collections.defaultdict(list)
    for s in samples:
        por_n[int(s["n_reviews"])].append(s)
    for n in sorted(por_n):
        g = por_n[n]
        if len(g) < 20:
            continue
        a = sum(1 for s in g if s["pos_any"] == "1")
        m = sum(1 for s in g if s["pos_maioria"] == "1")
        sv = sum(float(s["sev_media"]) for s in g) / len(g)
        print("    %11d %9d %11d %6.1f%% %6d %6.1f%% %16.3f"
              % (n, len(g), a, 100 * a / len(g), m, 100 * m / len(g), sv))

    # a tabela: prevalencia por regra e por smell
    print("\n  prevalencia por regra de agregacao:")
    smells = sorted(c.CODE_SMELLS)
    regras = [("any > none", "pos_any"), ("maioria > none", "pos_maioria"),
              ("unanime > none", "pos_unanime"), ("any >= major", "pos_any_major")]
    print("    %-16s" % "regra" + "".join("%16s" % s for s in smells) + "%10s" % "GERAL")
    for nome, col in regras:
        linha = "    %-16s" % nome
        tp = tn = 0
        for s in smells:
            sub = [x for x in samples if x["smell"] == s]
            p = sum(1 for x in sub if x[col] == "1")
            tp += p
            tn += len(sub)
            linha += "%7d %6.1f%%" % (p, 100 * p / len(sub))
        print(linha + "%9.1f%%" % (100 * tp / tn))

    # concordancia
    multi = [s for s in samples if int(s["n_reviews"]) >= 2]
    disc = sum(1 for s in multi
               if 0 < int(s["n_positivos"]) < int(s["n_reviews"]))
    anypos = [s for s in multi if s["pos_any"] == "1"]
    una = sum(1 for s in anypos if s["pos_unanime"] == "1")
    print("\n  concordancia entre revisores:")
    print("    amostras com >=2 revisoes                          %d" % len(multi))
    print("    discordantes no binario                            %d  (%.1f%%)"
          % (disc, 100 * disc / len(multi)))
    print("    positivas por any>none                             %d" % len(anypos))
    print("      destas, com positivo unanime                     %d  (%.1f%%)"
          % (una, 100 * una / len(anypos)))
    print("      destas, disputadas                               %d  (%.1f%%)"
          % (len(anypos) - una, 100 * (len(anypos) - una) / len(anypos)))

    print("\n  estratos (coluna estrato do mlcq_samples.csv):")
    est = collections.Counter(s["estrato"] for s in samples)
    for k, v in est.most_common():
        print("    %-22s %5d  %5.1f%%" % (k, v, 100 * v / len(samples)))


def secao_4():
    titulo("SECAO 4 - o binding")

    # 6. colisao de basename, que e a razao de o binding ser por caminho
    por_base = collections.defaultdict(set)
    classes = c.ler_csv(os.path.join(c.DADOS, "test_classes.csv"))
    for t in classes:
        por_base[(t["github_repo"], t["nome_arquivo"])].add(t["path"])
    col = {k: v for k, v in por_base.items() if len(v) > 1}
    print("  ambiguidade de basename de teste dentro do mesmo repositorio:")
    print("    basenames distintos                                %d" % len(por_base))
    print("    basenames com mais de um arquivo                   %d  (%.1f%%)"
          % (len(col), 100 * len(col) / len(por_base)))
    print("    arquivos envolvidos                                %d"
          % sum(len(v) for v in col.values()))
    print("    piores casos:")
    for k, v in sorted(col.items(), key=lambda kv: -len(kv[1]))[:5]:
        print("      %4dx  %-32s em %s" % (len(v), k[1], k[0]))

    # cardinalidade do join
    prod = collections.defaultdict(set)
    for t in classes:
        if t["production_path"]:
            prod[(t["github_repo"], t["production_path"])].add(t["path"])
    card = collections.Counter(len(v) for v in prod.values())
    multi = sum(v for k, v in card.items() if k > 1)
    print("\n  cardinalidade producao -> teste (via ProductionFileName do JNose):")
    for k in sorted(card)[:6]:
        print("    %d classe(s) de teste                               %6d  (%.1f%%)"
              % (k, card[k], 100 * card[k] / len(prod)))
    print("    com mais de uma                                    %6d  (%.1f%%)"
          % (multi, 100 * multi / len(prod)))
    print("    maximo                                             %6d" % max(card))

    # cobertura por metodo e cadeia de atrito
    pares = c.ler_csv(os.path.join(c.DADOS, "binding.csv"))
    samples = c.ler_csv(os.path.join(c.DADOS, "mlcq_samples.csv"))
    ligados = {(p["github_repo"], p["production_path"]) for p in pares}
    hash_ok = [s for s in samples if s["repo_status"] == "HASH_OK"]
    com = [s for s in hash_ok if (s["github_repo"], s["path"]) in ligados]

    print("\n  pares por metodo de binding:")
    for m, v in collections.Counter(p["metodo"] for p in pares).most_common():
        so_este = {(p["github_repo"], p["production_path"]) for p in pares if p["metodo"] == m}
        amostras_m = sum(1 for s in hash_ok if (s["github_repo"], s["path"]) in so_este)
        print("    %-22s %6d pares, %4d amostras alcancadas (%.1f%% dos HASH_OK)"
              % (m, v, amostras_m, 100 * amostras_m / len(hash_ok)))

    print("\n  cadeia de atrito (o recorte que o artigo declara):")
    print("    %5d  amostras no MLCQ" % len(samples))
    print("    %5d  em repositorio disponivel (HASH_OK)" % len(hash_ok))
    print("    %5d  com classe de teste identificada  (%.1f%%)"
          % (len(com), 100 * len(com) / len(hash_ok)))
    for e in ("positivo_confiavel", "disputado", "negativo_confiavel", "negativo_1_review"):
        a = sum(1 for s in com if s["estrato"] == e)
        b = sum(1 for s in hash_ok if s["estrato"] == e)
        print("       %-20s %4d de %4d  (%.1f%%)" % (e, a, b, 100 * a / b if b else 0))

    print("\n  motivo_sem_ligacao (production_files.csv):")
    pf = c.ler_csv(os.path.join(c.DADOS, "production_files.csv"))
    for k, v in collections.Counter(r["motivo_sem_ligacao"] or "(ligado)"
                                    for r in pf).most_common():
        print("    %-32s %5d  %5.1f%%" % (k, v, 100 * v / len(pf)))

    refs = os.path.join(c.DADOS, "refs_producao.csv")
    if os.path.exists(refs):
        rr = c.ler_csv(refs)
        print("\n  estrategia 3 - evidencia dos pares (refs_producao.csv):")
        for k, v in collections.Counter(r["evidencia"] for r in rr).most_common():
            print("    %-22s %6d  %5.1f%%" % (k, v, 100 * v / len(rr)))
        log = c.ler_csv(os.path.join(c.DADOS, "refs_log.csv"))
        ok = [r for r in log if r["status"] == "OK"]
        seg = sum(int(r["segundos"]) for r in ok)
        print("    repositorios processados                        %d" % len(log))
        print("      OK                                            %d" % len(ok))
        for st, n in collections.Counter(r["status"] for r in log).items():
            if st != "OK":
                print("      %-44s %d" % (st, n))
        print("    tempo total / medio                             %ds / %.1fs por repo"
              % (seg, seg / len(ok) if ok else 0))
        if len(log) < len(glob.glob(os.path.join(c.BYCLASSTEST, "*.csv"))):
            print("    ATENCAO: lote incompleto - os numeros acima sao parciais")
    else:
        print("\n  estrategia 3 nao rodou (refs_producao.csv ausente)")

    tradeoff(pares, samples, hash_ok)


def tradeoff(pares, samples, hash_ok):
    """Cobertura contra concentracao de testes por producao, para cada filtro disponivel.

    A estrategia 3 troca precisao por cobertura, e esta tabela e o que permite escolher o
    ponto de troca com numero na mao em vez de intuicao. A coluna t/prod (testes por
    arquivo de producao) e o indicador de risco: quanto mais alta, mais provavel que a
    ligacao seja referencia incidental - um DTO importado por todo mundo - e nao teste
    dedicado.
    """
    refs = {}
    caminho = os.path.join(c.DADOS, "refs_producao.csv")
    if not os.path.exists(caminho):
        return
    ordem = {"import_fqn": 0, "wildcard": 1, "mesmo_pacote": 2}
    for r in c.ler_csv(caminho):
        k = (r["github_repo"], r["production_path"], r["test_path"])
        if k not in refs or ordem[r["evidencia"]] < ordem[refs[k]]:
            refs[k] = r["evidencia"]

    def medir(metodos, evidencias, max_testes):
        testes = collections.defaultdict(set)
        for p in pares:
            if p["metodo"] not in metodos:
                continue
            if p["metodo"] == "referencia_estatica" and evidencias:
                if refs.get((p["github_repo"], p["production_path"], p["test_path"])) \
                        not in evidencias:
                    continue
            testes[(p["github_repo"], p["production_path"])].add(p["test_path"])
        if max_testes:
            testes = {k: v for k, v in testes.items() if len(v) <= max_testes}
        com = [s for s in hash_ok if (s["github_repo"], s["path"]) in testes]
        n_pares = sum(len(v) for v in testes.values())
        return (len(com),
                sum(1 for s in com if s["estrato"] == "positivo_confiavel"),
                sum(1 for s in com if s["estrato"] == "negativo_confiavel"),
                n_pares, n_pares / len(testes) if testes else 0)

    base = ["caminho_exato", "convencao"]
    todos = base + ["referencia_estatica"]
    cfgs = [
        ("so caminho_exato + convencao", base, None, 0),
        ("+ refs, todas as evidencias", todos, None, 0),
        ("+ refs, so import_fqn", todos, {"import_fqn"}, 0),
        ("+ refs, max 10 testes", todos, None, 10),
        ("+ refs, max 5 testes", todos, None, 5),
        ("+ refs, max 3 testes", todos, None, 3),
        ("+ refs import_fqn, max 3", todos, {"import_fqn"}, 3),
        ("+ refs, max 1 teste", todos, None, 1),
    ]
    print("\n  cobertura x concentracao (o trade-off da estrategia 3):")
    print("    %-30s %7s %8s %7s %7s %8s %7s"
          % ("configuracao", "amostras", "% HASHOK", "pos_cf", "neg_cf", "pares", "t/prod"))
    for nome, m, e, mx in cfgs:
        a, pc, nc, np_, razao = medir(m, e, mx)
        print("    %-30s %7d %7.1f%% %7d %7d %8d %7.1f"
              % (nome, a, 100 * a / len(hash_ok), pc, nc, np_, razao))



def secao_6():
    """A tabela de prevalencia da secao 6: o binding desloca o rotulo?

    Se deslocasse, a ligacao seria mais facil para classe suja e o binding viraria ameaca
    a validade interna da RQ. E a checagem que sustenta a afirmacao mais forte da secao 6.
    """
    titulo("SECAO 6 - as duas tabelas derivadas")

    samples = c.ler_csv(os.path.join(c.DADOS, "mlcq_samples.csv"))
    pares = c.ler_csv(os.path.join(c.DADOS, "binding.csv"))

    metodos_de = collections.defaultdict(set)
    for p in pares:
        metodos_de[(p["github_repo"], p["production_path"])].add(p["metodo"])

    hash_ok = [s for s in samples if s["repo_status"] == "HASH_OK"]
    det, tudo = [], []
    for s in hash_ok:
        m = metodos_de.get((s["github_repo"], s["path"]))
        if not m:
            continue
        tudo.append(s)
        if m & {"caminho_exato", "convencao"}:
            det.append(s)

    regras = ["pos_any", "pos_maioria", "pos_any_major", "pos_unanime"]
    print("  prevalencia do rotulo por cobertura do binding:")
    print("    %-22s %8s %s" % ("", "amostras", " ".join("%14s" % r for r in regras)))
    taxas = {}
    for nome, grupo in (("HASH_OK (todas)", hash_ok), ("so deterministicas", det),
                        ("com estrategia 3", tudo)):
        col = []
        for r in regras:
            n = sum(1 for s in grupo if s[r] == "1")
            taxas[(nome, r)] = 100 * n / len(grupo)
            col.append("%6d (%4.1f%%)" % (n, 100 * n / len(grupo)))
        print("    %-22s %8d %s" % (nome, len(grupo), " ".join("%14s" % x for x in col)))

    # O ponto da secao: ligar ou nao ligar e quase independente do rotulo.
    for r in regras:
        base = taxas[("HASH_OK (todas)", r)]
        for nome in ("so deterministicas", "com estrategia 3"):
            exigir(abs(taxas[(nome, r)] - base) < 3.0,
                   "prevalencia de %s em '%s' fica a menos de 3 pp do universo HASH_OK" % (r, nome),
                   "%.1f%% vs %.1f%%" % (taxas[(nome, r)], base))

    # As duas tabelas existem e batem com o que o README diz que elas sao.
    for nome, linhas_esperadas in (("deterministico", 730), ("ampliado", 1369)):
        caminho = os.path.join(c.DADOS, "analise_%s.csv" % nome)
        if not os.path.exists(caminho):
            exigir(False, "analise_%s.csv existe" % nome, "ausente - rode gerar_analises.py")
            continue
        n = len(c.ler_csv(caminho))
        exigir(n == linhas_esperadas, "analise_%s.csv tem %d linhas" % (nome, linhas_esperadas), n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secao", type=int, choices=[2, 3, 4, 6], action="append",
                    help="confere so esta secao do README (repetivel)")
    args = ap.parse_args()

    secoes = {2: secao_2, 3: secao_3, 4: secao_4, 6: secao_6}
    for n in (args.secao or [2, 3, 4, 6]):
        secoes[n]()

    print()
    if falhas:
        print("%d PRESSUPOSTO(S) VIOLADO(S):" % len(falhas))
        for f in falhas:
            print("  - %s" % f)
        print("\nAlgum script do step 2 esta errado, ou a entrada mudou. Nao siga para o step 3.")
        sys.exit(1)
    print("todos os pressupostos conferem")


if __name__ == "__main__":
    main()
