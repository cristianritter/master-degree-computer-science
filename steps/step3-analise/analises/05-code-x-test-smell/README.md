# Análise 05 — Code smell × test smell

**Pergunta.** Algum code smell específico se associa a algum test smell específico?

**Resposta curta.** Não. Nenhuma das 52 células sobrevive ao FDR, e nenhuma alcança o
efeito que o próprio N dela consegue detectar. Os dois pares mais altos, data class × Eager
e Lazy Test, ficam em 0,20, abaixo dos 0,27 detectáveis com N = 105.

```bash
python cruzado.py --csv
```

---

## De onde vem

Pedida pelo orientador (reunião de 04/10/2026, comentário da p. 7 do relatório: "tabela
dos N code smells mais correlacionados com test smells"). Uma **prévia** foi rodada naquele
dia e levada à reunião sem registro no repositório. Esta análise é a versão registrada, e a
prévia entra no caderno de tentativas do README do step 3: os testes dela foram olhados, e
isso conta.

A análise 02 já tinha perguntado se algum test smell se comporta diferente, contra o code
smell agregado. Esta subdivide pelo lado da produção: cada code smell com a sua própria
severidade.

## Decisões

Fixadas antes de rodar esta versão:

| | escolha | por quê |
|---|---|---|
| rótulo | `cs_<smell>_sev_media` do próprio code smell | vazio = não avaliado, fica fora; nunca vira 0 |
| desfecho | densidade (ocorrências / métodos de teste) | o bruto já se mostrou efeito de tamanho (análise 01) |
| Eager e Lazy Test | só linhas sem teste `nome_divergente` | caem 28× e 23× nessas linhas (step 1, seção 5) |
| família | os 52 testes, com p ajustado por Benjamini-Hochberg | mesmo tratamento da análise 02 |
| efeito detectável | r mínimo com 80% de poder, por célula | um rho abaixo dele não decide nada |

A prévia não filtrava `nome_divergente`. Usar como família principal um dado sabidamente
contaminado seria errado, então o filtro entrou, e as 8 células de Eager/Lazy sem filtro
rodam à parte, como sensibilidade, fora da família.

---

## Resultado

Ramo determinístico, 730 arquivos. **Nenhuma célula sobrevive ao FDR**; o menor p ajustado
é 0,271. **Nenhum |rho| alcança o r detectável da sua célula.**

As seis células com p nominal < 0,05:

| code smell | test smell | N | rho | p | p ajustado | r detectável |
|---|---|---:|---:|---:|---:|---:|
| long method | Magic Number Test | 249 | 0,167 | 0,008 | 0,271 | 0,177 |
| long method | Verbose Test | 249 | 0,162 | 0,010 | 0,271 | 0,177 |
| data class | Lazy Test | 105 | 0,202 | 0,039 | 0,372 | 0,270 |
| data class | Eager Test | 105 | 0,199 | 0,042 | 0,372 | 0,270 |
| blob | Duplicate Assert | 195 | 0,153 | 0,032 | 0,372 | 0,199 |
| long method | Assertion Roulette | 249 | 0,128 | 0,043 | 0,372 | 0,177 |

Com 52 testes e α = 0,05, o acaso sozinho produziria ~2,6 significâncias nominais. Seis
não é muito mais que isso, e nenhuma resiste ao ajuste.

O N de cada code smell limita o que a linha enxerga:

| code smell | N | r detectável |
|---|---:|---:|
| long method | 249 | 0,177 |
| blob | 195 | 0,199 |
| feature envy | 185 | 0,205 |
| data class | 114 | 0,260 |

Eager e Lazy Test perdem as linhas `nome_divergente` e ficam com N menor (data class: 105,
r detectável 0,270).

## O filtro quase não mudou nada

| | sem filtro (prévia) | com filtro |
|---|---:|---:|
| data class × Eager Test | 0,206 (N = 114) | 0,199 (N = 105) |
| data class × Lazy Test | 0,209 (N = 114) | 0,202 (N = 105) |

Nas oito células a diferença fica abaixo de 0,02. A sensibilidade reproduz a prévia (0,21),
o que confirma que a versão registrada é a mesma análise, com o filtro como única mudança.

## A leitura

**Não dá para afirmar associação em nenhum par.** Os candidatos mais altos estão abaixo do
efeito detectável, então a célula não distingue "não há relação" de "há uma relação menor
que o desenho enxerga".

**O que a grade acrescenta à análise 02:** o nulo agregado não esconde um par forte
compensado por outros. Se existisse um code smell com relação clara com um test smell, ele
apareceria aqui, e não aparece.

**Para o artigo:** a grade só pode ser mostrada com o N e o r detectável ao lado, e sem
destaque por p nominal. Sem isso, o 0,20 de data class lê como achado.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `cruzado.py` | a análise |
| `dados/cruzado.csv` | 60 linhas: 52 da família (`recorte = principal`) e 8 de sensibilidade (`sensibilidade_sem_filtro`), com rho, p, p ajustado, IC e r detectável |
