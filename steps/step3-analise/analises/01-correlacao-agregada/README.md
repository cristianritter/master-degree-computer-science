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
| `bruto` (soma das ocorrências) | 730 | 0,087 | 0,019 | [0,014, 0,158] | **0,560** |
| `densidade` (soma / métodos) | 726 | 0,044 | 0,238 | [−0,029, 0,116] | −0,087 |
| `distintos` (quantos dos 20) | 730 | 0,072 | 0,051 | [−0,000, 0,144] | **0,447** |

| controlando `n_metodos_teste` | N | rho parcial | p |
|---|---:|---:|---:|
| `bruto` | 730 | 0,052 | 0,162 |
| `distintos` | 730 | 0,042 | 0,260 |

O desfecho bruto dá significância nominal e o de distintos fica no limiar; o normalizado
não chega perto. Sob controle explícito de tamanho, os dois caem para ~0,05 e ficam longe
da significância.

## O mecanismo, medido

A confusão não é hipótese — as três pernas do triângulo estão medidas:

| par | rho |
|---|---:|
| test smell bruto × tamanho do teste | 0,560 |
| code smell × tamanho do teste (`n_metodos_teste`) | 0,078 (p = 0,035) |
| code smell × tamanho do teste (`loc_teste`) | 0,090 (p = 0,015) |

Classe com mais code smell tende a ter teste maior; teste maior tem mais ocorrências de
tudo. O produto das duas relações gera a correlação bruta de 0,087 sem que exista relação
com *qualidade* do teste.

**Se a análise tivesse parado no desfecho bruto, o artigo reportaria uma correlação
positiva significativa que é artefato.**

## Ramo ampliado

| desfecho | N | rho | p |
|---|---:|---:|---:|
| `bruto` | 1.369 | 0,008 | 0,775 |
| `densidade` | 1.365 | −0,004 | 0,888 |
| `distintos` | 1.369 | −0,013 | 0,641 |

Tudo em zero, como esperado: com 10,1% de precisão para o construto "o teste testa esta
classe", a atenuação por erro de medida leva qualquer relação verdadeira para perto de
zero. Ele **não contradiz** o determinístico — não tem como discordar dele.

## Por code smell individual

A RQ1 também é respondida para cada smell, em densidade. Um nulo agregado poderia esconder
smells com efeitos opostos que se cancelam; a tabela mostra que não é o caso. Os quatro
testes formam uma família, com p ajustado por Benjamini-Hochberg:

| smell | N | rho (densidade) | IC95% | p | p ajustado |
|---|---:|---:|---|---:|---:|
| blob | 306 | 0,002 | [−0,110, 0,114] | 0,968 | 0,968 |
| data class | 306 | 0,013 | [−0,099, 0,125] | 0,823 | 0,968 |
| feature envy | 426 | 0,035 | [−0,060, 0,129] | 0,473 | 0,945 |
| long method | 429 | 0,053 | [−0,042, 0,147] | 0,273 | 0,945 |

Nenhum smell se associa à densidade de test smell, e o teto do IC fica entre 0,11 e 0,15.

Nos três desfechos, o quadro completo:

**Determinístico.** Duas células alcançam p < 0,05, ambas no desfecho bruto, e a densidade
do mesmo smell fica perto de zero:

| smell | N | bruto | densidade | distintos |
|---|---:|---:|---:|---:|
| blob | 307 | **0,128 (p=0,025)** | 0,002 (p=0,968) | 0,097 (p=0,090) |
| data class | 307 | 0,058 (p=0,309) | 0,013 (p=0,823) | 0,086 (p=0,133) |
| feature envy | 429 | 0,023 (p=0,641) | 0,035 (p=0,473) | 0,046 (p=0,346) |
| long method | 432 | **0,097 (p=0,044)** | 0,053 (p=0,273) | 0,067 (p=0,162) |

**Ampliado.** Nenhuma célula alcança p < 0,05; a maior é feature envy em densidade, 0,062
(p = 0,093).

**As três significâncias nominais desta análise (o agregado e as duas células acima) estão
no desfecho bruto, sensível a tamanho, e as três somem quando o tamanho é normalizado.**

## O que dá para afirmar

**Não dá para afirmar que existe relação.** O desfecho que isola qualidade dá rho = 0,044
com IC [−0,029, 0,116], que inclui o zero.

**Dá para afirmar que, se existe, é pequena** — e isso vem do step 2:

- a precisão do binding está medida em 94,2%, então o nulo não é explicável por ruído de
  ligação;
- o poder está calculado: este desenho detecta r ≥ 0,104 com 80% de poder.

Juntando: **qualquer associação entre densidade de test smell e severidade de code smell,
em classes com teste dedicado, é menor que r ≈ 0,12 no agregado, e menor que 0,11 a 0,15
em cada smell.**

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `explorar.py` | a análise |
| `dados/exploracao.csv` | 40 resultados: 30 correlações simples, 6 parciais, 4 do confundidor; `p_ajustado` preenchido só na família da RQ1 por smell |
