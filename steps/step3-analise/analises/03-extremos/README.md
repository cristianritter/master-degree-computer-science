# Análise 03 — Extremos de evidência

**Pergunta.** Classes em que os revisores **confirmaram** algum code smell têm testes com
mais test smell que classes em que ninguém sinalizou nada?

**Resposta curta.** Têm mais test smell em contagem, e isso sobrevive ao FDR. Em densidade,
não: a diferença some quando o tamanho do teste é normalizado. É o padrão da análise 01,
agora visto pela comparação de grupos.

```bash
python extremos.py --csv
```

---

## Por que comparar extremos em vez de correlacionar

A correlação da análise 01 pressupõe relação monotônica ao longo de toda a faixa de
severidade. O desenho do MLCQ não sustenta bem isso: a severidade média é contínua, mas vem
de um processo de rotulagem circular com o crosscheck (step 2, seção 3).

O que o desenho sustenta melhor é comparar os extremos de evidência. Como quase todo
arquivo reúne unidades (amostra, smell) de estratos diferentes — blob negativo e data class
confirmado, por exemplo —, o arquivo é classificado pelo conjunto dos seus smells
(`variaveis.grupo_arquivo`):

| grupo | definição |
|---|---|
| confirmado | algum smell do arquivo teve a maioria dos revisores marcando > `none` |
| limpo | nenhum revisor marcou > `none` em nenhum smell do arquivo |

O grupo limpo é quase todo de negativos com um único revisor. O step 2 mediu quanto vale um
`none` isolado: revisado de novo, coincide com a maioria final em 97,8% dos casos.

Mann-Whitney, que não supõe distribuição e lida com os 72% de zeros. O tamanho de efeito é
o r bisserial de postos (`delta`): a probabilidade de um arquivo do grupo confirmado ter
mais test smell que um do limpo, menos a probabilidade do contrário. Zero significa nenhuma
separação.

---

## Resultado

**Determinístico** — 136 confirmados, 526 limpos, 68 fora (67 só disputados e 1 cujo único
positivo é de revisor solitário):

| desfecho | mediana confirmados | mediana limpos | delta | p | p ajustado | delta detectável |
|---|---:|---:|---:|---:|---:|---:|
| bruto | 21,0 | 15,0 | 0,127 | 0,022 | **0,039** | 0,156 |
| densidade | 1,875 | 1,689 | 0,069 | 0,215 | 0,215 | 0,156 |
| distintos | 5,0 | 4,0 | 0,123 | 0,026 | **0,039** | 0,156 |

**Ampliado** — 267 confirmados, 985 limpos:

| desfecho | mediana confirmados | mediana limpos | delta | p | p ajustado | delta detectável |
|---|---:|---:|---:|---:|---:|---:|
| bruto | 35,0 | 29,0 | 0,026 | 0,508 | 0,890 | 0,112 |
| densidade | 1,550 | 1,600 | −0,016 | 0,693 | 0,890 | 0,112 |
| distintos | 5,0 | 6,0 | −0,005 | 0,890 | 0,890 | 0,112 |

## A leitura

**No ramo determinístico, os desfechos sensíveis a tamanho separam os grupos, e a densidade
não.** Bruto e distintos dão delta 0,127 e 0,123, significativos depois do FDR. A
densidade dá 0,069, com p = 0,215.

É o mesmo mecanismo medido na análise 01: classes com code smell confirmado tendem a ter
testes maiores, e teste maior acumula mais ocorrências de tudo. A mediana de métodos de
teste não é controlada aqui; a análise 01 controla, e lá a associação cai a ~0,05 sem
significância.

**A densidade aponta na direção esperada, mas sem decidir.** Com 135 contra 524 (os
arquivos com métodos de teste), esta comparação detectaria delta ≥ 0,156 com 80% de poder;
o 0,069 observado está abaixo disso.
É compatível com o limite superior da análise 01 (r < 0,12), não o contradiz.

**O ramo ampliado não separa em nada**, como na análise 01: com 10,1% de precisão para "o
teste testa esta classe", a atenuação leva tudo para perto de zero.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `extremos.py` | a análise |
| `dados/extremos.csv` | 6 resultados: 2 ramos × 3 desfechos, com delta, p, p ajustado e delta detectável |
