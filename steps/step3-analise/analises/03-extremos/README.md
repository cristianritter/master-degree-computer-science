# Análise 03 — Extremos de evidência

**Pergunta.** Classes em que os revisores **concordaram** que há code smell têm testes com
mais test smell que classes em que concordaram que não há?

**Resposta curta.** Não. E nas duas medianas de densidade, o grupo negativo tem
ligeiramente *mais* test smell.

```bash
python extremos.py --csv
```

---

## Por que comparar extremos em vez de correlacionar

A correlação da análise 01 pressupõe relação monotônica ao longo de toda a faixa de
severidade. O desenho do MLCQ não sustenta bem isso: a severidade média é contínua, mas vem
de um processo de rotulagem circular com o crosscheck (step 2, seção 3).

O que o desenho sustenta melhor é a comparação dos estratos que o step 2 definiu:

| grupo | definição |
|---|---|
| `positivo_confiavel` | a maioria dos revisores marcou > `none` |
| `negativo_confiavel` | 2+ revisores, nenhum marcou > `none` |

O estrato negativo é especialmente forte neste dataset: pelo desenho amostral, qualquer
sinalização teria escalado a amostra para mais revisores. São negativos com corroboração —
coisa rara em dataset de code smell.

Mann-Whitney, que não supõe distribuição e lida com os 72% de zeros. O tamanho de efeito é
o r bisserial de postos (`delta`): a probabilidade de um arquivo do grupo positivo ter mais
test smell que um do negativo, menos a probabilidade do contrário. Zero significa nenhuma
separação.

---

## Resultado

**Determinístico** — 42 positivos, 523 negativos, 165 fora (arquivo com amostras de mais de
um estrato, ou de estrato intermediário):

| desfecho | mediana positivos | mediana negativos | delta | p | p ajustado |
|---|---:|---:|---:|---:|---:|
| bruto | 18,0 | 14,0 | 0,113 | 0,223 | 0,334 |
| densidade | 1,552 | **1,609** | 0,032 | 0,736 | 0,736 |
| distintos | 5,0 | 4,0 | 0,154 | 0,094 | 0,282 |

**Ampliado** — 76 positivos, 976 negativos:

| desfecho | mediana positivos | mediana negativos | delta | p | p ajustado |
|---|---:|---:|---:|---:|---:|
| bruto | 46,0 | 27,0 | 0,084 | 0,222 | 0,667 |
| densidade | 1,506 | **1,543** | 0,029 | 0,673 | 0,673 |
| distintos | 5,0 | 5,0 | 0,039 | 0,571 | 0,673 |

## A leitura

**Nenhum resultado significativo, nem antes nem depois do ajuste.**

O detalhe mais eloquente está nas medianas de densidade: 1,552 contra 1,609 no
determinístico, 1,506 contra 1,543 no ampliado. **Nos dois ramos o grupo negativo tem
densidade de test smell ligeiramente maior.** A diferença não é significativa, mas mostra
ausência de separação — não uma tendência fraca na direção esperada, que é como um nulo às
vezes é apresentado.

## Ressalva de poder

Com 42 positivos, esta comparação só detectaria delta ≥ 0,29 com 80% de poder. Os
observados vão até 0,154. O nulo aqui é mais fraco que o da análise 01, onde N = 730 e o
detectável era r ≥ 0,104. A análise 04 leva essa questão adiante.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `extremos.py` | a análise |
| `dados/extremos.csv` | 6 resultados: 2 ramos × 3 desfechos, com delta, p e p ajustado |
