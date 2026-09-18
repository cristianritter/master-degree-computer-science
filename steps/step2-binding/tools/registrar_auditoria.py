"""Grava vereditos da auditoria automatica em dados/auditoria_binding_auto.csv.

Fica separado de auditoria_binding.csv de proposito: aquele arquivo e a planilha do
auditor humano, e misturar juizo automatico com juizo humano na mesma coluna apagaria a
distincao que o artigo precisa declarar. Os dois arquivos tem as mesmas 250 linhas na
mesma ordem, entao a concordancia entre eles e calculavel quando a humana existir.

A gravacao e incremental e idempotente: cada lote reescreve o arquivo inteiro a partir do
que ja estava nele mais o que chegou agora, entao interromper no meio custa o lote
corrente, nao a rodada.

Entrada (stdin), uma linha por par:
    <indice>|<s|n|?>|<observacao>

Uso:
    python registrar_auditoria.py < lote.txt
    python registrar_auditoria.py --status
"""
import argparse
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

ORIGEM = os.path.join(c.DADOS, "auditoria_binding.csv")
SAIDA = os.path.join(c.DADOS, "auditoria_binding_auto.csv")


def carregar():
    base = list(c.ler_csv(ORIGEM))
    if os.path.exists(SAIDA):
        ja = list(c.ler_csv(SAIDA))
        if len(ja) != len(base):
            sys.exit("auditoria_binding_auto.csv tem %d linhas e a origem tem %d" % (len(ja), len(base)))
        return ja
    for r in base:
        r["correto"] = ""
        r["observacao"] = ""
    return base


def gravar(linhas):
    cab = list(linhas[0].keys())
    tmp = SAIDA + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cab)
        w.writeheader()
        for r in linhas:
            w.writerow(r)
    os.replace(tmp, SAIDA)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--status", action="store_true")
    args = p.parse_args()

    linhas = carregar()
    if args.status:
        from collections import Counter
        ct = Counter((r["correto"] or "").strip() or "(vazio)" for r in linhas)
        for k in sorted(ct):
            print("%-8s %d" % (k, ct[k]))
        return

    n = 0
    for bruto in sys.stdin:
        bruto = bruto.strip()
        if not bruto or bruto.startswith("#"):
            continue
        partes = bruto.split("|", 2)
        if len(partes) < 2:
            sys.exit("linha mal formada: %s" % bruto)
        idx = int(partes[0])
        veredito = partes[1].strip()
        obs = partes[2].strip() if len(partes) > 2 else ""
        if veredito not in ("s", "n", "?"):
            sys.exit("veredito invalido em %d: %s" % (idx, veredito))
        if not (1 <= idx <= len(linhas)):
            sys.exit("indice fora da faixa: %d" % idx)
        linhas[idx - 1]["correto"] = veredito
        linhas[idx - 1]["observacao"] = obs
        n += 1

    gravar(linhas)
    preenchidas = sum(1 for r in linhas if (r["correto"] or "").strip())
    print("gravados %d vereditos; %d/%d preenchidos" % (n, preenchidas, len(linhas)))


if __name__ == "__main__":
    main()
