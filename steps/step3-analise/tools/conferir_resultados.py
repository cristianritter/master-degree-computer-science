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
import explorar as ex

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

    agregado = [ex.rotulo_agregado(r) for r in linhas]
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
        x, y, _ = ex.pares(linhas, chave, ex.rotulo_agregado)
        rho, p, _, _, n = estat.spearman(x, y)
        exigir(perto(rho, rho_esp) and perto(p, p_esp, 0.002),
               "%s/%s: rho %.3f e p %.3f" % (ramo, chave, rho_esp, p_esp),
               "rho=%.3f p=%.3f N=%d" % (rho, p, n))

    print("\n  correlacoes parciais, controlando n_metodos_teste:")
    for chave, r_esp in (("bruto", 0.058), ("distintos", 0.055)):
        linhas = c.ler_ramo("deterministico")
        x, y, tam = ex.pares(linhas, chave, ex.rotulo_agregado)
        r, p, n = estat.parcial(x, y, tam)
        exigir(perto(r, r_esp), "parcial de %s cai para %.3f" % (chave, r_esp),
               "%.3f (p=%.3f)" % (r, p))

    print("\n  o confundidor:")
    linhas = c.ler_ramo("deterministico")
    validos = [r for r in linhas if ex.rotulo_agregado(r) is not None
               and c.num(r["n_metodos_teste"]) is not None]
    rot = [ex.rotulo_agregado(r) for r in validos]
    for nome, col, esp in (("n_metodos_teste", "n_metodos_teste", 0.079),
                           ("loc_teste", "loc_teste", 0.091)):
        rho, p, _, _, n = estat.spearman(rot, [c.num(r[col]) for r in validos])
        exigir(perto(rho, esp), "code smell x %s: rho %.3f" % (nome, esp),
               "%.3f (p=%.3f)" % (rho, p))

    x, y, tam = ex.pares(linhas, "bruto", ex.rotulo_agregado)
    rho, _, _, _, _ = estat.spearman(x, tam)
    exigir(perto(rho, 0.554), "test smell bruto x tamanho: rho 0,554", "%.3f" % rho)


def conferir_caderno():
    """O caderno da secao 5 declara um total de testes; o CSV tem que conter todos eles."""
    print("\nCADERNO DE TENTATIVAS (secao 5)")
    print("-" * 31)
    caminho = os.path.join(c.DADOS, "exploracao.csv")
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


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    conferir_caracterizacao()
    conferir_primeira_rodada()
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
