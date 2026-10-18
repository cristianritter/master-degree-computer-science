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

**Nenhum sobrevive à correção FDR.** O menor p ajustado é 0,260.

Os seis que alcançam significância nominal:

| test smell | desfecho | N | rho | p | p ajustado |
|---|---|---:|---:|---:|---:|
| Magic Number Test | bruto | 730 | 0,086 | 0,020 | 0,260 |
| Assertion Roulette | bruto | 730 | 0,081 | 0,029 | 0,260 |
| Verbose Test | bruto | 730 | 0,078 | 0,035 | 0,260 |
| Magic Number Test | densidade | 726 | 0,073 | 0,049 | 0,260 |
| Magic Number Test | bruto, filtrado | 677 | 0,084 | 0,029 | 0,391 |
| Assertion Roulette | bruto, filtrado | 677 | 0,077 | 0,045 | 0,391 |

## O achado negativo com mais conteúdo

Os dois smells que **dependem da classe de produção** — os candidatos naturais — são os
mais próximos de zero da tabela inteira:

| smell | densidade, todas as linhas | sem `nome_divergente` |
|---|---:|---:|
| Eager Test | −0,020 (N=726) | −0,027 (N=677) |
| Lazy Test | 0,038 (N=726) | 0,031 (N=677) |
| **General Fixture** (controle) | 0,006 (N=726) | 0,012 (N=677) |

Isso é mais informativo que um nulo genérico: se a hipótese fosse verdadeira, a relação
teria de aparecer com mais força exatamente onde o instrumento enxerga a ligação
teste–produção. Aparece com menos.

## O controle do step 1 se comporta como previsto

General Fixture não depende da classe de produção, então o filtro de `nome_divergente` não
deveria mudá-lo — e não muda (0,006 → 0,012). É a validação de que o filtro faz o que o
step 1 documentou, e não está removendo linhas por outro motivo.

## O "perto de zero" de Eager e Lazy não é artefato do instrumento

O JNose mede Eager Test e Lazy Test contra a classe de produção que **ele** resolve, não
contra a que o binding ligou. Nos pares de `convencao`, o JNose pode não ter resolvido
classe nenhuma — e aí Eager e Lazy ficam perto de zero por construção — ou ter resolvido
outra. Se isso explicasse o resultado, o argumento acima estaria apoiado num defeito.

A sensibilidade restringe aos arquivos cujos testes foram todos ligados por
`caminho_exato`, onde as duas classes coincidem por construção (`comum.so_caminho_exato`),
sem `nome_divergente`. São 3 testes fora da família:

| smell | densidade, sem `nome_divergente` | só `caminho_exato` |
|---|---:|---:|
| Eager Test | −0,027 (N=677) | −0,032 (N=649), IC [−0,109, 0,045] |
| Lazy Test | 0,031 (N=677) | 0,024 (N=649), IC [−0,053, 0,100] |
| General Fixture (controle) | 0,012 (N=677) | 0,016 (N=649) |

Eager e Lazy continuam perto de zero onde o instrumento mede a classe certa. O argumento se
sustenta.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `por_test_smell.py` | a análise |
| `dados/por_test_smell.csv` | 55 linhas: 52 da família e 3 da sensibilidade (`recorte = sensibilidade_caminho_exato`), com rho, p, p ajustado, IC e proporção de zeros |
