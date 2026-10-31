"""Confere que todo numero escrito na documentacao sai de algum comando versionado.

Os conferidores de cada step (conferir_dados.py, conferir_resultados.py) checam os numeros
que alguem colocou neles. Este aqui checa o contrario: procura numeros nos documentos que
NENHUM comando produz. Sao eles que podem ter sido digitados a mao, e numero digitado a
mao nao e reproduzivel.

Como funciona:
  1. roda os comandos de reproducao rapidos e sem efeito colateral (COMANDOS) e junta a
     saida deles com os CSVs de resultado das analises e os .params.txt;
  2. extrai os numeros dos documentos (DOCUMENTOS), em formato brasileiro (1.611; 0,050;
     37,5%) ou ingles;
  3. um numero do documento tem origem se algum numero das saidas, arredondado ao mesmo
     numero de casas, e igual a ele (ou igual a ele em porcentagem);
  4. os sem origem sao listados, com arquivo e linha.

Numeros que nao sao dado (anos, versoes, numeros de secao, parametros de linha de comando)
ficam em cobertura_ignorar.txt, um por linha, com o motivo. A lista e curta de proposito:
cada entrada e uma afirmacao de que aquele numero nao precisa de origem.

A checagem e de cobertura, nao de corretude: um numero pode casar por coincidencia com
outro de mesmo valor. Corretude e trabalho dos conferidores de cada step.

Uso:
    python conferir_cobertura.py            # lista os numeros sem origem; codigo 1 se houver
    python conferir_cobertura.py --resumo   # so a contagem por documento
"""
import argparse
import collections
import glob
import html
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = os.path.join(RAIZ, "steps")
S1 = os.path.join(STEPS, "step1-coleta-jnose")
S2 = os.path.join(STEPS, "step2-binding")
S3 = os.path.join(STEPS, "step3-analise")
A3 = os.path.join(S3, "analises")

# (pasta, argumentos). So comandos que leem e imprimem: nenhum deles grava arquivo.
COMANDOS = [
    (S1, ["tools/conferir_coleta.py"]),
    (S2, ["tools/conferir_dados.py"]),
    (S2, ["tools/poder_analise.py"]),
    (S2, ["tools/auditar_binding.py", "--apurar", "--arquivo", "dados/auditoria_binding_auto.csv"]),
    (S2, ["tools/auditar_binding.py", "--apurar", "--arquivo", "dados/auditoria_binding_auto.csv",
          "--criterio", "amplo"]),
    (S2, ["tools/auditoria_humana.py", "--apurar"]),
    (os.path.join(A3, "00-caracterizacao"), ["caracterizar.py"]),
    (os.path.join(A3, "01-correlacao-agregada"), ["explorar.py", "--por-smell"]),
    (os.path.join(A3, "02-por-test-smell"), ["por_test_smell.py"]),
    (os.path.join(A3, "03-extremos"), ["extremos.py"]),
    (os.path.join(A3, "04-disputados"), ["disputados.py"]),
    (os.path.join(A3, "05-code-x-test-smell"), ["cruzado.py"]),
    (os.path.join(A3, "06-robustez"), ["robustez.py"]),
    (S3, ["tools/conferir_resultados.py"]),
    (S3, ["tools/validar_estat.py"]),
    (os.path.join(RAIZ, "artigo"), ["tools/folha_de_fatos.py"]),
]

DOCUMENTOS = [
    os.path.join(S1, "README.md"),
    os.path.join(S2, "README.md"),
    os.path.join(S2, "NOTAS-METODOLOGICAS.md"),
    os.path.join(S2, "PROTOCOLO-AUDITORIA-HUMANA.md"),
    os.path.join(S3, "README.md"),
] + sorted(glob.glob(os.path.join(A3, "*", "README.md"))) + sorted(
    glob.glob(os.path.join(RAIZ, "artigo", "*.md"))) + [
    os.path.join(RAIZ, "artigo", "relatorio-orientador.html"),
]

LIMITE_CSV = 2 * 1024 * 1024

# numero no documento: 1.611 | 2.059.905 | 0,050 | 37,5 | 1,05 | 730 | −0,022
RE_DOC = re.compile(r"(?<![\w.,/])[−-]?\d{1,3}(?:\.\d{3})+(?:,\d+)?(?![\w.]*\d)"
                    r"|(?<![\w.,/])[−-]?\d+,\d+(?![\w,]*\d)"
                    r"|(?<![\w.,/])[−-]?\d+(?![\w.,/]*\d)")
RE_SAIDA = re.compile(r"-?\d+(?:\.\d+)?")


def rodar_comandos():
    textos = []
    for pasta, argv in COMANDOS:
        r = subprocess.run([sys.executable] + argv, cwd=pasta, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("AVISO: %s %s terminou com codigo %d" % (os.path.relpath(pasta, RAIZ),
                                                          " ".join(argv), r.returncode))
        textos.append(r.stdout)
    return textos


def ler_artefatos():
    textos = []
    # So artefatos de RESULTADO: os CSVs das analises e os .params.txt. Os CSVs de dado
    # bruto (amostras, classes, pares) tem milhares de valores, e qualquer numero do texto
    # casaria com algum por coincidencia - a checagem perderia o sentido.
    for padrao in ("*/dados/*.params.txt", "*/analises/*/dados/*.csv"):
        for p in glob.glob(os.path.join(STEPS, padrao)):
            if os.path.getsize(p) <= LIMITE_CSV:
                texto = open(p, encoding="utf-8-sig", errors="replace").read()
                textos.append(texto)
                if p.endswith(".csv"):
                    # o numero de linhas de dado do CSV tambem e uma saida (o README cita)
                    textos.append(str(max(0, len(texto.splitlines()) - 1)))
    return textos


def valores_das_saidas(textos):
    vals = set()
    for t in textos:
        for m in RE_SAIDA.findall(t):
            try:
                vals.add(float(m))
            except ValueError:
                pass
    return vals


def normalizar(token):
    """'1.611' -> (1611, 0); '0,050' -> (0.05, 3); '−0,022' -> (-0.022, 3)."""
    t = token.replace("−", "-")
    if "," in t:
        inteiro, dec = t.split(",")
        return float(inteiro.replace(".", "") + "." + dec), len(dec)
    return float(t.replace(".", "")), 0


def tem_origem(v, casas, saida, por_casas):
    if casas == 0:
        return v in saida or abs(v) in saida
    alvo = round(abs(v), casas)
    return alvo in por_casas[casas] or alvo in por_casas["pct%d" % casas]


def indexar(saida):
    por_casas = collections.defaultdict(set)
    for x in saida:
        for k in range(1, 5):
            por_casas[k].add(round(abs(x), k))
            por_casas["pct%d" % k].add(round(abs(x) * 100, k))
    return por_casas


def ler_ignorar():
    caminho = os.path.join(STEPS, "cobertura_ignorar.txt")
    regras = []
    if os.path.exists(caminho):
        for linha in open(caminho, encoding="utf-8"):
            linha = linha.split("#", 1)[0].strip()
            if linha:
                doc, _, num = linha.partition(":")
                regras.append((doc.strip(), num.strip()))
    return regras


def ignorado(doc_rel, token, regras):
    nome = os.path.basename(doc_rel)
    for doc, num in regras:
        if num == token and (doc == "*" or doc == nome or doc == doc_rel):
            return True
    return False


def linhas_do_documento(caminho):
    texto = open(caminho, encoding="utf-8").read()
    if caminho.endswith(".html"):
        texto = texto[texto.index('<div class="wrap">'):]
        texto = html.unescape(re.sub(r"<[^>]+>", "", texto))
    return texto.splitlines()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumo", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    saida = valores_das_saidas(rodar_comandos() + ler_artefatos())
    por_casas = indexar(saida)
    regras = ler_ignorar()

    sem = collections.defaultdict(list)
    total = 0
    for caminho in DOCUMENTOS:
        rel = os.path.relpath(caminho, RAIZ).replace(os.sep, "/")
        for n, linha in enumerate(linhas_do_documento(caminho), 1):
            for m in RE_DOC.finditer(linha):
                token = m.group(0)
                v, casas = normalizar(token)
                if casas == 0 and abs(v) < 10:
                    continue        # contagens pequenas: ruido demais para conferir
                total += 1
                if ignorado(rel, token.replace("−", "-"), regras):
                    continue
                if not tem_origem(v, casas, saida, por_casas):
                    sem[rel].append((n, token, linha.strip()[:110]))

    n_sem = sum(len(v) for v in sem.values())
    print("numeros nos documentos: %d   sem origem em nenhum comando: %d" % (total, n_sem))
    for rel in sorted(sem):
        print("\n%s  (%d)" % (rel, len(sem[rel])))
        if not args.resumo:
            for n, token, ctx in sem[rel]:
                print("  %5d  %-10s %s" % (n, token, ctx))
    sys.exit(1 if n_sem else 0)


if __name__ == "__main__":
    main()
