# Análise 01 — Correlação agregada

**Pergunta.** A quantidade de test smell no teste correlaciona com a severidade de code
smell na classe de produção?

**Resposta curta.** A associação aparente existe, mas é efeito do tamanho do teste. O
desfecho que isola qualidade de tamanho dá nulo, e o nulo é informativo.

```bash
python explorar.py --por-smell --csv
```

Spearman sobre postos, IC95% por z de Fisher, rótulo `sev_media` contínuo.

O rótulo agregado do arquivo é **o maior `sev_media` entre os smells avaliados nele**:
quase todo arquivo tem dois smells julgados (blob e data class numa classe, por exemplo),
então o agregado é o smell percebido como mais grave.

---

## Resultado

Ramo determinístico, 730 arquivos, code smell agregado:

| desfecho | N | rho | p | IC95% | rho com o tamanho do teste |
|---|---:|---:|---:|---|---:|
| `bruto` (soma das ocorrências) | 730 | 0,094 | 0,011 | [0,022, 0,166] | **0,554** |
| `densidade` (soma / métodos) | 726 | 0,050 | 0,175 | [−0,022, 0,123] | −0,077 |
| `distintos` (quantos dos 13) | 730 | 0,084 | 0,022 | [0,012, 0,156] | **0,433** |

| controlando `n_metodos_teste` | N | rho parcial | p |
|---|---:|---:|---:|
| `bruto` | 730 | 0,062 | 0,096 |
| `distintos` | 730 | 0,056 | 0,129 |

Os dois desfechos que dependem de tamanho dão significância nominal; o normalizado não dá.
Sob controle explícito de tamanho, os dois caem para ~0,06 e perdem a significância.

## O mecanismo, medido

A confusão não é hipótese — as três pernas do triângulo estão medidas:

| par | rho |
|---|---:|
| test smell bruto × tamanho do teste | 0,554 |
| code smell × tamanho do teste (`n_metodos_teste`) | 0,078 (p = 0,035) |
| code smell × tamanho do teste (`loc_teste`) | 0,090 (p = 0,015) |

Classe com mais code smell tende a ter teste maior; teste maior tem mais ocorrências de
tudo. O produto das duas relações gera a correlação bruta de 0,094 sem que exista relação
com *qualidade* do teste.

**Se a análise tivesse parado no desfecho bruto, o artigo reportaria uma correlação
positiva significativa que é artefato.**

## Ramo ampliado

| desfecho | N | rho | p |
|---|---:|---:|---:|
| `bruto` | 1.369 | 0,012 | 0,659 |
| `densidade` | 1.365 | 0,001 | 0,959 |
| `distintos` | 1.369 | −0,003 | 0,913 |

Tudo em zero, como esperado: com 10,1% de precisão para o construto "o teste testa esta
classe", a atenuação por erro de medida leva qualquer relação verdadeira para perto de
zero. Ele **não contradiz** o determinístico — não tem como discordar dele.

## Por code smell individual

A RQ1 também é respondida para cada smell, em densidade. Um nulo agregado poderia esconder
smells com efeitos opostos que se cancelam; a tabela mostra que não é o caso. Os quatro
testes formam uma família, com p ajustado por Benjamini-Hochberg:

| smell | N | rho (densidade) | IC95% | p | p ajustado |
|---|---:|---:|---|---:|---:|
| blob | 306 | 0,019 | [−0,094, 0,131] | 0,745 | 0,836 |
| data class | 306 | 0,012 | [−0,100, 0,124] | 0,836 | 0,836 |
| feature envy | 426 | 0,040 | [−0,055, 0,135] | 0,408 | 0,816 |
| long method | 429 | 0,053 | [−0,042, 0,147] | 0,273 | 0,816 |

Nenhum smell se associa à densidade de test smell, e o teto do IC fica entre 0,12 e 0,15.

Nos três desfechos, o quadro completo:

**Determinístico.** Três células alcançam p < 0,05, todas em desfecho sensível a tamanho,
e a densidade do mesmo smell fica perto de zero:

| smell | N | bruto | densidade | distintos |
|---|---:|---:|---:|---:|
| blob | 307 | **0,140 (p=0,014)** | 0,019 (p=0,745) | **0,113 (p=0,047)** |
| data class | 307 | 0,063 (p=0,273) | 0,012 (p=0,836) | 0,087 (p=0,129) |
| feature envy | 429 | 0,028 (p=0,560) | 0,040 (p=0,408) | 0,062 (p=0,198) |
| long method | 432 | **0,101 (p=0,035)** | 0,053 (p=0,273) | 0,078 (p=0,105) |

**Ampliado.** Nenhuma célula alcança p < 0,05; a maior é feature envy em densidade, 0,066
(p = 0,074).

**As cinco significâncias nominais desta análise estão em desfecho sensível a tamanho, e
as cinco somem quando o tamanho é normalizado.**

## O que dá para afirmar

**Não dá para afirmar que existe relação.** O desfecho que isola qualidade dá rho = 0,050
com IC [−0,022, 0,123], que inclui o zero.

**Dá para afirmar que, se existe, é pequena** — e isso vem do step 2:

- a precisão do binding está medida em 94,2%, então o nulo não é explicável por ruído de
  ligação;
- o poder está calculado: este desenho detecta r ≥ 0,104 com 80% de poder.

Juntando: **qualquer associação entre densidade de test smell e severidade de code smell,
em classes com teste dedicado, é menor que r ≈ 0,12 no agregado, e menor que 0,13 a 0,15
em cada smell.**

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `explorar.py` | a análise |
| `dados/exploracao.csv` | 40 resultados: 30 correlações simples, 6 parciais, 4 do confundidor; `p_ajustado` preenchido só na família da RQ1 por smell |
