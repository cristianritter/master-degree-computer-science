# Análise 01 — Correlação agregada

**Pergunta.** A quantidade de test smell no teste correlaciona com a severidade de code
smell na classe de produção?

**Resposta curta.** A associação aparente existe, mas é efeito do tamanho do teste. O
desfecho que isola qualidade de tamanho dá nulo — e o nulo é informativo.

```bash
python explorar.py --por-smell --csv
```

Spearman sobre postos, IC95% por z de Fisher, rótulo `sev_media` contínuo.

---

## Resultado

Ramo determinístico, 730 arquivos, code smell agregado:

| desfecho | N | rho | p | IC95% | rho com o tamanho do teste |
|---|---:|---:|---:|---|---:|
| `bruto` (soma das ocorrências) | 730 | 0,092 | 0,012 | [0,020, 0,164] | **0,554** |
| `densidade` (soma / métodos) | 726 | 0,047 | 0,204 | [−0,026, 0,120] | −0,077 |
| `distintos` (quantos dos 13) | 730 | 0,084 | 0,024 | [0,011, 0,155] | **0,433** |

| controlando `n_metodos_teste` | N | rho parcial | p |
|---|---:|---:|---:|
| `bruto` | 730 | 0,058 | 0,115 |
| `distintos` | 730 | 0,055 | 0,140 |

Os dois desfechos que dependem de tamanho dão significância nominal; o normalizado não dá.
Sob controle explícito de tamanho, os dois caem para ~0,056 e perdem a significância.

## O mecanismo, medido

A confusão não é hipótese — as três pernas do triângulo estão medidas:

| par | rho |
|---|---:|
| test smell bruto × tamanho do teste | 0,554 |
| code smell × tamanho do teste (`n_metodos_teste`) | 0,079 (p = 0,032) |
| code smell × tamanho do teste (`loc_teste`) | 0,091 (p = 0,014) |

Classe com mais code smell tende a ter teste maior; teste maior tem mais ocorrências de
tudo. O produto das duas relações gera a correlação bruta de 0,092 sem que exista relação
com *qualidade* do teste.

**Se a análise tivesse parado no desfecho bruto, o artigo reportaria uma correlação
positiva significativa que é artefato.**

## Ramo ampliado

| desfecho | N | rho | p |
|---|---:|---:|---:|
| `bruto` | 1.369 | 0,015 | 0,568 |
| `densidade` | 1.365 | 0,003 | 0,915 |
| `distintos` | 1.369 | 0,001 | 0,973 |

Tudo em zero, como esperado: com 10,1% de precisão para o construto "o teste testa esta
classe", a atenuação por erro de medida leva qualquer relação verdadeira para perto de
zero. Ele **não contradiz** o determinístico — não tem como discordar dele.

## Por code smell individual

**Determinístico.** Só `blob`/`bruto` alcança p < 0,05, e a densidade do mesmo smell é
−0,005:

| smell | N | bruto | densidade | distintos |
|---|---:|---:|---:|---:|
| blob | 196 | **0,148 (p=0,038)** | −0,005 (p=0,948) | 0,100 (p=0,163) |
| data class | 114 | 0,124 (p=0,189) | 0,096 (p=0,313) | 0,174 (p=0,063) |
| feature envy | 186 | 0,069 (p=0,351) | 0,070 (p=0,343) | 0,094 (p=0,201) |
| long method | 251 | 0,117 (p=0,063) | 0,082 (p=0,199) | 0,088 (p=0,167) |

**Ampliado.** `blob`/`distintos` dá rho 0,121 (p = 0,018) — mesmo padrão: rho com tamanho
0,560, e a densidade do mesmo par dá −0,058 (p = 0,259).

**As quatro significâncias nominais desta análise estão em desfecho sensível a tamanho, e
as quatro somem quando o tamanho é normalizado ou controlado.**

## O que dá para afirmar

**Não dá para afirmar que existe relação.** O desfecho que isola qualidade dá rho = 0,047
com IC [−0,026, 0,120], que inclui o zero.

**Dá para afirmar que, se existe, é pequena** — e isso vem do step 2:

- a precisão do binding está medida em 94,2%, então o nulo não é explicável por ruído de
  ligação;
- o poder está calculado: este desenho detecta r ≥ 0,104 com 80% de poder.

Juntando: **qualquer associação entre densidade de test smell e severidade de code smell,
em classes com teste dedicado, é menor que r ≈ 0,12.**

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `explorar.py` | a análise |
| `dados/exploracao.csv` | 40 resultados: 30 correlações simples, 6 parciais, 4 do confundidor |
