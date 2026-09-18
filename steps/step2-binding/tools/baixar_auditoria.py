"""Baixa os dois arquivos de cada par sorteado para auditoria, em cache local.

A auditoria precisa ler o codigo dos dois lados de cada par. Baixar uma vez e conferir
depois torna a conferencia retomavel: uma interrupcao custa o que faltava baixar, nao a
rodada inteira. O cache fica fora do git (.cache-auditoria/), e o download e idempotente -
arquivo ja em disco com tamanho > 0 e pulado.

As URLs vem do proprio auditoria_binding.csv, que ja aponta para o commit da coleta, entao
o conteudo baixado e exatamente o que o JNose analisou no step 1.

Uso:
    python baixar_auditoria.py
    python baixar_auditoria.py --arquivo dados/auditoria_binding.csv --threads 8
"""
import argparse
import concurrent.futures as cf
import hashlib
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c

CACHE = os.path.join(os.path.dirname(c.DADOS), ".cache-auditoria")


def caminho_cache(url):
    # o nome do arquivo em disco e o hash da url; o mapa url->arquivo e reconstruivel
    # a qualquer momento por esta funcao, entao nao precisa de indice em disco.
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    base = url.rsplit("/", 1)[-1]
    return os.path.join(CACHE, "%s__%s" % (h, base))


def raw(url):
    # .../blob/<commit>/<path> -> raw.githubusercontent.com/<repo>/<commit>/<path>
    u = url.replace("https://github.com/", "https://raw.githubusercontent.com/", 1).replace("/blob/", "/", 1)
    # ha caminho com espaco no MLCQ (eclipse.platform.swt tem um diretorio "JUnit Tests");
    # sem escapar, urllib recusa a url inteira com InvalidURL.
    esquema, resto = u.split("://", 1)
    return esquema + "://" + urllib.parse.quote(resto, safe="/:@")


def baixar(url):
    destino = caminho_cache(url)
    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        return "cache", url
    req = urllib.request.Request(raw(url), headers={"User-Agent": "auditoria-binding"})
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                dados = r.read()
            # grava em temporario e renomeia: um arquivo no cache esta sempre completo,
            # mesmo se a energia cair no meio do download.
            tmp = destino + ".tmp"
            with open(tmp, "wb") as f:
                f.write(dados)
            os.replace(tmp, destino)
            return "ok", url
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "404", url
            if tentativa == 2:
                return "erro:%s" % e.code, url
        except Exception as e:
            if tentativa == 2:
                return "erro:%s" % type(e).__name__, url
    return "erro", url


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arquivo", default=os.path.join(c.DADOS, "auditoria_binding.csv"))
    p.add_argument("--threads", type=int, default=8)
    args = p.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    urls = []
    for r in c.ler_csv(args.arquivo):
        urls.append(r["url_producao"])
        urls.append(r["url_teste"])
    urls = sorted(set(urls))
    print("%d urls distintas (%d pares)" % (len(urls), len(urls) // 2))

    contagem = {}
    with cf.ThreadPoolExecutor(max_workers=args.threads) as ex:
        for i, (status, url) in enumerate(ex.map(baixar, urls), 1):
            contagem[status] = contagem.get(status, 0) + 1
            if i % 50 == 0:
                print("  %d/%d" % (i, len(urls)))
            if status.startswith("erro") or status == "404":
                print("  %s  %s" % (status, url))
    for k in sorted(contagem):
        print("%-12s %d" % (k, contagem[k]))


if __name__ == "__main__":
    main()
