# Análise 02 — Cada test smell isolado

**Pergunta.** Algum dos 13 test smells se comporta diferente do conjunto?

**Resposta curta.** Nenhum. E os dois que tinham a melhor razão teórica para aparecer são
justamente os mais próximos de zero.

```bash
python por_test_smell.py --csv
python por_test_smell.py --ramo ampliado
```

---

## Por que valia perguntar

Até aqui o desfecho foi sempre agregado. Mas os 13 smells não são equivalentes: **Eager
Test e Lazy Test dependem da classe de produção para serem detectados** — o JNose precisa
resolver qual classe o teste exercita para contá-los —, enquanto Assertion Roulette e
Verbose Test são propriedades internas do arquivo de teste.

Se existisse relação entre qualidade do teste e code smell da classe, os dois primeiros
eram os candidatos naturais a mostrá-la.

52 testes: 13 smells × bruto/densidade × com e sem o filtro de `nome_divergente`, ramo
determinístico, contra o code smell agregado. O ajuste para comparações múltiplas
(Benjamini-Hochberg) entra aqui de verdade — com 52 testes, α = 0,05 por teste deixaria
~2,6 falsos positivos esperados.

---

## Resultado

**Nenhum sobrevive à correção FDR.** O menor p ajustado é 0,283.

Os cinco que alcançam significância nominal:

| test smell | desfecho | rho | p | p ajustado |
|---|---|---:|---:|---:|
| Magic Number Test | bruto | 0,087 | 0,019 | 0,283 |
| Assertion Roulette | bruto | 0,078 | 0,035 | 0,283 |
| Verbose Test | bruto | 0,077 | 0,037 | 0,283 |
| Magic Number Test | densidade | 0,074 | 0,046 | 0,283 |
| Magic Number Test | bruto, filtrado | 0,085 | 0,027 | 0,380 |

## O achado negativo com mais conteúdo

Os dois smells que **dependem da classe de produção** — os candidatos naturais — são os
mais próximos de zero da tabela inteira:

| smell | densidade, todas as linhas | sem `nome_divergente` |
|---|---:|---:|
| Eager Test | −0,020 (N=726) | −0,028 (N=677) |
| Lazy Test | 0,038 (N=726) | 0,031 (N=677) |
| **General Fixture** (controle) | 0,008 (N=726) | 0,013 (N=677) |

Isso é mais informativo que um nulo genérico: se a hipótese fosse verdadeira, a relação
teria de aparecer com mais força exatamente onde o instrumento enxerga a ligação
teste–produção. Aparece com menos.

## O controle do step 1 se comporta como previsto

General Fixture não depende da classe de produção, então o filtro de `nome_divergente` não
deveria mudá-lo — e não muda (0,008 → 0,013). É a validação de que o filtro faz o que o
step 1 documentou, e não está removendo linhas por outro motivo.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `por_test_smell.py` | a análise |
| `dados/por_test_smell.csv` | 52 resultados com rho, p, p ajustado, IC e proporção de zeros |
