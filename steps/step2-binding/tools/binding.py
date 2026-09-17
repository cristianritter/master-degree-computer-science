"""Liga cada arquivo de producao anotado no MLCQ as classes de teste que o exercitam.

    dados/binding.csv           1 linha por par (arquivo de producao, classe de teste)
    dados/production_files.csv  1 linha por arquivo de producao anotado, ligado ou nao

O binding.csv e muitos-para-muitos de proposito. 3,0% dos arquivos de producao tem mais
de uma classe de teste apontando para eles (legitimamente ate 8), e colapsar isso numa
linha por classe forcaria a decidir agora como agregar varios testes - soma, media,
maximo - deixando a decisao enterrada no dado. Ela fica em montar_analise.py.

O metodo de cada par e uma COLUNA, nao um pressuposto, porque os metodos tem precisao
diferente e o artigo precisa poder mostrar que o achado se mantem em mais de um:

  caminho_exato          o ProductionFileName que o proprio JNose resolveu, reduzido a
                         caminho relativo. Cobre 15,8% das amostras. Viesado: a resolucao
                         parte do nome da classe, que esta errado nas 6.842 linhas de
                         classe aninhada, onde production fica vazio em 93,8% - ou seja,
                         a falta de ligacao nao e aleatoria.
  convencao              X.java <- XTest.java / XTests.java / XTestCase.java / XIT.java /
                         XITCase.java, casando por caminho e nunca por nome solto. Cobre
                         +1,7%. Barato e independente do defeito acima.
  referencia_estatica    a classe de teste referencia o tipo de producao no codigo
                         (refs_producao.py). Preenchido so se aquele script tiver rodado.

Somados, caminho_exato e convencao ligam 17,7% das amostras em repositorio disponivel.
As duas quase nao se somam (15,8% + 1,7%), o que indica que erram nos mesmos casos: nao
e falta de estrategia, e falta de sinal. E por isso que a referencia estatica existe.

O production_files.csv e a contrapartida: ele mantem os NAO ligados com um motivo, porque
"classe com code smell nao tem teste" e potencialmente um achado do artigo, e porque a
cadeia de atrito (4.770 amostras -> 4.300 em repo disponivel -> 759 com teste) e uma
tabela que o artigo vai precisar declarar.

Uso:
    python binding.py
"""
import collections
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

# Sufixos de classe de teste, na ordem em que sao tentados. Os dois ultimos sao a
# convencao de teste de integracao do maven-failsafe.
SUFIXOS = ["Test", "Tests", "TestCase", "IT", "ITCase"]

CAB_BINDING = [
    "github_repo", "production_path", "test_path", "metodo", "ambiguo", "n_candidatos",
]

CAB_PRODUCTION = [
    "github_repo", "production_path", "n_amostras", "sample_ids", "smells",
    "estratos", "sev_max", "repo_status",
    "n_testes", "metodos", "motivo_sem_ligacao",
]

REFS = "refs_producao.csv"     # opcional, gerado por refs_producao.py


def carregar_refs():
    """Le o CSV da estrategia 3, se existir. Devolve {(repo, production_path): [test_path]}."""
    caminho = os.path.join(c.DADOS, REFS)
    if not os.path.exists(caminho):
        return {}, False
    d = collections.defaultdict(list)
    for r in c.ler_csv(caminho):
        d[(r["github_repo"], r["production_path"])].append(r["test_path"])
    return d, True


def main():
    samples = c.ler_csv(os.path.join(c.DADOS, "mlcq_samples.csv"))
    classes = c.ler_csv(os.path.join(c.DADOS, "test_classes.csv"))

    # indices do lado do JNose
    por_producao = collections.defaultdict(list)      # (repo, prod_path) -> [test_path]
    por_nome = collections.defaultdict(list)          # (repo, basename) -> [test_path]
    repos_com_teste = set()
    for t in classes:
        repo, path = t["github_repo"], t["path"]
        repos_com_teste.add(repo)
        por_nome[(repo, t["nome_arquivo"])].append(path)
        if t["production_path"]:
            por_producao[(repo, t["production_path"])].append(path)

    refs, tem_refs = carregar_refs()
    if tem_refs:
        print("refs_producao.csv presente: estrategia referencia_estatica ativa")
    else:
        print("refs_producao.csv ausente: so caminho_exato e convencao")

    # agrupa as amostras por arquivo de producao. Varias amostras caem no mesmo arquivo:
    # long method e feature envy sao anotados por funcao, e a unidade da RQ e a classe.
    por_arquivo = collections.defaultdict(list)
    for s in samples:
        por_arquivo[(s["github_repo"], s["path"])].append(s)

    pares = []
    prod_linhas = []
    motivos = collections.Counter()
    metodo_cobertura = collections.Counter()

    for (repo, prod), amostras in sorted(por_arquivo.items()):
        status = amostras[0]["repo_status"]
        encontrados = []      # (test_path, metodo)

        if status == "HASH_OK":
            for t in por_producao.get((repo, prod), []):
                encontrados.append((t, "caminho_exato"))

            base = os.path.basename(prod)[:-5] if prod.endswith(".java") else os.path.basename(prod)
            ja = {t for t, _ in encontrados}
            for suf in SUFIXOS:
                for t in por_nome.get((repo, base + suf), []):
                    if t not in ja:
                        encontrados.append((t, "convencao"))
                        ja.add(t)

            for t in refs.get((repo, prod), []):
                if t not in ja:
                    encontrados.append((t, "referencia_estatica"))
                    ja.add(t)

        # ambiguo marca o par cujo metodo produziu mais de um candidato. Nao e erro - uma
        # classe pode ter varios testes - mas para a convencao e sinal de risco: e o caso
        # do AppTest que aparece 159 vezes no mesmo repositorio.
        n_por_metodo = collections.Counter(m for _, m in encontrados)
        for t, m in encontrados:
            pares.append([repo, prod, t, m, int(n_por_metodo[m] > 1), n_por_metodo[m]])
            metodo_cobertura[m] += 1

        if encontrados:
            motivo = ""
        elif status != "HASH_OK":
            motivo = "repo_indisponivel"
        elif repo not in repos_com_teste:
            motivo = "projeto_sem_classe_de_teste"
        else:
            motivo = "sem_ligacao_resolvida"
        motivos[motivo or "ligado"] += 1

        prod_linhas.append([
            repo, prod, len(amostras),
            "|".join(a["sample_id"] for a in amostras),
            "|".join(sorted({a["smell"] for a in amostras})),
            "|".join(sorted({a["estrato"] for a in amostras})),
            max(int(a["sev_max"]) for a in amostras),
            status,
            len(encontrados), "|".join(sorted({m for _, m in encontrados})), motivo,
        ])

    n = c.escrever_csv(os.path.join(c.DADOS, "binding.csv"), CAB_BINDING, pares)
    print("\nbinding.csv           %6d pares" % n)
    for m, v in metodo_cobertura.most_common():
        print("  %-22s %6d pares" % (m, v))

    n = c.escrever_csv(os.path.join(c.DADOS, "production_files.csv"), CAB_PRODUCTION,
                       prod_linhas)
    print("\nproduction_files.csv  %6d arquivos de producao anotados" % n)
    for k, v in motivos.most_common():
        print("  %-30s %5d  %5.1f%%" % (k, v, 100 * v / n))

    # Cadeia de atrito: o recorte que o artigo tem que declarar.
    ligados = {(r[0], r[1]) for r in pares}
    print("\ncadeia de atrito (amostras do MLCQ):")
    print("  %5d  no MLCQ" % len(samples))
    hash_ok = [s for s in samples if s["repo_status"] == "HASH_OK"]
    print("  %5d  em repositorio disponivel (HASH_OK)" % len(hash_ok))
    com = [s for s in hash_ok if (s["github_repo"], s["path"]) in ligados]
    print("  %5d  com classe de teste identificada  (%.1f%% dos disponiveis)"
          % (len(com), 100 * len(com) / len(hash_ok)))
    for estrato in ("positivo_confiavel", "disputado", "negativo_confiavel", "negativo_1_review"):
        a = sum(1 for s in com if s["estrato"] == estrato)
        b = sum(1 for s in hash_ok if s["estrato"] == estrato)
        print("     %-20s %4d de %4d" % (estrato, a, b))


if __name__ == "__main__":
    main()
