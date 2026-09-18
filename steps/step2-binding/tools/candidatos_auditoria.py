"""Para cada par sorteado, lista os OUTROS arquivos do repositorio com o mesmo basename.

E a evidencia que faltava para auditar os estratos deterministicos. A pergunta deles nao e
"o teste exercita a classe?" e sim "a regra casou o arquivo certo entre os candidatos?" -
e para responder e preciso ver os candidatos que a regra NAO escolheu.

Exemplo do porque: em aspectj, LangUtilTest esta em org.aspectj.testing.util e nao importa
nada; se existir um LangUtil naquele pacote, e ele que o teste exercita, e o par com
org.aspectj.util.LangUtil e falso. Sem a arvore do repositorio nao da para saber.

A arvore vem da API do GitHub, uma chamada por repositorio, no commit da coleta, e fica em
cache local (.cache-auditoria/arvores/). Repositorio grande tem arvore truncada pela API -
o script avisa quando isso acontece em vez de responder errado em silencio.

Uso:
    python candidatos_auditoria.py --indices 229,88,68
    python candidatos_auditoria.py --estrato convencao/so_basename
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c
import baixar_auditoria as b

CACHE = os.path.join(b.CACHE, "arvores")


def arvore(repo, commit):
    """Lista de caminhos do repositorio no commit, com cache em disco."""
    os.makedirs(CACHE, exist_ok=True)
    destino = os.path.join(CACHE, "%s__%s.json" % (repo, commit[:12]))
    if os.path.exists(destino):
        with open(destino, "r", encoding="utf-8") as f:
            return json.load(f)
    url = ("https://api.github.com/repos/cristianritter/%s/git/trees/%s?recursive=1"
           % (repo, commit))
    req = urllib.request.Request(url, headers={"User-Agent": "auditoria-binding",
                                               "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            dados = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"erro": "HTTP %s" % e.code}
    saida = {
        "truncada": bool(dados.get("truncated")),
        "paths": [x["path"] for x in dados.get("tree", []) if x.get("type") == "blob"
                  and x["path"].endswith(".java")],
    }
    tmp = destino + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(saida, f)
    os.replace(tmp, destino)
    return saida


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--indices")
    p.add_argument("--estrato")
    args = p.parse_args()
    escolhidos = set(int(x) for x in args.indices.split(",")) if args.indices else None

    linhas = list(c.ler_csv(os.path.join(c.DADOS, "auditoria_binding.csv")))
    for i, r in enumerate(linhas, 1):
        if escolhidos is not None and i not in escolhidos:
            continue
        if args.estrato and r["estrato_auditoria"] != args.estrato:
            continue
        commit = r["url_producao"].split("/blob/")[1].split("/")[0]
        arv = arvore(r["github_repo"], commit)
        base_prod = os.path.basename(r["production_path"])
        base_teste = os.path.basename(r["test_path"])
        print("PAR %03d  %s" % (i, r["github_repo"]))
        if "erro" in arv:
            print("   !! arvore indisponivel: %s" % arv["erro"])
            print()
            continue
        if arv["truncada"]:
            print("   !! arvore TRUNCADA pela API - a lista abaixo pode estar incompleta")
        homonimos = [x for x in arv["paths"] if os.path.basename(x) == base_prod]
        testes = [x for x in arv["paths"] if os.path.basename(x) == base_teste]
        print("   producao  %s" % r["production_path"])
        print("   homonimos de %s: %d" % (base_prod, len(homonimos)))
        for x in homonimos:
            marca = "  <== o par" if "/" + x == r["production_path"] else ""
            print("      %s%s" % (x, marca))
        print("   teste     %s" % r["test_path"])
        print("   homonimos de %s: %d" % (base_teste, len(testes)))
        for x in testes:
            marca = "  <== o par" if "/" + x == r["test_path"] else ""
            print("      %s%s" % (x, marca))
        print()


if __name__ == "__main__":
    main()
