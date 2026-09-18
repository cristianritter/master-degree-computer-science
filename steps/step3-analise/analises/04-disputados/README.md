# Análise 04 — Confirmados × disputados

**Pergunta.** Entre as amostras que **algum revisor sinalizou**, a densidade de test smell
prediz quais delas a maioria acabou confirmando?

**Resposta curta.** Inconclusiva por falta de poder — e isso é diferente das análises 01 a
03, que deram nulo com poder suficiente para limitar o efeito.

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

Nas análises anteriores, os grupos comparados passaram por funis diferentes:

| análise | grupo A | grupo B | mesmo roteamento? |
|---|---|---|---|
| 03 — extremos | `positivo_confiavel` | `negativo_confiavel` | **não** — só o A foi ao crosscheck |
| **04 — esta** | `positivo_confiavel` | `disputado` | **sim** — os dois foram sinalizados |

Os dois grupos daqui foram sinalizados por pelo menos um revisor, e os dois foram ao
crosscheck. O roteamento é o mesmo, então ele não pode explicar a diferença entre eles. O
que sobra é o **veredito do crosscheck** — exatamente o julgamento que o MLCQ coletou para
decidir os casos duvidosos, e que a regra `any > none` descarta.

É a comparação menos circular que este dataset permite. Se existisse relação entre
qualidade do teste e code smell, aqui ela teria a melhor chance de aparecer limpa.

---

## Resultado

### Ramo determinístico — 42 confirmados, 155 disputados

| desfecho | mediana confirmados | mediana disputados | delta | p | p ajustado | delta detectável |
|---|---:|---:|---:|---:|---:|---:|
| bruto | 18,0 | 18,0 | 0,013 | 0,896 | 0,896 | 0,282 |
| densidade | 1,552 | 1,865 | −0,039 | 0,699 | 0,896 | 0,285 |
| distintos | 5,0 | 4,0 | 0,076 | 0,445 | 0,896 | 0,282 |

### Ramo ampliado — 76 confirmados, 293 disputados

| desfecho | mediana confirmados | mediana disputados | delta | p | p ajustado | delta detectável |
|---|---:|---:|---:|---:|---:|---:|
| bruto | 46,0 | 28,0 | 0,102 | 0,169 | 0,508 | 0,208 |
| densidade | 1,506 | 1,412 | 0,041 | 0,582 | 0,582 | 0,210 |
| distintos | 5,0 | 5,0 | 0,063 | 0,391 | 0,582 | 0,208 |

---

## A leitura, e por que ela não é "mais um nulo"

**Os deltas observados estão todos abaixo do detectável.** No ramo determinístico, este N
só encontraria um efeito de delta ≥ 0,282 com 80% de poder; o maior observado é 0,076. O
teste não tinha como decidir.

Isso **não é evidência de ausência** — é ausência de evidência, que é coisa diferente e
precisa ser escrita diferente. Comparar com as análises anteriores deixa claro:

| análise | N | efeito detectável | efeito observado | leitura |
|---|---:|---|---|---|
| 01 — correlação | 730 | r ≥ 0,104 | r = 0,047 | nulo **informativo**: limita o efeito a < 0,12 |
| 03 — extremos | 42 vs 523 | delta ≥ 0,29 | delta ≤ 0,15 | nulo fraco |
| **04 — esta** | 42 vs 155 | delta ≥ 0,28 | delta ≤ 0,08 | **inconclusiva** |

A ironia metodológica vale registrar no artigo: **a comparação com o melhor desenho é a que
tem o pior poder.** Isolar a circularidade custou condicionar a amostra às sinalizadas, que
são poucas — 197 arquivos dos 730.

## O que seria preciso para responder

**O gargalo são os 42 confirmados, não os disputados.** Mantendo os 42 e aumentando só o
outro grupo, o detectável praticamente não melhora:

| disputados | delta detectável |
|---:|---:|
| 155 (o que temos) | 0,282 |
| 500 | 0,260 |
| 5.000 | 0,251 |
| infinito | **0,250** (piso teórico) |

Ou seja: mesmo com infinitas amostras disputadas, este desenho nunca detectaria um efeito
menor que 0,25 — e efeito de 0,25 é grande para esta literatura. Coletar mais disputados
não resolve.

Para delta de 0,15 (pequeno e plausível), mantendo a proporção 1:3,7 observada, seriam
precisos **148 confirmados e 547 disputados**. Temos 42 e 155 — cerca de 3,5× menos.

Caminhos possíveis, nenhum barato:
- ampliar a cobertura do binding, que o step 2 já explorou até 37,5% e cujo custo de
  construto está medido;
- usar outro dataset de code smell com mais anotações por classe;
- aceitar a pergunta como não respondível com o MLCQ e declarar isso.

## Ressalva adicional

No ramo determinístico, a mediana de **densidade é maior no grupo disputado** (1,865 contra
1,552) — direção contrária à hipótese. Sem significância e com poder insuficiente, não
sustenta afirmação nenhuma; está registrado para não parecer omissão seletiva quando alguém
abrir o CSV.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `disputados.py` | a análise |
| `dados/disputados.csv` | 6 resultados: 2 ramos × 3 desfechos, com delta, p, p ajustado e delta detectável |
