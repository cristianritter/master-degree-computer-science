"""Auditoria humana do binding: censo dos 293 pares por um avaliador, subamostra por outro.

    dados/auditoria_humana_avaliador1.csv   293 pares, para o primeiro avaliador (censo)
    dados/auditoria_humana_avaliador2.csv    48 pares, 8 por estrato, para o segundo

A auditoria de auditoria_binding_auto.csv foi julgamento automatizado. Esta substitui o juiz:
a precisao reportada passa a ser a humana, e o automatizado vira segunda leitura, com a
concordancia calculada sobre os 293. O segundo avaliador existe para medir a concordancia
entre humanos (kappa); sem ele, "avaliador unico" seria ameaca declarada.

As planilhas sao CEGAS. Nao trazem estrato, metodo, evidencia nem sinal de risco: saber que
o par veio de referencia_estatica/import_fqn ja sugere a resposta no criterio estrito. Os
pares mantem o numero da linha em auditoria_binding.csv (coluna par), que e o que
dossie_auditoria.py --cego --indices espera. O protocolo esta em
PROTOCOLO-AUDITORIA-HUMANA.md, registrado antes de qualquer par ser julgado.

Uso:
    python auditoria_humana.py --gerar     # cria as duas planilhas (nao sobrescreve preenchida)
    python auditoria_humana.py --apurar    # precisao humana e concordancias

Como preencher, nas duas colunas, para todo par:
    correto_estrito   s/n/?   a classe de producao e o ALVO do teste
    correto_amplo     s/n/?   o teste EXECUTA codigo da classe, ainda que como fixture
"""
import argparse
import collections
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

ORIGEM = os.path.join(c.DADOS, "auditoria_binding.csv")
AUTO = os.path.join(c.DADOS, "auditoria_binding_auto.csv")
AV1 = os.path.join(c.DADOS, "auditoria_humana_avaliador1.csv")
AV2 = os.path.join(c.DADOS, "auditoria_humana_avaliador2.csv")

CAB = ["par", "correto_estrito", "correto_amplo", "observacao",
       "github_repo", "production_path", "test_path", "url_producao", "url_teste"]
# consenso so e preenchido depois que os dois julgaram de forma independente
CAB_AV2 = CAB[:4] + ["consenso_estrito", "consenso_amplo"] + CAB[4:]

POR_ESTRATO_AV2 = 8
SEMENTE = 42


def preenchidas(caminho):
    if not os.path.exists(caminho):
        return 0
    return sum(1 for r in c.ler_csv(caminho)
               if (r["correto_estrito"] or r["correto_amplo"]).strip())


def gerar():
    for arq in (AV1, AV2):
        n = preenchidas(arq)
        if n:
            sys.exit("%s ja tem %d linhas preenchidas - nao vou sobrescrever." % (arq, n))

    base = c.ler_csv(ORIGEM)
    linha = lambda i, r: [i, "", "", "", r["github_repo"], r["production_path"],
                          r["test_path"], r["url_producao"], r["url_teste"]]

    n1 = c.escrever_csv(AV1, CAB, (linha(i, r) for i, r in enumerate(base, 1)))

    # Estratificado e nao proporcional, como o sorteio original: proporcional daria quase
    # so import_fqn, e o kappa sairia de um estrato so.
    por = collections.defaultdict(list)
    for i, r in enumerate(base, 1):
        por[r["estrato_auditoria"]].append(i)
    rnd = random.Random(SEMENTE)
    sorteados = set()
    for e in sorted(por):
        sorteados.update(rnd.sample(por[e], min(POR_ESTRATO_AV2, len(por[e]))))
    # ordem da planilha original, que ja e embaralhada: a posicao nao entrega o estrato
    n2 = c.escrever_csv(AV2, CAB_AV2, (linha(i, r)[:4] + ["", ""] + linha(i, r)[4:]
                                       for i, r in enumerate(base, 1) if i in sorteados))
    print("%s: %d pares\n%s: %d pares (%d por estrato, semente %d)"
          % (AV1, n1, AV2, n2, POR_ESTRATO_AV2, SEMENTE))


def veredito(v):
    v = (v or "").strip().lower()
    return v if v in ("s", "n", "?") else ""


def kappa(pares):
    """Kappa de Cohen sobre pares (a, b) de vereditos s/n. '?' fica fora, e e contado."""
    validos = [(a, b) for a, b in pares if a in "sn" and b in "sn" and a and b]
    n = len(validos)
    if not n:
        return n, None, None
    po = sum(a == b for a, b in validos) / n
    pa = sum(a == "s" for a, _ in validos) / n
    pb = sum(b == "s" for _, b in validos) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    # pe = 1 quando os dois avaliadores so usaram uma categoria: kappa indefinido, e o
    # texto tem que reportar a concordancia percentual sozinha (paradoxo do kappa)
    k = None if pe == 1 else (po - pe) / (1 - pe)
    return n, po, k


def fmt_kappa(rotulo, n, po, k, total):
    if po is None:
        return "%-34s sem pares decididos" % rotulo
    return "%-34s n=%3d (de %d)  concordancia %5.1f%%  kappa %s" % (
        rotulo, n, total, 100 * po, "indefinido" if k is None else "%.3f" % k)


def apurar():
    base = c.ler_csv(ORIGEM)
    estrato = {i: r["estrato_auditoria"] for i, r in enumerate(base, 1)}
    peso = {r["estrato_auditoria"]: float(r["peso_no_universo"]) for r in base}
    auto = {i: r for i, r in enumerate(c.ler_csv(AUTO), 1)}
    av1 = {int(r["par"]): r for r in c.ler_csv(AV1)}
    av2 = {int(r["par"]): r for r in c.ler_csv(AV2)} if os.path.exists(AV2) else {}

    for crit in ("estrito", "amplo"):
        col = "correto_" + crit
        print("=" * 78)
        print("criterio %s" % crit.upper())

        # 1. concordancia entre humanos, nos vereditos INDEPENDENTES (antes do consenso)
        p12 = [(veredito(av1[i][col]), veredito(r[col])) for i, r in av2.items()]
        print(fmt_kappa("avaliador 1 x avaliador 2", *kappa(p12), len(p12)))

        # 2. veredito final: o consenso, onde existe; o do avaliador 1 no resto
        final = {}
        for i, r in av1.items():
            v = veredito(r[col])
            if i in av2:
                v = veredito(av2[i]["consenso_" + crit]) or v
            final[i] = v

        # 3. concordancia do juiz automatizado com o veredito humano final. Nos estratos
        # deterministicos o automatizado so preencheu o estrito (as leituras coincidem la)
        coluna_auto = "correto_amplo" if crit == "amplo" else "correto"
        pha = [(final[i], veredito(auto[i].get(coluna_auto)) or veredito(auto[i]["correto"]))
               for i in final]
        print(fmt_kappa("humano final x automatizado", *kappa(pha), len(pha)))

        # 4. precisao humana por estrato, ponderada como no auditar_binding.py
        print("\n%-38s %4s %4s %4s %8s" % ("estrato", "s", "n", "?", "precisao"))
        cont = collections.defaultdict(collections.Counter)
        for i, v in final.items():
            if v:
                cont[estrato[i]][v] += 1
        num = den = 0.0
        for e in sorted(cont):
            t = cont[e]
            dec = t["s"] + t["n"]
            p = t["s"] / dec if dec else None
            print("%-38s %4d %4d %4d %s" % (e, t["s"], t["n"], t["?"],
                                             "       -" if p is None else "%7.1f%%" % (100 * p)))
            if p is not None:
                num += p * peso[e]
                den += peso[e]
        if den:
            print("precisao global ponderada: %.1f%%" % (100 * num / den))
        print("pares com veredito: %d de %d" % (sum(1 for v in final.values() if v), len(final)))


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--gerar", action="store_true")
    g.add_argument("--apurar", action="store_true")
    args = ap.parse_args()
    gerar() if args.gerar else apurar()


if __name__ == "__main__":
    main()
