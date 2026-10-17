# Análise 04 — Confirmados × só disputados

**Pergunta.** Entre os arquivos que **algum revisor sinalizou**, a densidade de test smell
prediz quais a maioria acabou confirmando?

**Resposta curta.** Inconclusiva por falta de poder — e isso é diferente da análise 01, que
deu nulo com poder suficiente para limitar o efeito.

```bash
python disputados.py --csv
```

---

## Por que esta comparação é diferente das outras

Ela é a única que **neutraliza a circularidade do desenho amostral do MLCQ**.

O problema está documentado no step 2, seção 3: revisores extras foram alocados apenas para
amostras que alguém já havia marcado como positiva. Por isso "alguém marcou > none" é quase
um detector de "esta amostra foi ao crosscheck", e o número de revisores é consequência do
rótulo, não evidência independente dele.

Os grupos, pelo conjunto dos smells do arquivo (`variaveis.grupo_arquivo`):

| grupo | definição | foi sinalizado? | foi ao crosscheck? |
|---|---|---|---|
| confirmado | algum smell com maioria > `none` | sim | sim |
| só disputado | algum smell sinalizado, nenhum confirmado | sim | sim |

Comparado com a análise 03:

| análise | grupo A | grupo B | mesmo roteamento? |
|---|---|---|---|
| 03 — extremos | confirmado | limpo | **não** — só o A foi ao crosscheck |
| **04 — esta** | confirmado | só disputado | **sim** — os dois foram sinalizados |

O roteamento é o mesmo nos dois grupos, então ele não pode explicar a diferença entre eles.
O que sobra é o **veredito do crosscheck** — exatamente o julgamento que o MLCQ coletou para
decidir os casos duvidosos, e que a regra `any > none` descarta.

---

## Resultado

### Ramo determinístico — 136 confirmados, 67 só disputados

| desfecho | mediana confirmados | mediana disputados | delta | p | p ajustado | delta detectável |
|---|---:|---:|---:|---:|---:|---:|
| bruto | 21,0 | 14,0 | 0,074 | 0,390 | 0,585 | 0,242 |
| densidade | 1,800 | 1,833 | 0,007 | 0,934 | 0,934 | 0,244 |
| distintos | 5,0 | 4,0 | 0,116 | 0,175 | 0,525 | 0,242 |

### Ramo ampliado — 267 confirmados, 117 só disputados

| desfecho | mediana confirmados | mediana disputados | delta | p | p ajustado | delta detectável |
|---|---:|---:|---:|---:|---:|---:|
| bruto | 32,0 | 27,0 | 0,077 | 0,229 | 0,493 | 0,180 |
| densidade | 1,456 | 1,600 | −0,037 | 0,562 | 0,562 | 0,181 |
| distintos | 5,0 | 5,0 | 0,062 | 0,329 | 0,493 | 0,180 |

---

## A leitura, e por que ela não é "mais um nulo"

**Os deltas observados estão todos abaixo do detectável.** No ramo determinístico, este N
só encontraria um efeito de delta ≥ 0,242 com 80% de poder; o maior observado é 0,116. O
teste não tinha como decidir.

Isso **não é evidência de ausência** — é ausência de evidência, que é coisa diferente e
precisa ser escrita diferente:

| análise | N | efeito detectável | efeito observado | leitura |
|---|---:|---|---|---|
| 01 — correlação | 730 | r ≥ 0,104 | r = 0,050 | nulo **informativo**: limita o efeito a < 0,12 |
| 03 — extremos, densidade | 136 vs 526 | delta ≥ 0,156 | delta = 0,074 | nulo fraco |
| **04 — esta** | 136 vs 67 | delta ≥ 0,24 | delta ≤ 0,12 | **inconclusiva** |

A ironia metodológica vale registrar no artigo: **a comparação com o melhor desenho é a que
tem o pior poder.** Isolar a circularidade custou condicionar a amostra aos arquivos
sinalizados, que são poucos — 203 dos 730.

## O que seria preciso para responder

**O gargalo agora são os 67 só disputados.** Mantendo os 136 confirmados e aumentando só o
outro grupo:

| só disputados | delta detectável |
|---:|---:|
| 67 (o que temos) | 0,242 |
| 200 | 0,180 |
| 500 | 0,157 |
| infinito | **0,139** (piso com 136 confirmados) |

Para delta de 0,15, mantendo a proporção observada, seriam precisos cerca de **408
confirmados e 201 só disputados** — três vezes o que temos.

Caminhos possíveis, nenhum barato:
- ampliar a cobertura do binding, que o step 2 já explorou até 37,5% e cujo custo de
  construto está medido;
- usar outro dataset de code smell com mais anotações por classe;
- aceitar a pergunta como não respondível com o MLCQ e declarar isso.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `disputados.py` | a análise |
| `dados/disputados.csv` | 6 resultados: 2 ramos × 3 desfechos, com delta, p, p ajustado e delta detectável |
