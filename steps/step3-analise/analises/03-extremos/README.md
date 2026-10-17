# Análise 03 — Extremos de evidência

**Pergunta.** Classes em que os revisores **confirmaram** algum code smell têm testes com
mais test smell que classes em que ninguém sinalizou nada?

**Resposta curta.** Têm mais test smell em contagem, e isso sobrevive ao FDR. Em densidade,
não: a diferença some quando o tamanho do teste é normalizado. É o padrão da análise 01,
agora visto pela comparação de grupos.

```bash
python extremos.py --csv
```

> **Refeita em 17/10/2026.** Até então a análise exigia estrato único por arquivo e
> comparava `positivo_confiavel` (42 arquivos) com `negativo_confiavel` (523). Com a
> unidade de rótulo corrigida para (amostra, smell) (step 2, seção 3), quase todo arquivo
> reúne estratos diferentes, os grupos caíram para 14 e 2, e o teste não rodava. A regra
> abaixo foi fixada antes de rodar a análise com ela. A versão anterior, e o resultado
> dela, estão no histórico do git e no caderno do README do step 3.

---

## Por que comparar extremos em vez de correlacionar

A correlação da análise 01 pressupõe relação monotônica ao longo de toda a faixa de
severidade. O desenho do MLCQ não sustenta bem isso: a severidade média é contínua, mas vem
de um processo de rotulagem circular com o crosscheck (step 2, seção 3).

O que o desenho sustenta melhor é comparar os extremos de evidência, com o arquivo
classificado pelo conjunto dos seus smells (`variaveis.grupo_arquivo`):

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

| desfecho | mediana confirmados | mediana limpos | delta | p | p ajustado |
|---|---:|---:|---:|---:|---:|
| bruto | 21,0 | 14,0 | 0,138 | 0,013 | **0,020** |
| densidade | 1,800 | 1,636 | 0,074 | 0,184 | 0,184 |
| distintos | 5,0 | 4,0 | 0,138 | 0,012 | **0,020** |

**Ampliado** — 267 confirmados, 985 limpos:

| desfecho | mediana confirmados | mediana limpos | delta | p | p ajustado |
|---|---:|---:|---:|---:|---:|
| bruto | 32,0 | 27,0 | 0,031 | 0,438 | 0,831 |
| densidade | 1,456 | 1,550 | −0,009 | 0,831 | 0,831 |
| distintos | 5,0 | 5,0 | 0,009 | 0,827 | 0,831 |

## A leitura

**No ramo determinístico, os desfechos sensíveis a tamanho separam os grupos, e a densidade
não.** Bruto e distintos dão delta 0,138, significativos depois do FDR. A densidade dá
0,074, com p = 0,184.

É o mesmo mecanismo medido na análise 01: classes com code smell confirmado tendem a ter
testes maiores, e teste maior acumula mais ocorrências de tudo. A mediana de métodos de
teste não é controlada aqui; a análise 01 controla, e lá a associação cai a ~0,06 sem
significância.

**A densidade aponta na direção esperada, mas sem decidir.** Com 136 contra 526, esta
comparação detectaria delta ≥ 0,156 com 80% de poder; o 0,074 observado está abaixo disso.
É compatível com o limite superior da análise 01 (r < 0,12), não o contradiz.

**O ramo ampliado não separa em nada**, como na análise 01: com 10,1% de precisão para "o
teste testa esta classe", a atenuação leva tudo para perto de zero.

> A versão anterior desta análise dizia que "o grupo negativo tem densidade ligeiramente
> maior". Na unidade corrigida isso não se sustenta: o confirmado tem mediana maior (1,800
> contra 1,636). A frase foi retirada.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `extremos.py` | a análise |
| `dados/extremos.csv` | 6 resultados: 2 ramos × 3 desfechos, com delta, p e p ajustado |
