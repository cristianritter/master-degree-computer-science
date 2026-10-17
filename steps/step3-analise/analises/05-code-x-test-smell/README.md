# Análise 05 — Code smell × test smell

**Pergunta.** Algum code smell específico se associa a algum test smell específico?

**Resposta curta.** Nenhuma das 52 células sobrevive ao FDR (menor p ajustado 0,104).
Duas passam do efeito que o próprio N detecta, feature envy × Verbose Test (0,149) e blob ×
Duplicate Assert (0,162); ficam registradas como candidatas, não como achado.

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

> **Refeita em 17/10/2026** com a unidade de rótulo corrigida para (amostra, smell) (step 2,
> seção 3). Na unidade antiga cada arquivo tinha, na prática, um smell avaliado, e o N de
> data class era 114; agora blob e data class são julgados juntos em cada classe, e o N de
> cada linha da grade subiu (306 a 429). O resultado mudou: a versão anterior dizia
> "nenhuma célula alcança o r detectável", o que não vale mais.

Ramo determinístico, 730 arquivos. **Nenhuma célula sobrevive ao FDR**; o menor p ajustado
é 0,104.

As seis células com p nominal < 0,05:

| code smell | test smell | N | rho | p | p ajustado | r detectável |
|---|---|---:|---:|---:|---:|---:|
| feature envy | Verbose Test | 426 | 0,149 | 0,002 | 0,104 | 0,135 |
| blob | Duplicate Assert | 306 | 0,162 | 0,004 | 0,113 | 0,159 |
| long method | Magic Number Test | 429 | 0,126 | 0,009 | 0,156 | 0,134 |
| long method | Verbose Test | 429 | 0,121 | 0,012 | 0,160 | 0,134 |
| data class | Eager Test | 291 | 0,131 | 0,025 | 0,262 | 0,163 |
| data class | Lazy Test | 291 | 0,123 | 0,035 | 0,307 | 0,163 |

Com 52 testes e α = 0,05, o acaso sozinho produziria ~2,6 significâncias nominais. Seis é
mais que isso, e nenhuma resiste ao ajuste.

O N de cada code smell limita o que a linha enxerga:

| code smell | N | r detectável |
|---|---:|---:|
| long method | 429 | 0,134 |
| feature envy | 426 | 0,135 |
| blob | 306 | 0,159 |
| data class | 306 | 0,159 |

Eager e Lazy Test perdem as linhas `nome_divergente` e ficam com N menor (291 a 395, r
detectável 0,140 a 0,163).

## O filtro quase não mudou nada

| | sem filtro | com filtro |
|---|---:|---:|
| data class × Eager Test | 0,127 (N = 306) | 0,131 (N = 291) |
| data class × Lazy Test | 0,119 (N = 306) | 0,123 (N = 291) |

Nas oito células a diferença fica abaixo de 0,02.

A prévia de 04/10 deu 0,21 nessas duas células, sem filtro. Ela foi rodada sobre o rótulo
com defeito e não se reproduz mais: na unidade corrigida, as mesmas células sem filtro dão
0,127 e 0,119.

## A leitura

**Não dá para afirmar associação em nenhum par.** Nenhuma célula sobrevive ao ajuste para
52 comparações.

**Duas células merecem registro, e só isso.** Feature envy × Verbose Test (0,149) e blob ×
Duplicate Assert (0,162) passam do r detectável da sua linha, com p ajustado de 0,104 e
0,113. Estar acima do detectável não é critério de significância: diz só que, se o efeito
for desse tamanho, o desenho tem poder para vê-lo. Numa exploração com 52 células, são
candidatas para um estudo confirmatório, não achados.

**O que a grade acrescenta à análise 02:** o nulo agregado não esconde um par forte. As
células mais altas ficam em 0,12 a 0,16, a mesma ordem do limite superior da análise 01.

**Para o artigo:** a grade só pode ser mostrada com o N, o p ajustado e o r detectável ao
lado, e sem destaque por p nominal.

---

## Artefatos

| arquivo | conteúdo |
|---|---|
| `cruzado.py` | a análise |
| `dados/cruzado.csv` | 60 linhas: 52 da família (`recorte = principal`) e 8 de sensibilidade (`sensibilidade_sem_filtro`), com rho, p, p ajustado, IC e r detectável |
