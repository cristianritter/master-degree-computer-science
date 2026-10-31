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

# mesma funcao de remocao de comentarios/literais que a estrategia 3 usou: auditar com
# uma limpeza diferente da que gerou o par inventaria discordancia.
rp.carregar_step1()
sem_comentarios = c.sem_comentarios

RE_PACOTE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)
RE_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", re.M)
RE_TIPO = re.compile(r"^\s*(?:public\s+|final\s+|abstract\s+)*(?:class|interface|enum|record)\s+(\w+)", re.M)
RE_METODO_TESTE = re.compile(r"(?:@Test[^\n]*\n(?:\s*@[^\n]*\n)*\s*[\w<>\[\], ]+?\s+(\w+)\s*\(|\bpublic\s+void\s+(test\w*)\s*\()")

NL = chr(10)


def limpar_preservando_linhas(fonte):
    """Apaga comentarios e literais trocando-os por espaco, mantendo TODAS as quebras.

    O comum.sem_comentarios nao preserva a contagem de linhas (colapsa 17 linhas num
    arquivo de 346), entao o numero de linha do texto limpo nao serve para citar o arquivo
    original - e citar a linha errada num dossie de auditoria e pior que nao citar nada.
    Esta versao existe so para o dossie: quem decide se ha mencao continua sendo a funcao
    do comum.py, a mesma que gerou os pares.
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


FIM_INSTRUCAO = (";", "{", "}")
MAX_CONTEXTO = 14      # mesmas 14 mencoes que a listagem simples mostra
MAX_USOS = 8           # chamadas mostradas por variavel


def tipo_da_producao(prod, nome):
    """'interface (2 metodos default)', 'abstract class', 'enum'... do tipo com o nome do arquivo.

    Interface sem codigo e classe abstrata mudam a leitura do criterio amplo: o que roda e
    a implementacao. O dossie so informa; quem decide e o avaliador.
    """
    limpo = limpar_preservando_linhas(prod)
    m = re.search(r"((?:\b(?:public|protected|private|abstract|final|static|sealed)\s+)*)"
                  r"\b(class|interface|enum|record)\s+%s\b" % re.escape(nome), limpo)
    if not m:
        return "?"
    mods = m.group(1).split()
    tipo = " ".join([x for x in mods if x == "abstract"] + [m.group(2)])
    if m.group(2) == "interface":
        corpo = re.findall(r"\b(?:default|static)\s+[\w<>\[\], ?]+\s+(\w+)\s*\([^;]*?\)\s*"
                           r"(?:throws[^{;]*)?\{", limpo)
        tipo += " (metodos default/static com corpo: %s)" % (", ".join(sorted(set(corpo))) or "nenhum")
    return tipo


def instrucao(limpas, n):
    """Intervalo de linhas da instrucao que contem a linha n (uma chamada quebrada em varias
    linhas mostra so um pedaco na listagem simples; e o resto que diz o que acontece)."""
    ini = n
    while ini > 0 and n - ini < 6 and not limpas[ini - 1].rstrip().endswith(FIM_INSTRUCAO) \
            and limpas[ini - 1].strip():
        ini -= 1
    fim = n
    while fim + 1 < len(limpas) and fim - n < 6 and not limpas[fim].rstrip().endswith(FIM_INSTRUCAO):
        fim += 1
    return ini, fim


def imprimir_contexto(prod, nome, todas, limpas, hits):
    print("  tipo da producao: %s" % tipo_da_producao(prod, nome))
    if not hits:
        return
    vistos, textos = set(), []
    print("  instrucao completa de cada mencao:")
    for n in hits[:MAX_CONTEXTO]:
        ini, fim = instrucao(limpas, n)
        if (ini, fim) in vistos:
            continue
        vistos.add((ini, fim))
        texto = " ".join(todas[i].strip() for i in range(ini, fim + 1))
        textos.append(" ".join(limpas[i].strip() for i in range(ini, fim + 1)))
        faixa = "%d" % (ini + 1) if ini == fim else "%d-%d" % (ini + 1, fim + 1)
        print("   %9s| %s" % (faixa, texto[:240] + (" ..." if len(texto) > 240 else "")))

    # variaveis declaradas com o tipo, ou que recebem algo onde o nome aparece (inclusive
    # Foo.class passado a uma fabrica): o que o teste chama nelas e o que decide se roda
    nm = re.escape(nome)
    variaveis = []
    for t in textos:
        # ':' cobre a variavel do for-each: for (Foo f : lista)
        for v in re.findall(r"\b%s\b(?:\s*<[^;()]*?>)?(?:\s*\[\s*\])*\s+(\w+)\s*(?=[=;,):]|$)" % nm, t):
            variaveis.append(v)
        for v in re.findall(r"(\w+)\s*=(?!=)[^;]*\b%s\b" % nm, t):
            variaveis.append(v)
    imprimir_auxiliares(nome, todas, limpas)

    reservadas = {nome, "return", "new", "this", "super", "final", "class"}
    variaveis = [v for i, v in enumerate(variaveis) if v not in reservadas and v not in variaveis[:i]]
    if not variaveis:
        return
    # linhas onde o tipo aparece declarando a variavel nao sao uso dela
    declaracoes = {i for i in hits}
    print("  uso das variaveis ligadas a '%s':" % nome)
    for v in variaveis[:6]:
        ve = re.escape(v)
        chamada = re.compile(r"\b%s\s*\.\s*\w+\s*\(" % ve)
        # passada a um metodo ou construtor: o codigo da classe pode rodar do outro lado
        argumento = re.compile(r"\(\s*(?:[^;]*?,\s*)?%s\s*[,)]|,\s*%s\s*[,)]" % (ve, ve))
        chamadas = [i for i, l in enumerate(limpas) if chamada.search(l)]
        argumentos = [i for i, l in enumerate(limpas)
                      if i not in declaracoes and i not in chamadas and argumento.search(l)]
        if not chamadas and not argumentos:
            print("   %s: nenhuma chamada de metodo, nao e passada como argumento" % v)
            continue
        for rotulo, linhas in (("metodos chamados em %s" % v, chamadas),
                               ("%s passada como argumento" % v, argumentos)):
            if not linhas:
                continue
            print("   %s:" % rotulo)
            for i in linhas[:MAX_USOS]:
                print("   %9d| %s" % (i + 1, todas[i].strip()[:150]))
            if len(linhas) > MAX_USOS:
                print("   %9s  ... mais %d" % ("", len(linhas) - MAX_USOS))


def imprimir_auxiliares(nome, todas, limpas):
    """Corpo dos metodos do proprio teste que devolvem o tipo (createFoo(), newFoo()...):
    e ali que se ve se o objeto e real, mock ou outra implementacao."""
    decl = re.compile(r"^\s*(?:(?:public|protected|private|static|final|synchronized)\s+)*"
                      r"%s(?:\s*<[^>]*>)?\s+(\w+)\s*\([^;]*$" % re.escape(nome))
    achados = []
    for i, l in enumerate(limpas):
        m = decl.match(l)
        if not m:
            continue
        # corpo: do '{' ate as chaves fecharem, no maximo 12 linhas
        prof, fim, abriu = 0, i, False
        for j in range(i, min(i + 40, len(limpas))):
            prof += limpas[j].count("{") - limpas[j].count("}")
            abriu = abriu or "{" in limpas[j]
            fim = j
            if abriu and prof <= 0:
                break
        if abriu:
            achados.append((m.group(1), i, fim))
    if not achados:
        return
    print("  metodos do teste que devolvem '%s':" % nome)
    for metodo, ini, fim in achados[:4]:
        for j in range(ini, min(fim, ini + 11) + 1):
            if todas[j].strip():
                print("   %9d| %s" % (j + 1, todas[j].rstrip()[:150]))
        if fim > ini + 11:
            print("   %9s  ... mais %d linhas" % ("", fim - ini - 11))


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
    # para a auditoria humana: o estrato sugere a resposta, entao o avaliador nao o ve
    p.add_argument("--cego", action="store_true", help="omite o estrato do cabecalho")
    p.add_argument("--contexto", action="store_true",
                   help="acrescenta o tipo da producao, a instrucao completa de cada mencao "
                        "e o que o teste faz com as variaveis ligadas a classe")
    args = p.parse_args()
    if args.cego and args.estrato:
        sys.exit("--cego e --estrato juntos revelariam o estrato")
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
        if args.cego:
            print("PAR %03d  repo=%s" % (i, r["github_repo"]))
        else:
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
        n_limpo = len(pad.findall(sem_comentarios(teste)))
        aviso = "" if n_limpo else "  !! a funcao da estrategia 3 nao ve mencao alguma"
        print("  mencoes de '%s' no teste (fora de comentario/literal): %d linhas%s"
              % (nome_prod, len(hits), aviso))
        for n in hits[:14]:
            print("   %5d| %s" % (n + 1, todas[n].strip()[:150]))
        if len(hits) > 14:
            print("   ... mais %d linhas com mencao" % (len(hits) - 14))
        if args.contexto:
            imprimir_contexto(prod, nome_prod, todas, limpas, hits)
        print()


if __name__ == "__main__":
    main()
