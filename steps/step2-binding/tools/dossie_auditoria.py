"""Monta, para cada par sorteado, o dossie minimo para decidir se o teste exercita a classe.

Julgar 250 pares abrindo dois arquivos inteiros e inviavel - alguns tem milhares de linhas.
O que decide a questao e sempre a mesma coisa: em que linhas do teste o tipo de producao
aparece, e o que essas linhas fazem com ele. Este script extrai exatamente isso, junto com
os sinais que distinguem teste dedicado de referencia incidental (quantos outros tipos o
teste importa, se o nome do teste remete ao da producao).

O dossie e evidencia, nao veredito: nao ha heuristica de decisao aqui. Se houvesse, a
auditoria seria uma heuristica conferindo outra, que e circular e nao mede nada.

Uso:
    python dossie_auditoria.py                 # todos os pares, para stdout
    python dossie_auditoria.py --de 1 --ate 25
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c
import baixar_auditoria as b
import refs_producao as rp

# mesma funcao de remocao de comentarios/literais que a estrategia 3 usou, carregada do
# step 1: auditar com uma limpeza diferente da que gerou o par inventaria discordancia.
rp.carregar_step1()
sem_comentarios = rp.jb._sem_comentarios

RE_PACOTE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)
RE_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", re.M)
RE_TIPO = re.compile(r"^\s*(?:public\s+|final\s+|abstract\s+)*(?:class|interface|enum|record)\s+(\w+)", re.M)
RE_METODO_TESTE = re.compile(r"(?:@Test[^\n]*\n(?:\s*@[^\n]*\n)*\s*[\w<>\[\], ]+?\s+(\w+)\s*\(|\bpublic\s+void\s+(test\w*)\s*\()")

NL = chr(10)


def limpar_preservando_linhas(fonte):
    """Apaga comentarios e literais trocando-os por espaco, mantendo TODAS as quebras.

    O _sem_comentarios do step 1 nao preserva a contagem de linhas (colapsa 17 linhas num
    arquivo de 346), entao o numero de linha do texto limpo nao serve para citar o arquivo
    original - e citar a linha errada num dossie de auditoria e pior que nao citar nada.
    Esta versao existe so para o dossie: quem decide se ha mencao continua sendo a funcao
    do step 1, a mesma que gerou os pares.
    """
    saida = []
    i, n = 0, len(fonte)
    estado = None  # None, "//", "/*", ou o caractere de aspas aberto
    aspas = ('"', "'")
    while i < n:
        ch = fonte[i]
        prox = fonte[i + 1] if i + 1 < n else ""
        if estado is None:
            if ch == "/" and prox == "/":
                estado, i = "//", i + 2
                saida.append("  ")
                continue
            if ch == "/" and prox == "*":
                estado, i = "/*", i + 2
                saida.append("  ")
                continue
            if ch in aspas:
                estado, i = ch, i + 1
                saida.append(" ")
                continue
            saida.append(ch)
            i += 1
            continue
        if estado == "//":
            if ch == NL:
                estado = None
                saida.append(NL)
            else:
                saida.append(" ")
            i += 1
            continue
        if estado == "/*":
            if ch == "*" and prox == "/":
                estado, i = None, i + 2
                saida.append("  ")
                continue
            saida.append(NL if ch == NL else " ")
            i += 1
            continue
        # dentro de literal de string ou char
        if ch == chr(92):  # barra invertida: pula o escapado
            saida.append("  ")
            i += 2
            continue
        if ch == estado:
            estado = None
        saida.append(NL if ch == NL else " ")
        i += 1
    return "".join(saida)


def ler(url):
    caminho = b.caminho_cache(url)
    if not os.path.exists(caminho):
        return None
    with open(caminho, "rb") as f:
        return f.read().decode("utf-8", errors="replace")


def main():
    # O console do Windows usa cp1252: uma seta ou um acento no fonte Java derrubava a
    # impressao com UnicodeEncodeError no meio do lote, perdendo os pares seguintes.
    # Mesmo problema de pagina de codigo que o step 1 enfrentou no repositorio atlas.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    p = argparse.ArgumentParser()
    p.add_argument("--de", type=int, default=1)
    p.add_argument("--ate", type=int, default=10 ** 9)
    p.add_argument("--indices", help="lista separada por virgula, no lugar de --de/--ate")
    p.add_argument("--estrato", help="so os pares deste estrato de auditoria")
    args = p.parse_args()
    escolhidos = set(int(x) for x in args.indices.split(",")) if args.indices else None

    linhas = list(c.ler_csv(os.path.join(c.DADOS, "auditoria_binding.csv")))
    for i, r in enumerate(linhas, 1):
        if escolhidos is not None:
            if i not in escolhidos:
                continue
        elif i < args.de or i > args.ate:
            continue
        if args.estrato and r["estrato_auditoria"] != args.estrato:
            continue
        prod, teste = ler(r["url_producao"]), ler(r["url_teste"])
        nome_prod = os.path.basename(r["production_path"])[:-5]

        print("=" * 78)
        print("PAR %03d  [%s]  repo=%s" % (i, r["estrato_auditoria"], r["github_repo"]))
        print("  producao: %s" % r["production_path"])
        print("  teste   : %s" % r["test_path"])
        if prod is None or teste is None:
            print("  !! arquivo ausente no cache")
            print()
            continue

        pac_p = RE_PACOTE.search(prod)
        pac_t = RE_PACOTE.search(teste)
        tipos_p = RE_TIPO.findall(prod)
        print("  package producao=%s  teste=%s  | tipos na producao: %s"
              % (pac_p.group(1) if pac_p else "?", pac_t.group(1) if pac_t else "?",
                 ", ".join(tipos_p[:6]) or "?"))

        imports = RE_IMPORT.findall(teste)
        metodos = [m[0] or m[1] for m in RE_METODO_TESTE.findall(teste)]
        amostra = ""
        if metodos:
            amostra = " (" + ", ".join(metodos[:8]) + ("..." if len(metodos) > 8 else "") + ")"
        print("  teste: %d linhas, %d imports, %d metodos de teste%s"
              % (teste.count(NL) + 1, len(imports), len(metodos), amostra))

        alvo = [im for im in imports if im.split(".")[-1] == nome_prod or im.endswith(".*")]
        print("  imports relevantes: %s" % (", ".join(alvo[:6]) or "(nenhum)"))

        pad = re.compile(r"\b%s\b" % re.escape(nome_prod))
        todas = teste.split(NL)
        limpas = limpar_preservando_linhas(teste).split(NL)
        hits = [n for n, l in enumerate(limpas) if pad.search(l)]
        n_step1 = len(pad.findall(sem_comentarios(teste)))
        aviso = "" if n_step1 else "  !! a funcao do step 1 nao ve mencao alguma"
        print("  mencoes de '%s' no teste (fora de comentario/literal): %d linhas%s"
              % (nome_prod, len(hits), aviso))
        for n in hits[:14]:
            print("   %5d| %s" % (n + 1, todas[n].strip()[:150]))
        if len(hits) > 14:
            print("   ... mais %d linhas com mencao" % (len(hits) - 14))
        print()


if __name__ == "__main__":
    main()
