"""Monta a tabela larga de analise: 1 linha por arquivo de producao, code smell ao lado de test smell.

    dados/<saida>.csv         a tabela (--saida; ver gerar_analises.py)
    dados/<saida>.params.txt  parametros, proveniencia e cobertura

Este e o unico artefato DERIVADO do step 2, e e descartavel: as decisoes que ele toma
- qual regra de rotulo, como agregar varios testes, quais metodos de binding aceitar -
sao todas parametros de linha de comando, e ficam gravadas no .params.txt ao lado. E de
proposito que elas vivam aqui e nao dentro dos CSVs normalizados: mudar de ideia sobre a
agregacao deve custar um rerun, nao uma recoleta.

Nada de analise estatistica sai daqui. Isso e step 3.

Duas armadilhas que a tabela evita:

1. "Nao anotado" nao e "negativo". O MLCQ anotou amostras especificas para smells
   especificos: um arquivo avaliado para blob nao diz nada sobre data class. Por isso
   cada code smell tem coluna propria com tres estados possiveis - vazio (nao avaliado),
   0 (avaliado, negativo pela regra escolhida) e 1 (positivo). Tratar vazio como 0
   inventaria milhares de negativos.

2. Teste que referencia nao e teste que testa. A estrategia referencia_estatica liga
   DTOs e classes de protocolo a dezenas de testes que so as importam (CanalEntry.java
   aparece ligado a 18 testes no piloto). Por isso existe --max-testes, que descarta a
   ligacao de arquivos de producao acima do limite, e a coluna n_testes, que deixa o
   efeito dessa escolha mensuravel.

Uso:
    python montar_analise.py
    python montar_analise.py --rotulo maioria --agregacao densidade
    python montar_analise.py --metodos caminho_exato --excluir-nome-divergente
    python montar_analise.py --rotulo sev_media --max-testes 5
"""
import argparse
import collections
import hashlib
import os
import platform
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

# Regra de rotulo -> (coluna do mlcq_samples.csv, descricao para o .params.txt).
# Nenhuma e o padrao "certo"; maioria e o padrao porque e a unica que usa o veredito do
# crosscheck que o MLCQ coletou justamente para julgar os flags iniciais.
ROTULOS = {
    "any": ("pos_any", "alguem marcou > none (circular com o desenho amostral, ver README)"),
    "maioria": ("pos_maioria", "a maioria marcou > none"),
    "unanime": ("pos_unanime", "todos marcaram > none (19 amostras em todo o MLCQ)"),
    "any_major": ("pos_any_major", "alguem marcou >= major"),
    "sev_media": ("sev_media", "severidade media como valor continuo (0-3), sem dicotomizar"),
}

AGREGACOES = {
    "soma": "soma do smell em todas as classes de teste ligadas",
    "max": "maior valor entre as classes de teste ligadas",
    "media": "media entre as classes de teste ligadas",
    "densidade": "soma dividida pelo total de metodos de teste ligados (por metodo)",
}

METODOS = ["caminho_exato", "convencao", "referencia_estatica"]

# Entradas que determinam a saida. O hash de cada uma vai para o .params.txt: sem isso
# "repetivel" e promessa; com isso, quem repetir sabe se partiu do mesmo dado.
ENTRADAS = ["mlcq_samples.csv", "test_classes.csv", "binding.csv"]


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def commit_do_repo():
    """O commit em que o codigo estava, marcado se havia mudanca nao commitada em tools/."""
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=c.STEP,
                           capture_output=True, text=True, timeout=15)
        if h.returncode != 0:
            return "(fora de repositorio git)"
        rev = h.stdout.strip()
        st = subprocess.run(["git", "status", "--porcelain", "--", "tools"], cwd=c.STEP,
                            capture_output=True, text=True, timeout=15)
        return rev + (" (tools com mudanca nao commitada)" if st.stdout.strip() else "")
    except Exception as e:
        return "(indisponivel: %s)" % type(e).__name__



def agregar(valores, agregacao, n_metodos):
    if not valores:
        return ""
    if agregacao == "soma":
        return sum(valores)
    if agregacao == "max":
        return max(valores)
    if agregacao == "media":
        return round(sum(valores) / len(valores), 4)
    if agregacao == "densidade":
        return round(sum(valores) / n_metodos, 6) if n_metodos else ""
    raise ValueError(agregacao)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rotulo", choices=sorted(ROTULOS), default="maioria")
    ap.add_argument("--agregacao", choices=sorted(AGREGACOES), default="soma")
    ap.add_argument("--metodos", nargs="+", choices=METODOS, default=METODOS,
                    help="metodos de binding aceitos (padrao: todos)")
    ap.add_argument("--max-testes", type=int, default=0,
                    help="descarta producao com mais de N testes ligados (0 = sem limite); "
                         "serve para cortar DTO referenciado por todo mundo")
    ap.add_argument("--excluir-nome-divergente", action="store_true",
                    help="ignora classes de teste afetadas pelo defeito de classe aninhada "
                         "do jnose-core; obrigatorio para analise com Eager/Lazy Test")
    ap.add_argument("--estratos", nargs="+",
                    default=["positivo_confiavel", "negativo_confiavel", "disputado",
                             "negativo_1_review"],
                    help="estratos de evidencia dos revisores a incluir")
    ap.add_argument("--saida", default="analise_classe.csv",
                    help="nome do CSV em dados/; gerar_analises.py usa os dois oficiais")
    args = ap.parse_args()

    samples = c.ler_csv(os.path.join(c.DADOS, "mlcq_samples.csv"))
    classes = {(t["github_repo"], t["path"]): t
               for t in c.ler_csv(os.path.join(c.DADOS, "test_classes.csv"))}
    pares = c.ler_csv(os.path.join(c.DADOS, "binding.csv"))

    coluna_rotulo, desc_rotulo = ROTULOS[args.rotulo]
    continuo = args.rotulo == "sev_media"

    # producao -> classes de teste, filtrando por metodo e pelo defeito de nome
    testes_de = collections.defaultdict(set)
    descartados = collections.Counter()
    for p in pares:
        if p["metodo"] not in args.metodos:
            descartados["metodo_nao_aceito"] += 1
            continue
        t = classes.get((p["github_repo"], p["test_path"]))
        if t is None:
            descartados["teste_fora_do_test_classes"] += 1
            continue
        if args.excluir_nome_divergente and t["nome_divergente"] == "1":
            descartados["nome_divergente"] += 1
            continue
        testes_de[(p["github_repo"], p["production_path"])].add(p["test_path"])

    if args.max_testes:
        antes = len(testes_de)
        testes_de = {k: v for k, v in testes_de.items() if len(v) <= args.max_testes}
        descartados["producao_acima_do_max_testes"] = antes - len(testes_de)

    # amostras agrupadas por arquivo de producao
    por_arquivo = collections.defaultdict(list)
    for s in samples:
        if s["repo_status"] != "HASH_OK" or s["estrato"] not in args.estratos:
            continue
        por_arquivo[(s["github_repo"], s["path"])].append(s)

    smells_ordenados = sorted(c.CODE_SMELLS)
    cab = ["github_repo", "production_path", "estratos", "n_amostras"]
    for sm in smells_ordenados:
        k = sm.replace(" ", "_")
        # Todas as regras de rotulo lado a lado, pelo mesmo motivo que o mlcq_samples.csv
        # carrega as suas: escolher a regra aqui congelaria no artefato a decisao mais
        # discutivel do dataset (ver README secao 3). cs_<smell> e apelido da regra pedida
        # em --rotulo, para quem quer uma coluna so.
        cab += ["cs_" + k]
        cab += ["cs_%s_%s" % (k, regra) for regra in sorted(ROTULOS)]
        cab += ["cs_%s_sev_max" % k, "cs_%s_n_reviews" % k]
    cab += ["n_testes", "n_testes_nome_divergente", "test_paths", "loc_teste",
            "n_metodos_teste"]
    cab += [c.coluna(s) for s in c.SMELLS]
    cab += ["ts_n_distintos", "ts_n_total"]

    linhas = []
    usados = 0   # pares de binding que sobreviveram aos filtros e entraram na tabela
    for chave, amostras in sorted(por_arquivo.items()):
        tpaths = sorted(testes_de.get(chave, ()))
        if not tpaths:
            continue
        ts = [classes[(chave[0], t)] for t in tpaths]
        n_metodos = sum(int(t["n_metodos"]) for t in ts)

        linha = [chave[0], chave[1], "|".join(sorted({a["estrato"] for a in amostras})),
                 len(amostras)]
        for sm in smells_ordenados:
            dela = [a for a in amostras if a["smell"] == sm]
            if not dela:
                # Nao avaliado para este smell. Vazio, nunca 0 - tratar vazio como zero
                # inventaria milhares de negativos (README, secao 6).
                linha += [""] * (3 + len(ROTULOS))
                continue
            # varias amostras (ex.: long method por funcao) colapsam num arquivo:
            # o arquivo conta como positivo se qualquer amostra dele e positiva, e a
            # severidade continua vira a maior entre elas.
            def valor(regra):
                col = ROTULOS[regra][0]
                if regra == "sev_media":
                    return round(max(float(a[col]) for a in dela), 4)
                return int(any(a[col] == "1" for a in dela))

            linha += [valor(args.rotulo)]
            linha += [valor(regra) for regra in sorted(ROTULOS)]
            linha += [max(int(a["sev_max"]) for a in dela),
                      sum(int(a["n_reviews"]) for a in dela)]

        # Quantos dos testes ligados tem o nome corrompido pelo defeito de classe
        # aninhada do jnose-core (step 1, secao 5). Fica como COLUNA, nao como filtro:
        # excluir aqui seria irreversivel, e General Fixture continua confiavel nessas
        # linhas. Analise com Eager/Lazy Test TEM que filtrar ou estratificar por ela.
        n_div = sum(1 for t in ts if t["nome_divergente"] == "1")
        linha += [len(tpaths), n_div, "|".join(tpaths),
                  sum(int(t["loc"]) for t in ts), n_metodos]
        for s in c.SMELLS:
            linha.append(agregar([int(t[c.coluna(s)]) for t in ts], args.agregacao, n_metodos))
        linha += [agregar([int(t["n_smells_distintos"]) for t in ts], args.agregacao, n_metodos),
                  agregar([int(t["n_smells_total"]) for t in ts], args.agregacao, n_metodos)]
        usados += len(tpaths)
        linhas.append(linha)

    destino = os.path.join(c.DADOS, args.saida)
    n = c.escrever_csv(destino, cab, linhas)
    print("%s  %d linhas (arquivos de producao com teste ligado)" % (args.saida, n))

    print("\nrotulo por code smell (colunas cs_*):")
    for sm in smells_ordenados:
        col = cab.index("cs_" + sm.replace(" ", "_"))
        vals = [l[col] for l in linhas if l[col] != ""]
        if not vals:
            print("  %-14s nenhuma linha avaliada" % sm)
        elif continuo:
            print("  %-14s %4d avaliadas, severidade media %.3f"
                  % (sm, len(vals), sum(float(v) for v in vals) / len(vals)))
        else:
            pos = sum(int(v) for v in vals)
            print("  %-14s %4d avaliadas, %3d positivas (%.1f%%)"
                  % (sm, len(vals), pos, 100 * pos / len(vals)))

    if descartados:
        print("\npares descartados pelos filtros:")
        for k, v in descartados.most_common():
            print("  %-34s %d" % (k, v))

    params = os.path.join(c.DADOS, args.saida.replace(".csv", "") + ".params.txt")
    with open(params, "w", encoding="utf-8") as fh:
        fh.write("gerado por montar_analise.py em %s\n\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        fh.write("comando           python %s" % " ".join(
            [os.path.basename(sys.argv[0])] + sys.argv[1:]) + chr(10))
        fh.write("commit            %s" % commit_do_repo() + chr(10))
        fh.write("python            %s (%s)" % (platform.python_version(),
                                                platform.system()) + chr(10) + chr(10))
        fh.write("rotulo            %s  (%s)\n" % (args.rotulo, desc_rotulo))
        fh.write("agregacao         %s  (%s)\n" % (args.agregacao, AGREGACOES[args.agregacao]))
        fh.write("metodos           %s\n" % ", ".join(args.metodos))
        fh.write("max_testes        %s\n" % (args.max_testes or "sem limite"))
        fh.write("nome_divergente   %s\n" % ("excluido" if args.excluir_nome_divergente
                                             else "incluido (cuidado com Eager/Lazy Test)"))
        fh.write("estratos          %s\n" % ", ".join(args.estratos))
        fh.write("linhas            %d\n" % n)
        fh.write("colunas           %d" % len(cab) + chr(10))
        fh.write(chr(10) + "entradas (sha256):" + chr(10))
        for nome in ENTRADAS:
            caminho = os.path.join(c.DADOS, nome)
            fh.write("  %-22s %s" % (nome, sha256(caminho) if os.path.exists(caminho)
                                     else "(ausente)") + chr(10))
        fh.write(chr(10) + "cobertura desta configuracao:" + chr(10))
        fh.write("  arquivos de producao com teste ligado   %d" % n + chr(10))
        fh.write("  pares de binding usados                 %d" % usados + chr(10))
        fh.write("  testes por arquivo de producao (media)  %.2f"
                 % (usados / n if n else 0) + chr(10))
        if descartados:
            fh.write(chr(10) + "pares descartados pelos filtros:" + chr(10))
            for k, v in descartados.most_common():
                fh.write("  %-36s %d" % (k, v) + chr(10))
    print("\nparametros gravados em %s" % os.path.basename(params))


if __name__ == "__main__":
    main()
