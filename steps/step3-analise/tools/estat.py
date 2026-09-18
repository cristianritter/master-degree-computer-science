"""Correlacao de Spearman, intervalo e valor-p, sem dependencia externa.

Spearman e nao-parametrica: correlaciona POSTOS, nao valores. E o que a caracterizacao
exige - com 72% de zeros e assimetria de ate 21, media e desvio-padrao nao descrevem os
dados, e um unico arquivo com 1.116 ocorrencias de Lazy Test dominaria uma correlacao de
Pearson.

Empates recebem posto medio (metodo padrao), que e essencial aqui: as colunas tem centenas
de zeros, todos empatados entre si.

O valor-p e o intervalo saem da transformacao z de Fisher com aproximacao normal. Para os
N deste step (730 e 1.369) a diferenca para a distribuicao t exata e desprezivel; com N
abaixo de ~30 a aproximacao pioraria, e o codigo avisa.

Nada aqui interpreta resultado. Interpretar e trabalho do README.
"""
import math


def postos(valores):
    """Postos com empate recebendo a media das posicoes que ocupariam."""
    indexado = sorted(range(len(valores)), key=lambda i: valores[i])
    r = [0.0] * len(valores)
    i = 0
    while i < len(indexado):
        j = i
        while j + 1 < len(indexado) and valores[indexado[j + 1]] == valores[indexado[i]]:
            j += 1
        medio = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[indexado[k]] = medio
        i = j + 1
    return r


def pearson(x, y):
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0 or dy == 0:
        return float("nan")
    return num / (dx * dy)


def normal_acum(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def spearman(x, y):
    """Devolve (rho, p bicaudal, ic_baixo, ic_alto, n). NaN se nao houver variacao."""
    assert len(x) == len(y)
    n = len(x)
    if n < 10:
        return float("nan"), float("nan"), float("nan"), float("nan"), n
    rho = pearson(postos(x), postos(y))
    if math.isnan(rho):
        return rho, float("nan"), float("nan"), float("nan"), n
    # z de Fisher
    rho_lim = max(min(rho, 0.999999), -0.999999)
    z = math.atanh(rho_lim)
    ep = 1.0 / math.sqrt(n - 3)
    p = 2 * (1 - normal_acum(abs(z) / ep))
    return rho, p, math.tanh(z - 1.96 * ep), math.tanh(z + 1.96 * ep), n


def formatar_p(p):
    if math.isnan(p):
        return "    -"
    if p < 0.001:
        return "<0.001"
    return "%.3f" % p


def parcial(x, y, z_ctrl):
    """Spearman parcial: correlacao entre x e y removendo o efeito de z_ctrl.

    Calculada sobre postos, pela formula da correlacao parcial de primeira ordem. Serve
    para a pergunta "sobra relacao depois de descontar o tamanho do teste?".
    """
    rx = postos(x)
    ry = postos(y)
    rz = postos(z_ctrl)
    rxy = pearson(rx, ry)
    rxz = pearson(rx, rz)
    ryz = pearson(ry, rz)
    den = math.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    if den == 0 or math.isnan(den):
        return float("nan"), float("nan"), len(x)
    r = (rxy - rxz * ryz) / den
    n = len(x)
    # um grau de liberdade a menos por variavel controlada
    r_lim = max(min(r, 0.999999), -0.999999)
    z = math.atanh(r_lim)
    ep = 1.0 / math.sqrt(n - 4)
    p = 2 * (1 - normal_acum(abs(z) / ep))
    return r, p, n


def mannwhitney(a, b):
    """Mann-Whitney U bicaudal, com correcao para empates.

    Compara duas amostras independentes sem supor distribuicao - e o teste que cabe quando
    a pergunta e "o grupo positivo tem mais test smell que o negativo?" e os dados tem
    72% de zeros.

    Devolve (U, p, delta, n1, n2), onde delta e o r bisserial de postos: a probabilidade
    de um elemento de 'a' superar um de 'b' menos a probabilidade do contrario. Varia de
    -1 a 1 e independe do tamanho das amostras, ao contrario do U.
    """
    n1, n2 = len(a), len(b)
    if n1 < 5 or n2 < 5:
        return float("nan"), float("nan"), float("nan"), n1, n2
    juntos = list(a) + list(b)
    r = postos(juntos)
    soma1 = sum(r[:n1])
    u1 = soma1 - n1 * (n1 + 1) / 2.0
    u2 = n1 * n2 - u1

    # correcao de empates na variancia: com centenas de zeros ela nao e opcional
    contagem = {}
    for v in juntos:
        contagem[v] = contagem.get(v, 0) + 1
    n = n1 + n2
    correcao = sum(t ** 3 - t for t in contagem.values())
    var = n1 * n2 / 12.0 * ((n + 1) - correcao / float(n * (n - 1)))
    if var <= 0:
        return u1, float("nan"), float("nan"), n1, n2
    media_u = n1 * n2 / 2.0
    z = (min(u1, u2) - media_u) / math.sqrt(var)
    p = 2 * normal_acum(-abs(z))
    delta = (u1 - u2) / float(n1 * n2)     # r bisserial de postos
    return u1, p, delta, n1, n2


def benjamini_hochberg(ps):
    """Valores-p ajustados por FDR (Benjamini-Hochberg).

    Com dezenas de testes, alfa 0,05 por teste deixa de significar 5% de falsos positivos
    no conjunto. BH controla a FRACAO ESPERADA de falsos positivos entre os que forem
    declarados significativos - e menos conservador que Bonferroni, que e o adequado para
    exploracao onde perder um achado real custa caro.

    Recebe a lista de p na ordem original e devolve os ajustados na mesma ordem.
    """
    indexado = sorted(range(len(ps)), key=lambda i: ps[i])
    m = len(ps)
    ajustados = [0.0] * m
    anterior = 1.0
    for posicao in range(m - 1, -1, -1):
        i = indexado[posicao]
        valor = min(anterior, ps[i] * m / (posicao + 1))
        ajustados[i] = valor
        anterior = valor
    return ajustados
