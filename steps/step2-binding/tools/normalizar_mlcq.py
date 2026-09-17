"""Normaliza a planilha do MLCQ em dois CSVs: uma revisao por linha, e uma amostra por linha.

    dados/mlcq_reviews.csv   14.739 linhas - 1 por revisao, nada agregado
    dados/mlcq_samples.csv    4.770 linhas - 1 por amostra, com VARIAS colunas de rotulo

A decisao central deste script e nao tomar uma decisao: o mlcq_samples.csv carrega
sev_max, sev_media, sev_mediana e n_positivos lado a lado, e nenhuma delas e "o
rotulo". Quem analisa escolhe, e a escolha fica visivel no script de analise em vez de
soterrada dentro do dado.

Isso importa porque a regra intuitiva - "se alguem marcou > none, a classe tem o smell" -
e circular com o desenho amostral do MLCQ. O apendice (secao 2.2, fase 4) diz que as
ultimas 5115 revisoes foram alocadas so para amostras ja marcadas > none. Logo o numero
de revisores e consequencia do rotulo, e a regra do maximo recupera quase exatamente o
critério de selecao do crosscheck:

    2 revisores   3.511 amostras     0,0% positivas por "any > none"
    6 revisores     702 amostras   100,0% positivas por "any > none"

Pior: o crosscheck foi feito justamente para julgar aqueles flags, e a regra do maximo
descarta o veredito dele. Com maioria, a prevalencia cai de 25,8% para 5,2%; em todo o
MLCQ ha 19 amostras com positivo unanime. A coluna estrato torna isso explicito.

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
    """Classifica a amostra pela forca da evidencia, nao por um limiar de severidade.

    O desenho amostral do MLCQ produz tres populacoes bem diferentes, e trata-las como
    uma so e o que faz a regra do maximo parecer defensavel:

      negativo_confiavel   2+ revisores, nenhum marcou > none. Sao 3.511 amostras, e o
                           desenho as torna especialmente confiaveis: qualquer flag
                           nelas teria escalado a amostra para o crosscheck. Negativo
                           forte e raro em dataset de code smell - e um ativo.
      positivo_confiavel   a maioria marcou > none.
      disputado            alguem marcou > none, mas nao a maioria. Sao ~967 amostras, e
                           e nelas que a regra do maximo e a da maioria discordam.
                           Merecem estrato proprio: sao a "lacuna de concordancia".
      negativo_1_review    unico revisor, negativo. 23 amostras, sem corroboracao.
    """
    if n_reviews == 1:
        return "negativo_1_review" if n_positivos == 0 else "positivo_1_review"
    if n_positivos == 0:
        return "negativo_confiavel"
    return "positivo_confiavel" if maioria else "disputado"


def main():
    mapa = c.ler_mapa()

    reviews = []
    por_amostra = collections.defaultdict(list)
    amostra_meta = {}

    for r in carregar_planilha():
        sid = r["sample_id"]
        sev = (r["severity"] or "").strip().lower()
        if sev not in c.RANK:
            sys.exit("severidade inesperada na planilha: %r (amostra %s)" % (sev, sid))
        ts = str(r["review_timestamp"])
        # O crosscheck e identificado pela data, nao pela contagem de revisores: a data
        # e o criterio que os autores do MLCQ descrevem, a contagem e so o efeito dele.
        cross = ts >= c.CORTE_CROSSCHECK

        reviews.append([r["id"], sid, r["reviewer_id"], r["smell"], sev, c.RANK[sev],
                        ts, int(cross)])
        por_amostra[sid].append((c.RANK[sev], r["reviewer_id"], cross))

        if sid not in amostra_meta:
            amostra_meta[sid] = r

    n = c.escrever_csv(os.path.join(c.DADOS, "mlcq_reviews.csv"), CAB_REVIEWS,
                       sorted(reviews, key=lambda x: (x[1], x[0])))
    print("mlcq_reviews.csv        %6d linhas" % n)

    linhas = []
    estratos = collections.Counter()
    status_repo = collections.Counter()

    for sid, revs in por_amostra.items():
        meta = amostra_meta[sid]
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
                       sorted(linhas, key=lambda x: x[0]))
    print("mlcq_samples.csv        %6d linhas" % n)

    print("\nestratos (forca da evidencia dos revisores):")
    for k, v in sorted(estratos.items(), key=lambda kv: -kv[1]):
        print("  %-22s %5d  %5.1f%%" % (k, v, 100 * v / n))
    print("\nstatus do repositorio no espelho (step 1):")
    for k, v in sorted(status_repo.items(), key=lambda kv: -kv[1]):
        print("  %-22s %5d  %5.1f%%" % (k, v, 100 * v / n))


if __name__ == "__main__":
    main()
