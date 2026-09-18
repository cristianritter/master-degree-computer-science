# Análise 00 — Caracterização das variáveis

**Pergunta.** Que forma têm as variáveis, e que teste estatístico elas permitem?

**Resposta curta.** Teste paramétrico está descartado, o tamanho do teste é confundidor não
controlado, e uma coluna do step 2 estava errada.

```bash
python caracterizar.py --csv
python caracterizar.py --ramo deterministico
```

Roda antes de tudo, pelo mesmo motivo que a auditoria do step 2 existe: escolher o teste
sem olhar a distribuição é assumir o que devia ser conferido.

---

## 1. As duas variáveis são fortemente assimétricas

Ramo determinístico, 730 arquivos:

| variável | zeros | mediana | p95 | máx | assimetria |
|---|---:|---:|---:|---:|---:|
| code smell agregado (`sev_media`) | 72,1% | 0,00 | 1,17 | 2,17 | 2,14 |
| `blob` | 66,3% | 0,00 | 1,04 | 1,62 | 1,61 |
| `feature envy` | 79,0% | 0,00 | 0,50 | 1,50 | 3,36 |
| Assertion Roulette | 32,6% | 4 | 77 | 533 | 6,02 |
| Lazy Test | 42,9% | 1 | 21 | **1.116** | **21,28** |
| Exception Catching Throwing | 72,1% | 0 | 11 | 213 | 16,00 |
| `ts_n_total` | 8,5% | 15 | 209 | 1.552 | 6,62 |

**Consequência: teste paramétrico está descartado.** Com 72% de zeros no rótulo e
assimetria de 21 numa das variáveis de desfecho, média e desvio-padrão não descrevem esses
dados. Cabe **Spearman** ou modelo que trate o excesso de zeros — não é escolha de gosto, é
o que a distribuição permite.

O Lazy Test com máximo 1.116 merece atenção própria: um único arquivo pode dominar qualquer
correlação não-robusta. Postos resolvem isso; média não.

## 2. O tamanho do teste é confundidor óbvio

| | mediana | p95 | máx |
|---|---:|---:|---:|
| LOC de teste (determinístico) | 181 | 1.323 | 4.668 |
| LOC de teste (ampliado) | 426 | 4.969 | **39.546** |
| métodos de teste (determinístico) | 9 | 61 | 297 |

As tabelas do step 2 saíram com `--agregacao soma`. Um arquivo de teste com 4.668 linhas
tem mais ocorrências de tudo que um de 50 linhas, independentemente de qualidade. **Sem
normalizar, a análise mede tamanho de teste, não qualidade.**

Três saídas, todas levadas adiante pela análise 01 em vez de escolhidas aqui:

1. `--agregacao densidade` no step 2, que divide pelo número de métodos;
2. manter a soma e usar `n_metodos_teste` como covariável;
3. usar `ts_n_distintos`, menos sensível a tamanho — e a única variável de desfecho **não
   patológica**, com assimetria 0,90 contra 6 a 21 das contagens.

## 3. Contaminação e estratos

| | determinístico | ampliado |
|---|---:|---:|
| arquivos com teste `nome_divergente` | 53 (7,3%) | 254 (18,6%) |
| `negativo_confiavel` | 72,6% | 72,4% |
| `disputado` | 21,9% | 22,3% |
| `positivo_confiavel` | 6,0% | 5,8% |
| `negativo_1_review` | 0,4% | 0,7% |

Análise com **Eager Test** ou **Lazy Test** tem que filtrar ou estratificar por
`n_testes_nome_divergente`. General Fixture não é afetado e serve como controle (step 1,
seção 5) — a análise 02 usa isso.

A distribuição de estratos é praticamente idêntica nos dois ramos: mais uma evidência de
que o binding não desloca o rótulo.

## 4. Um defeito encontrado aqui e corrigido no step 2

`ts_n_distintos` dava **19** num arquivo — impossível, já que só existem 13 smells
habilitados. A coluna somava a contagem de distintos de cada classe de teste em vez de unir
os conjuntos; o valor correto daquele arquivo era 10.

Corrigido em `montar_analise.py`: passou a ser união, e não depende mais de `--agregacao`.
Os máximos voltaram para dentro do possível — 12 e 13.

> O defeito apareceu por olhar a distribuição antes de usar a variável, não por revisão de
> código. Mesmo padrão da seção 4 do step 2, em que a discordância entre README e
> implementação apareceu ao montar a auditoria.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `caracterizar.py` | a caracterização |
| `dados/caracterizacao.csv` | 23 linhas: n, zeros, quartis, p95, máximo e assimetria por variável |
