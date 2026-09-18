"""As definicoes de variavel que todas as analises compartilham.

Mora em tools/ e nao dentro de uma analise porque e vocabulario, nao metodo: se cada
analise definisse "densidade de test smell" do seu jeito, os resultados delas nao seriam
comparaveis entre si - e o ponto do step 3 e justamente comparar operacionalizacoes.

Qualquer mudanca aqui muda TODAS as analises. E de proposito: e o que garante que
"densidade" significa a mesma coisa na secao 4 e na secao 5 do README.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comum as c


def desfechos(linha):
    """As tres definicoes de 'quanto test smell tem o teste desta classe'.

    bruto       soma das ocorrencias                 sensivel ao tamanho do teste
    densidade   soma / numero de metodos de teste    normalizado por tamanho
    distintos   quantos dos 13 smells aparecem       pouco sensivel a tamanho

    As tres existem porque a rodada 1 mostrou que a escolha entre elas muda o resultado:
    as sensiveis a tamanho dao significancia, a normalizada nao.
    """
    total = c.num(linha["ts_n_total"])
    metodos = c.num(linha["n_metodos_teste"])
    distintos = c.num(linha["ts_n_distintos"])
    if total is None or distintos is None:
        return None
    return {
        "bruto": total,
        "densidade": total / metodos if metodos else None,
        "distintos": distintos,
    }


def rotulo_agregado(linha):
    """Severidade do smell avaliado no arquivo, qualquer que seja ele.

    O MLCQ anota cada amostra para UM smell, e 715 dos 730 arquivos do ramo
    deterministico tem exatamente um avaliado - agregar assim recupera o N inteiro sem
    misturar avaliacoes de smells diferentes (step 2, secao 12.3).
    """
    v = [c.num(linha[c.coluna_cs(sm, "sev_media")]) for sm in c.CODE_SMELLS]
    v = [x for x in v if x is not None]
    return max(v) if v else None


def pares(linhas, chave_desfecho, rotulo):
    """Series alinhadas (desfecho, rotulo, tamanho), descartando linha incompleta.

    Descarta a linha inteira quando qualquer uma das tres falta, para que os N das tres
    series sejam sempre comparaveis entre si.
    """
    x, y, tam = [], [], []
    for r in linhas:
        d = desfechos(r)
        lab = rotulo(r)
        met = c.num(r["n_metodos_teste"])
        if d is None or lab is None or d[chave_desfecho] is None or met is None:
            continue
        x.append(d[chave_desfecho])
        y.append(lab)
        tam.append(met)
    return x, y, tam


def estrato_unico(linha):
    """O estrato do arquivo, so quando ele e inequivoco.

    Um arquivo pode reunir amostras de mais de um estrato; esses ficam de fora das
    comparacoes entre grupos, porque classifica-los exigiria uma regra de desempate que
    seria mais uma decisao escondida no codigo.
    """
    estratos = {e for e in (linha["estratos"] or "").split("|") if e}
    if len(estratos) != 1:
        return None
    return estratos.pop()
