"""Sorteia pares do binding para conferencia manual, e apura a auditoria quando preenchida.

    dados/auditoria_binding.csv   planilha de auditoria (sorteada, com coluna em branco)

O binding e heuristica: caminho_exato herda o nome de classe do jnose-core, que esta errado
em 6,4% das linhas; convencao casa por sufixo; referencia_estatica confunde "o teste
referencia a classe" com "o teste testa a classe" - o piloto ligou CanalEntry.java, um DTO
de protocolo, a 18 classes de teste que so o importam.

Sem medir, o artigo teria que escrever "assumimos que o binding esta correto", que e a
frase que um revisor ataca primeiro. Com esta auditoria ele escreve a precisao observada
por estrategia, com intervalo de confianca, e trata o resto como ameaca a validade
declarada. O custo e uma tarde de trabalho manual.

A amostragem e estratificada por (metodo, evidencia) e nao proporcional: as estrategias
raras precisam de N proprio para ter precisao estimavel, e proporcional daria 2 pares de
convencao. O peso de cada estrato para a precisao global fica na coluna
peso_no_universo.

Cada linha traz as URLs dos dois arquivos no espelho do GitHub, no commit da coleta, para
a conferencia ser um clique em vez de um clone.

Uso:
    python auditar_binding.py                  # sorteia 50 por estrato (semente 42)
    python auditar_binding.py --por-estrato 30 --semente 7
    python auditar_binding.py --apurar         # le a coluna correto e calcula a precisao

Como preencher: abra dados/auditoria_binding.csv e escreva na coluna correto
    s   o teste exercita a classe de producao
    n   nao exercita (so importa, e homonimo, e fixture)
    ?   nao consegui decidir
Depois rode --apurar. O script nao sobrescreve um arquivo ja preenchido.
"""
import argparse
import collections
import csv
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

SAIDA = os.path.join(c.DADOS, "auditoria_binding.csv")

CAB = [
    "correto", "observacao",
    "estrato_auditoria", "peso_no_universo",
    "github_repo", "production_path", "test_path", "metodo", "evidencia",
    "ambiguo", "n_testes_da_producao", "url_producao", "url_teste",
]


def url(repo, commit, path):
    return "https://github.com/cristianritter/%s/blob/%s%s" % (repo, commit, path)


def sortear(args):
    if os.path.exists(SAIDA):
        preenchidas = sum(1 for r in c.ler_csv(SAIDA) if (r["correto"] or "").strip())
        if preenchidas:
            sys.exit("%s ja tem %d linhas preenchidas - nao vou sobrescrever.\n"
                     "Renomeie o arquivo ou rode --apurar." % (SAIDA, preenchidas))

    pares = c.ler_csv(os.path.join(c.DADOS, "binding.csv"))
    mapa = c.ler_mapa()
    commit = {m["github_repo"]: m["head_atual"] for m in mapa.values()}

    # evidencia so existe para a estrategia 3; vem do refs_producao.csv
    evidencia = {}
    refs = os.path.join(c.DADOS, "refs_producao.csv")
    if os.path.exists(refs):
        for r in c.ler_csv(refs):
            # um par pode ter mais de uma evidencia; a mais forte manda
            k = (r["github_repo"], r["production_path"], r["test_path"])
            ordem = {"import_fqn": 0, "wildcard": 1, "mesmo_pacote": 2}
            if k not in evidencia or ordem[r["evidencia"]] < ordem[evidencia[k]]:
                evidencia[k] = r["evidencia"]

    n_testes = collections.Counter((p["github_repo"], p["production_path"]) for p in pares)

    estratos = collections.defaultdict(list)
    for p in pares:
        k = (p["github_repo"], p["production_path"], p["test_path"])
        # a estrategia 3 traz a evidencia do refs_producao.csv; a convencao ja traz a
        # dela no proprio binding.csv (caminho_espelhado x so_basename), e sao riscos
        # diferentes o bastante para virarem estratos separados.
        if p["metodo"] == "referencia_estatica":
            ev = evidencia.get(k, "")
        else:
            ev = (p.get("evidencia") or "").strip()
        estratos[(p["metodo"], ev)].append((p, ev))

    rnd = random.Random(args.semente)
    linhas = []
    print("estratos de auditoria (semente %d):" % args.semente)
    for chave, itens in sorted(estratos.items()):
        amostra = itens if len(itens) <= args.por_estrato else rnd.sample(itens, args.por_estrato)
        nome = chave[0] + ("/" + chave[1] if chave[1] else "")
        print("  %-42s %6d pares, %3d sorteados" % (nome, len(itens), len(amostra)))
        for p, ev in amostra:
            repo = p["github_repo"]
            linhas.append([
                "", "", nome, round(len(itens) / len(pares), 6),
                repo, p["production_path"], p["test_path"], p["metodo"], ev,
                p["ambiguo"], n_testes[(repo, p["production_path"])],
                url(repo, commit.get(repo, "HEAD"), p["production_path"]),
                url(repo, commit.get(repo, "HEAD"), p["test_path"]),
            ])

    rnd.shuffle(linhas)   # ordem cega, para o auditor nao inferir o estrato pela posicao
    n = c.escrever_csv(SAIDA, CAB, linhas)
    print("\n%d pares para auditar em %s" % (n, SAIDA))
    print("preencha a coluna correto com s / n / ? e rode: python auditar_binding.py --apurar")


def apurar(arquivo=None, criterio="estrito"):
    """Precisao por estrato. O criterio escolhe a coluna de veredito.

    estrito  correto        a classe de producao e o ALVO do teste
    amplo    correto_amplo  o teste EXECUTA codigo da classe, ainda que como fixture

    Nos estratos deterministicos a pergunta e "a regra casou o arquivo certo?" e as duas
    leituras coincidem, entao correto_amplo fica vazio la e o estrito e reusado.
    """
    arquivo = arquivo or SAIDA
    linhas = c.ler_csv(arquivo)
    coluna = "correto_amplo" if criterio == "amplo" else "correto"
    por = collections.defaultdict(lambda: collections.Counter())
    for r in linhas:
        v = (r.get(coluna) or "").strip().lower() or (r["correto"] or "").strip().lower()
        if v:
            por[r["estrato_auditoria"]][v] += 1
    if not por:
        sys.exit("nenhuma linha preenchida em %s" % arquivo)

    peso = {r["estrato_auditoria"]: float(r["peso_no_universo"]) for r in linhas}

    # Quantos pares cada estrato tem no binding inteiro: se a auditoria cobriu todos, o
    # estrato e censo e a precisao e exata - intervalo de confianca ali nao significa nada,
    # porque nao houve amostragem.
    universo = collections.Counter()
    for r in c.ler_csv(os.path.join(c.DADOS, "binding.csv")):
        ev = (r.get("evidencia") or "").strip()
        universo[r["metodo"] + ("/" + ev if ev else "")] += 1
    refs = os.path.join(c.DADOS, "refs_producao.csv")
    if os.path.exists(refs):
        universo.update({})  # estratos da estrategia 3 ja vem do proprio sorteio
    print("%-42s %5s %5s %5s %8s %s" % ("estrato", "s", "n", "?", "precisao", "IC95%"))
    global_num = global_den = 0.0
    for e in sorted(por):
        t = por[e]
        dec = t["s"] + t["n"]
        if not dec:
            print("%-42s %5d %5d %5d        -" % (e, t["s"], t["n"], t["?"]))
            continue
        p = t["s"] / dec
        # Wald simples; com N de auditoria (30-50 por estrato) e suficiente para o texto,
        # e o script imprime o N para o leitor julgar.
        if universo.get(e) and dec >= universo[e]:
            print("%-42s %5d %5d %5d %7.1f%%  censo (exato, n=%d)"
                  % (e, t["s"], t["n"], t["?"], 100 * p, dec))
        else:
            meia = 1.96 * (p * (1 - p) / dec) ** 0.5
            print("%-42s %5d %5d %5d %7.1f%%  +-%.1f pp  (n=%d)"
                  % (e, t["s"], t["n"], t["?"], 100 * p, 100 * meia, dec))
        global_num += p * peso.get(e, 0)
        global_den += peso.get(e, 0)
    if global_den:
        print("\nprecisao global ponderada pelo peso de cada estrato no binding: %.1f%%"
              % (100 * global_num / global_den))
    print("\nlinhas preenchidas: %d de %d"
          % (sum(sum(t.values()) for t in por.values()), len(linhas)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--por-estrato", type=int, default=50)
    ap.add_argument("--semente", type=int, default=42)
    ap.add_argument("--arquivo", help="planilha a apurar (padrao: auditoria_binding.csv)")
    ap.add_argument("--criterio", choices=["estrito", "amplo"], default="estrito",
                    help="estrito: a classe e o alvo do teste; amplo: o teste executa "
                         "codigo da classe, ainda que como fixture")
    ap.add_argument("--apurar", action="store_true")
    args = ap.parse_args()
    apurar(args.arquivo, args.criterio) if args.apurar else sortear(args)


if __name__ == "__main__":
    main()
