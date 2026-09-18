"""Reapura todo numero afirmado no README do step 3.

Mesmo papel do conferir_dados.py no step 2: resultado citado em texto que nao sai de um
comando envelhece em silencio. Aqui o risco e maior, porque as tabelas do step 2 podem ser
regeneradas com outros parametros - e ai o README do step 3 passaria a descrever numeros
que o dado nao produz mais.

Falha com codigo 1 se algum numero divergir.

Uso:
    python conferir_resultados.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c
import estat
from variaveis import pares, rotulo_agregado

falhas = []


def exigir(condicao, descricao, observado):
    marca = "ok  " if condicao else "FALHA"
    print("  [%s] %-62s %s" % (marca, descricao, observado))
    if not condicao:
        falhas.append("%s (observado: %s)" % (descricao, observado))


def perto(a, b, tol=0.001):
    return abs(a - b) <= tol


def conferir_caracterizacao():
    print("\nCARACTERIZACAO (secao 2)")
    print("-" * 24)
    linhas = c.ler_ramo("deterministico")
    exigir(len(linhas) == 730, "ramo deterministico tem 730 arquivos", len(linhas))

    agregado = [rotulo_agregado(r) for r in linhas]
    agregado = [v for v in agregado if v is not None]
    zeros = 100.0 * sum(1 for v in agregado if v == 0) / len(agregado)
    exigir(perto(zeros, 72.1, 0.1), "72,1% de zeros no rotulo agregado", "%.1f%%" % zeros)

    # a coluna de distintos nao pode passar do numero de smells habilitados
    mx = max(int(r["ts_n_distintos"]) for r in linhas)
    exigir(mx <= len(c.SMELLS),
           "ts_n_distintos nao passa dos %d smells habilitados" % len(c.SMELLS), mx)

    lazy = max(c.num(r[c.coluna_ts("Lazy Test")]) for r in linhas)
    exigir(perto(lazy, 1116, 0.5), "maximo de Lazy Test e 1.116", lazy)


def conferir_primeira_rodada():
    print("\nPRIMEIRA RODADA (secao 4)")
    print("-" * 25)

    esperado = {
        # ramo, desfecho -> (rho, p)
        ("deterministico", "bruto"): (0.092, 0.012),
        ("deterministico", "densidade"): (0.047, 0.204),
        ("deterministico", "distintos"): (0.084, 0.024),
        ("ampliado", "bruto"): (0.015, 0.568),
        ("ampliado", "densidade"): (0.003, 0.915),
        ("ampliado", "distintos"): (0.001, 0.973),
    }
    for (ramo, chave), (rho_esp, p_esp) in sorted(esperado.items()):
        linhas = c.ler_ramo(ramo)
        x, y, _ = pares(linhas, chave, rotulo_agregado)
        rho, p, _, _, n = estat.spearman(x, y)
        exigir(perto(rho, rho_esp) and perto(p, p_esp, 0.002),
               "%s/%s: rho %.3f e p %.3f" % (ramo, chave, rho_esp, p_esp),
               "rho=%.3f p=%.3f N=%d" % (rho, p, n))

    print("\n  correlacoes parciais, controlando n_metodos_teste:")
    for chave, r_esp in (("bruto", 0.058), ("distintos", 0.055)):
        linhas = c.ler_ramo("deterministico")
        x, y, tam = pares(linhas, chave, rotulo_agregado)
        r, p, n = estat.parcial(x, y, tam)
        exigir(perto(r, r_esp), "parcial de %s cai para %.3f" % (chave, r_esp),
               "%.3f (p=%.3f)" % (r, p))

    print("\n  o confundidor:")
    linhas = c.ler_ramo("deterministico")
    validos = [r for r in linhas if rotulo_agregado(r) is not None
               and c.num(r["n_metodos_teste"]) is not None]
    rot = [rotulo_agregado(r) for r in validos]
    for nome, col, esp in (("n_metodos_teste", "n_metodos_teste", 0.079),
                           ("loc_teste", "loc_teste", 0.091)):
        rho, p, _, _, n = estat.spearman(rot, [c.num(r[col]) for r in validos])
        exigir(perto(rho, esp), "code smell x %s: rho %.3f" % (nome, esp),
               "%.3f (p=%.3f)" % (rho, p))

    x, y, tam = pares(linhas, "bruto", rotulo_agregado)
    rho, _, _, _, _ = estat.spearman(x, tam)
    exigir(perto(rho, 0.554), "test smell bruto x tamanho: rho 0,554", "%.3f" % rho)


def conferir_caderno():
    """O caderno da secao 4 declara um total de testes; o CSV tem que conter todos eles."""
    print("\nCADERNO DE TENTATIVAS (secao 4)")
    print("-" * 31)
    caminho = os.path.join(c.STEP, "analises", "01-correlacao-agregada", "dados", "exploracao.csv")
    if not os.path.exists(caminho):
        exigir(False, "exploracao.csv existe", "ausente - rode explorar.py --por-smell --csv")
        return
    import csv
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    simples = sum(1 for r in linhas if r["analise"] == "simples")
    parciais = sum(1 for r in linhas if r["analise"] == "parcial")
    exigir(len(linhas) == 40, "exploracao.csv tem 40 resultados gravados", len(linhas))
    exigir(simples == 30, "30 correlacoes simples", simples)
    exigir(parciais == 6, "6 correlacoes parciais", parciais)

    nominais = [r for r in linhas
                if r["analise"] == "simples" and r["p"] and float(r["p"]) < 0.05]
    print("  significancias nominais (p < 0,05):")
    for r in nominais:
        print("    %-16s %-14s %-11s rho=%6.3f  p=%.3f"
              % (r["ramo"], r["code_smell"], r["desfecho"], float(r["rho"]), float(r["p"])))
    exigir(len(nominais) == 4, "4 significancias nominais entre as simples", len(nominais))
    exigir(all(r["desfecho"] in ("bruto", "distintos") for r in nominais),
           "todas as significancias sao em desfecho sensivel a tamanho",
           ", ".join(sorted({r["desfecho"] for r in nominais})))


def conferir_segunda_rodada():
    """As analises 02 e 03: nenhuma sobrevive ao ajuste para comparacoes multiplas."""
    import csv
    print("")
    print("ANALISES 02 e 03")
    print("-" * 24)

    caminho = os.path.join(c.STEP, "analises", "02-por-test-smell", "dados", "por_test_smell.csv")
    if not os.path.exists(caminho):
        exigir(False, "por_test_smell.csv existe", "ausente - rode por_test_smell.py --csv")
    else:
        with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
            L = list(csv.DictReader(f))
        exigir(len(L) == 52, "analise 1 tem 52 testes", len(L))
        sobrevivem = [r for r in L if float(r["p_ajustado"]) < 0.05]
        exigir(len(sobrevivem) == 0,
               "nenhum test smell sobrevive ao ajuste FDR", len(sobrevivem))
        menor = min(float(r["p_ajustado"]) for r in L)
        exigir(perto(menor, 0.283, 0.001), "menor p ajustado e 0,283", "%.3f" % menor)
        # Eager e Lazy sao os que dependem da classe de producao: sao os mais proximos de
        # zero, que e o achado negativo com mais conteudo da secao
        for smell, esp in (("Eager Test", -0.020), ("Lazy Test", 0.038)):
            r = [x for x in L if x["test_smell"] == smell and x["desfecho"] == "densidade"
                 and x["recorte"] == "todas"][0]
            exigir(perto(float(r["rho"]), esp), "%s em densidade: rho %.3f" % (smell, esp),
                   r["rho"][:6])

    caminho = os.path.join(c.STEP, "analises", "03-extremos", "dados", "extremos.csv")
    if not os.path.exists(caminho):
        exigir(False, "extremos.csv existe", "ausente - rode extremos.py --csv")
        return
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        L = list(csv.DictReader(f))
    exigir(len(L) == 6, "analise 2 tem 6 testes", len(L))
    nominais = [r for r in L if float(r["p"]) < 0.05]
    exigir(len(nominais) == 0, "nenhum extremo alcanca p < 0,05", len(nominais))
    det = {r["desfecho"]: r for r in L if r["ramo"] == "deterministico"}
    exigir(int(det["bruto"]["n_positivo"]) == 42 and int(det["bruto"]["n_negativo"]) == 523,
           "deterministico: 42 positivos e 523 negativos confiaveis",
           "%s e %s" % (det["bruto"]["n_positivo"], det["bruto"]["n_negativo"]))
    # o grupo negativo tem densidade LIGEIRAMENTE MAIOR: ausencia de separacao, nao
    # tendencia fraca na direcao esperada
    dens = det["densidade"]
    exigir(float(dens["mediana_negativo"]) > float(dens["mediana_positivo"]),
           "na densidade, a mediana do grupo negativo e maior que a do positivo",
           "%s vs %s" % (dens["mediana_negativo"], dens["mediana_positivo"]))


def conferir_disputados():
    """A analise 04: inconclusiva por poder, nao nula. O verificador precisa distinguir."""
    import csv
    print("")
    print("ANALISE 04 - disputados")
    print("-" * 23)
    caminho = os.path.join(c.STEP, "analises", "04-disputados", "dados", "disputados.csv")
    if not os.path.exists(caminho):
        exigir(False, "disputados.csv existe", "ausente - rode disputados.py --csv")
        return
    with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
        L = list(csv.DictReader(f))
    exigir(len(L) == 6, "analise 04 tem 6 testes", len(L))
    det = {r["desfecho"]: r for r in L if r["ramo"] == "deterministico"}
    exigir(int(det["bruto"]["n_confirmado"]) == 42 and int(det["bruto"]["n_disputado"]) == 155,
           "deterministico: 42 confirmados e 155 disputados",
           "%s e %s" % (det["bruto"]["n_confirmado"], det["bruto"]["n_disputado"]))
    nominais = [r for r in L if float(r["p"]) < 0.05]
    exigir(len(nominais) == 0, "nenhum resultado com p < 0,05", len(nominais))
    # o ponto da analise: TODOS os deltas ficam abaixo do detectavel - inconclusiva
    abaixo = [r for r in L if abs(float(r["delta"])) < float(r["delta_detectavel"])]
    exigir(len(abaixo) == 6,
           "todos os 6 deltas ficam abaixo do detectavel (inconclusiva, nao nula)",
           "%d de 6" % len(abaixo))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    conferir_caracterizacao()
    conferir_primeira_rodada()
    conferir_segunda_rodada()
    conferir_disputados()
    conferir_caderno()

    print()
    if falhas:
        print("%d NUMERO(S) DIVERGENTE(S):" % len(falhas))
        for f in falhas:
            print("  - %s" % f)
        print("\nO README do step 3 descreve um dado que nao existe mais.")
        sys.exit(1)
    print("todos os numeros do README conferem")


if __name__ == "__main__":
    main()
