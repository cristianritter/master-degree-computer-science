"""Normaliza a planilha do MLCQ em dois CSVs: uma revisao por linha, e uma unidade por linha.

    dados/mlcq_reviews.csv   14.739 linhas - 1 por revisao, nada agregado
    dados/mlcq_samples.csv    9.517 linhas - 1 por (amostra, smell), com VARIAS colunas de rotulo

**A unidade de rotulo e (sample_id, smell), nao sample_id.** No MLCQ cada revisor julga a
mesma amostra para dois smells de uma vez - blob e data class nas classes, feature envy e
long method nas funcoes -, e cada julgamento vira uma linha, com milissegundos de diferenca.
4.747 das 4.770 amostras tem os dois smells. Ate 17/10/2026 este script agrupava so por
sample_id: misturava as severidades dos dois smells numa media so, pegava o smell da
primeira linha como "o" smell da amostra e contava 1 revisor x 2 smells como "2
revisores". O README do step 2 (secao 3) registra o defeito e os numeros corrigidos.

A decisao central deste script e nao tomar uma decisao: o mlcq_samples.csv carrega
sev_max, sev_media, sev_mediana e n_positivos lado a lado, e nenhuma delas e "o
rotulo". Quem analisa escolhe, e a escolha fica visivel no script de analise em vez de
soterrada dentro do dado.

Isso importa porque a regra intuitiva - "se alguem marcou > none, a classe tem o smell" -
e circular com o desenho amostral do MLCQ. O apendice (secao 2.2, fase 4) diz que as
ultimas revisoes foram alocadas so para amostras ja marcadas > none: o numero de
revisores e consequencia do rotulo. A coluna estrato torna isso explicito, e
conferir_dados.py --secao 3 mede o efeito.

Uso:
    python normalizar_mlcq.py
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c


CAB_REVIEWS = [
    "review_id", "sample_id", "reviewer_id", "smell", "severidade", "severidade_num",
    "review_timestamp", "is_crosscheck",
]

CAB_SAMPLES = [
    # identidade
    "sample_id", "smell", "granularidade", "code_name", "path", "start_line", "end_line",
    # procedencia do repositorio (vem do step 1)
    "mlcq_repo", "github_repo", "repo_status", "commit_hash", "is_industry_relevant",
    # o que os revisores disseram
    "n_reviews", "n_revisores", "severidades", "n_positivos", "n_major_ou_mais",
    "n_reviews_crosscheck",
    # rotulos derivados - nenhum e "o" rotulo
    "sev_max", "sev_media", "sev_mediana", "pos_any", "pos_maioria", "pos_unanime",
    "pos_any_major", "foi_crosscheck", "estrato",
]


def carregar_planilha(xlsx=c.XLSX):
    """Le a aba MLCQ da planilha e devolve as linhas como dicionarios."""
    try:
        import openpyxl
    except ImportError:
        sys.exit("falta o openpyxl: pip install openpyxl")
    if not os.path.exists(xlsx):
        sys.exit("planilha do MLCQ nao encontrada em %s" % xlsx)
    wb = openpyxl.load_workbook(xlsx, read_only=True)
    linhas = wb["MLCQ"].iter_rows(values_only=True)
    cabecalho = [str(x) for x in next(linhas)]
    for linha in linhas:
        if linha[0] is None:          # a planilha tem linhas vazias no fim
            continue
        yield dict(zip(cabecalho, linha))


def mediana(sevs):
    """Mediana da severidade. Para escala ordinal ela e a tendencia central apropriada -
    a media trata a distancia none->minor como igual a major->critical, o que a escala do
    MLCQ nao garante. Com numero par de revisores fica a media dos dois centrais, entao
    pode dar meio ponto; e informacao, nao arredondamento.
    """
    s = sorted(sevs)
    meio = len(s) // 2
    v = s[meio] if len(s) % 2 else (s[meio - 1] + s[meio]) / 2
    return round(float(v), 2)   # sempre float: com N par a mediana cai no meio ponto


def estrato_de(n_reviews, n_positivos, maioria):
    """Classifica a unidade (amostra, smell) pela forca da evidencia, nao por um limiar.

    O desenho amostral do MLCQ produz populacoes bem diferentes, e trata-las como uma so e
    o que faz a regra do maximo parecer defensavel:

      negativo_confiavel   2+ revisores, nenhum marcou > none.
      positivo_confiavel   a maioria marcou > none.
      disputado            alguem marcou > none, mas nao a maioria. E nelas que a regra
                           do maximo e a da maioria discordam: a "lacuna de concordancia".
      negativo_1_review    unico revisor, negativo. A maioria das unidades do MLCQ: pelo
                           desenho amostral, um flag teria levado a unidade ao
                           crosscheck, mas nenhum segundo revisor a corrobora.
      positivo_1_review    unico revisor, positivo. Raro, pelo mesmo motivo.

    Uma revisao conta uma vez por revisor: n_reviews e n_revisores coincidem na unidade
    (conferir_dados.py exige), e por isso os limiares aqui podem usar n_reviews.
    """
    if n_reviews == 1:
        return "negativo_1_review" if n_positivos == 0 else "positivo_1_review"
    if n_positivos == 0:
        return "negativo_confiavel"
    return "positivo_confiavel" if maioria else "disputado"


def main():
    mapa = c.ler_mapa()

    reviews = []
    # chave (sample_id, smell): cada revisor julga a amostra para dois smells, e misturar
    # os dois numa unidade so foi o defeito corrigido em 17/10/2026 (docstring)
    por_amostra = collections.defaultdict(list)
    amostra_meta = {}
    repetidas = []

    for r in carregar_planilha():
        sid = r["sample_id"]
        unidade = (sid, r["smell"])
        sev = (r["severity"] or "").strip().lower()
        if sev not in c.RANK:
            sys.exit("severidade inesperada na planilha: %r (amostra %s)" % (sev, sid))
        ts = str(r["review_timestamp"])
        # O crosscheck e identificado pela data, nao pela contagem de revisores: a data
        # e o criterio que os autores do MLCQ descrevem, a contagem e so o efeito dele.
        cross = ts >= c.CORTE_CROSSCHECK

        reviews.append([r["id"], sid, r["reviewer_id"], r["smell"], sev, c.RANK[sev],
                        ts, int(cross)])
        # Um julgamento por revisor por unidade. A planilha tem uma submissao em dobro
        # (amostra 5715127, revisor 3, mesmas severidades, 16 ms de diferenca): contada
        # duas vezes, viraria "2 revisores" concordando. mlcq_reviews.csv fica bruto.
        if any(rid == r["reviewer_id"] for _, rid, _ in por_amostra[unidade]):
            repetidas.append(str(r["id"]))
        else:
            por_amostra[unidade].append((c.RANK[sev], r["reviewer_id"], cross))

        if unidade not in amostra_meta:
            amostra_meta[unidade] = r

    n = c.escrever_csv(os.path.join(c.DADOS, "mlcq_reviews.csv"), CAB_REVIEWS,
                       sorted(reviews, key=lambda x: (x[1], x[0])))
    print("mlcq_reviews.csv        %6d linhas" % n)
    print("  revisoes repetidas do mesmo revisor na mesma unidade, contadas uma vez: %d (%s)"
          % (len(repetidas), ", ".join(repetidas)))

    linhas = []
    estratos = collections.Counter()
    status_repo = collections.Counter()

    for unidade, revs in por_amostra.items():
        sid = unidade[0]
        meta = amostra_meta[unidade]
        sevs = [s for s, _, _ in revs]
        n_reviews = len(sevs)
        n_pos = sum(1 for s in sevs if s >= c.RANK["minor"])
        n_major = sum(1 for s in sevs if s >= c.RANK["major"])
        maioria = n_pos > n_reviews / 2
        unanime = n_pos == n_reviews

        mlcq_repo = c.repo_do_mlcq(meta["repository"])
        m = mapa.get(mlcq_repo)
        if m is None:
            # O repos_map do step 1 cobre os 522 repositorios do MLCQ; uma amostra fora
            # dele significaria que a planilha mudou. Falha alto em vez de rotular
            # silenciosamente como indisponivel.
            sys.exit("repositorio %s (amostra %s) nao esta no repos_map do step 1"
                     % (mlcq_repo, sid))
        status_repo[m["status"]] += 1

        smell = meta["smell"]
        granularidade = meta["type"]
        if c.CODE_SMELLS.get(smell) != granularidade:
            sys.exit("granularidade inesperada: smell %r com type %r (amostra %s)"
                     % (smell, granularidade, sid))

        estrato = estrato_de(n_reviews, n_pos, maioria)
        estratos[estrato] += 1

        linhas.append([
            sid, smell, granularidade, meta["code_name"],
            c.normalizar_mlcq_path(meta["path"]), meta["start_line"], meta["end_line"],
            mlcq_repo, m["github_repo"], m["status"], meta["commit_hash"],
            meta["is_from_industry_relevant_project"],
            n_reviews, len({rid for _, rid, _ in revs}),
            "|".join(c.SEVERIDADES[s] for s in sorted(sevs, reverse=True)),
            n_pos, n_major, sum(1 for _, _, cc in revs if cc),
            max(sevs), round(sum(sevs) / n_reviews, 4), mediana(sevs),
            int(max(sevs) >= c.RANK["minor"]), int(maioria), int(unanime and n_pos > 0),
            int(max(sevs) >= c.RANK["major"]),
            int(any(cc for _, _, cc in revs)), estrato,
        ])

    n = c.escrever_csv(os.path.join(c.DADOS, "mlcq_samples.csv"), CAB_SAMPLES,
                       sorted(linhas, key=lambda x: (x[0], x[1])))
    print("mlcq_samples.csv        %6d linhas" % n)

    print("\nestratos (forca da evidencia dos revisores):")
    for k, v in sorted(estratos.items(), key=lambda kv: -kv[1]):
        print("  %-22s %5d  %5.1f%%" % (k, v, 100 * v / n))
    print("\nstatus do repositorio no espelho (step 1):")
    for k, v in sorted(status_repo.items(), key=lambda kv: -kv[1]):
        print("  %-22s %5d  %5.1f%%" % (k, v, 100 * v / n))


if __name__ == "__main__":
    main()
