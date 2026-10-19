# Análise 00 — Caracterização das variáveis

**Pergunta.** Que forma têm as variáveis, e que teste estatístico elas permitem?

**Resposta curta.** Teste paramétrico está descartado, o tamanho do teste é confundidor não
controlado, e um dos 20 test smells (Default Test) não ocorre em nenhum arquivo.

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
| code smell agregado (`sev_media`) | 72,1% | 0,00 | 2,00 | 3,00 | 1,98 |
| `blob` | 73,6% | 0,00 | 1,92 | 3,00 | 2,12 |
| `feature envy` | 84,6% | 0,00 | 0,67 | 2,00 | 3,39 |
| Assertion Roulette | 32,6% | 4 | 77 | 533 | 6,02 |
| Lazy Test | 42,9% | 1 | 21 | **1.116** | **21,28** |
| Exception Catching Throwing | 72,1% | 0 | 11 | 213 | 16,00 |
| `ts_n_total` | 7,4% | 15 | 211,65 | 1.595 | 6,74 |

**Consequência: teste paramétrico está descartado.** Com 72% de zeros no rótulo e
assimetria de 21 numa das variáveis de desfecho, média e desvio-padrão não descrevem esses
dados. Cabe **Spearman** ou modelo que trate o excesso de zeros — não é escolha de gosto, é
o que a distribuição permite.

O Lazy Test com máximo 1.116 merece atenção própria: um único arquivo pode dominar qualquer
correlação não-robusta. Postos resolvem isso; média não.

O **Default Test** está zerado nos 730 arquivos do determinístico e nos 1.369 do ampliado: é
constante, então nenhuma correlação com ele é calculável. As análises o mantêm na tabela e o
deixam fora das famílias de teste (`estat.calculaveis`).

## 2. O tamanho do teste é confundidor óbvio

| | mediana | p95 | máx |
|---|---:|---:|---:|
| LOC de teste (determinístico) | 181 | 1.322,8 | 4.668 |
| LOC de teste (ampliado) | 426 | 4.968,8 | **39.546** |
| métodos de teste (determinístico) | 9 | 61 | 297 |

As tabelas do step 2 saíram com `--agregacao soma`. Um arquivo de teste com 4.668 linhas
tem mais ocorrências de tudo que um de 50 linhas, independentemente de qualidade. **Sem
normalizar, a análise mede tamanho de teste, não qualidade.**

Três saídas, todas levadas adiante pela análise 01 em vez de escolhidas aqui:

1. `--agregacao densidade` no step 2, que divide pelo número de métodos;
2. manter a soma e usar `n_metodos_teste` como covariável;
3. usar `ts_n_distintos`, menos sensível a tamanho — e a única variável de desfecho **não
   patológica**, com assimetria 0,51 contra 4,71 a 25,24 das contagens.

## 3. Contaminação e estratos

| | determinístico | ampliado |
|---|---:|---:|
| arquivos com teste `nome_divergente` | 53 (7,3%) | 254 (18,6%) |

Cada arquivo reúne unidades (amostra, smell) de estratos diferentes, então a tabela abaixo
conta **arquivos que contêm** cada estrato, e as porcentagens somam mais de 100%:

| arquivos com ao menos uma unidade | determinístico | ampliado |
|---|---:|---:|
| `negativo_1_review` | 72,9% | 73,0% |
| `negativo_confiavel` | 18,8% | 19,0% |
| `positivo_confiavel` | 18,6% | 19,5% |
| `disputado` | 15,1% | 14,4% |

E os grupos de arquivo usados pelas análises 03 e 04 (`variaveis.grupo_arquivo`):

| grupo | determinístico | ampliado |
|---|---:|---:|
| confirmado (algum smell com maioria > none) | 136 | 267 |
| limpo (nenhum voto positivo) | 526 | 985 |
| só disputado | 67 | 117 |
| fora (único positivo de revisor solitário) | 1 | 0 |

Análise com **Eager Test** ou **Lazy Test** tem que filtrar ou estratificar por
`n_testes_nome_divergente`. General Fixture não é afetado e serve como controle (step 1,
seção 5) — a análise 02 usa isso.

A distribuição é praticamente idêntica nos dois ramos: mais uma evidência de que o binding
não desloca o rótulo.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `caracterizar.py` | a caracterização |
| `dados/caracterizacao.csv` | 60 linhas, os dois ramos: n, zeros, quartis, p95, máximo e assimetria por variável |
