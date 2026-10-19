# Análise 05 — Code smell × test smell

**Pergunta.** Algum code smell específico se associa a algum test smell específico?

**Resposta curta.** Nenhum dos 76 testes sobrevive ao FDR (menor p ajustado 0,153). Duas
células passam do efeito que o próprio N detecta, feature envy × Verbose Test (0,149) e
blob × Duplicate Assert (0,162); ficam registradas como candidatas, não como achado.

```bash
python cruzado.py --csv
```

---

## De onde vem

Pedida pelo orientador (reunião de 04/10/2026, comentário da p. 7 do relatório: "tabela
dos N code smells mais correlacionados com test smells").

A análise 02 já tinha perguntado se algum test smell se comporta diferente, contra o code
smell agregado. Esta subdivide pelo lado da produção: cada code smell com a sua própria
severidade.

## Decisões

Fixadas antes de rodar:

| | escolha | por quê |
|---|---|---|
| rótulo | `cs_<smell>_sev_media` do próprio code smell | vazio = não avaliado, fica fora; nunca vira 0 |
| desfecho | densidade (ocorrências / métodos de teste) | o bruto já se mostrou efeito de tamanho (análise 01) |
| Eager e Lazy Test | só linhas sem teste `nome_divergente` | caem 28× e 23× nessas linhas (step 1, seção 5) |
| família | as 4 × 20 células, com p ajustado por Benjamini-Hochberg; célula de smell constante no ramo não é teste e fica fora | mesmo tratamento da análise 02 |
| efeito detectável | r mínimo com 80% de poder, por célula | um rho abaixo dele não decide nada |

As 8 células de Eager/Lazy também rodam sem o filtro, à parte, como sensibilidade, fora
da família.

---

## Resultado

Ramo determinístico, 730 arquivos. O Default Test não ocorre em nenhum arquivo (análise
00), então suas 4 células não têm correlação calculável: a família tem **76 testes**.
**Nenhum sobrevive ao FDR**; o menor p ajustado é 0,153.

As seis células com p nominal < 0,05:

| code smell | test smell | N | rho | p | p ajustado | r detectável |
|---|---|---:|---:|---:|---:|---:|
| feature envy | Verbose Test | 426 | 0,149 | 0,002 | 0,153 | 0,135 |
| blob | Duplicate Assert | 306 | 0,162 | 0,004 | 0,165 | 0,160 |
| long method | Magic Number Test | 429 | 0,126 | 0,009 | 0,228 | 0,135 |
| long method | Verbose Test | 429 | 0,121 | 0,012 | 0,233 | 0,135 |
| data class | Eager Test | 291 | 0,131 | 0,025 | 0,383 | 0,164 |
| data class | Lazy Test | 291 | 0,123 | 0,035 | 0,449 | 0,164 |

Com 76 testes e α = 0,05, o acaso sozinho produziria ~3,8 significâncias nominais. Seis é
mais que isso, e nenhuma resiste ao ajuste.

O N de cada code smell limita o que a linha enxerga:

| code smell | N | r detectável |
|---|---:|---:|
| long method | 429 | 0,135 |
| feature envy | 426 | 0,135 |
| blob | 306 | 0,160 |
| data class | 306 | 0,160 |

Eager e Lazy Test perdem as linhas `nome_divergente` e ficam com N menor (291 a 395, r
detectável 0,141 a 0,164).

## O filtro quase não mudou nada

| | sem filtro | com filtro |
|---|---:|---:|
| data class × Eager Test | 0,127 (N = 306) | 0,131 (N = 291) |
| data class × Lazy Test | 0,119 (N = 306) | 0,123 (N = 291) |

Nas oito células a diferença fica abaixo de 0,02.

Uma segunda sensibilidade restringe Eager e Lazy aos arquivos ligados só por
`caminho_exato`, onde a classe que o JNose usa para medi-los é a mesma que o MLCQ rotulou
(`comum.so_caminho_exato`; ver a análise 02). Nas oito células, a diferença para a família
fica abaixo de 0,01:

| | família | só `caminho_exato` |
|---|---:|---:|
| data class × Eager Test | 0,131 (N = 291) | 0,138 (N = 280) |
| data class × Lazy Test | 0,123 (N = 291) | 0,119 (N = 280) |

## A leitura

**Não dá para afirmar associação em nenhum par.** Nenhuma célula sobrevive ao ajuste para
76 comparações.

**Duas células merecem registro, e só isso.** Feature envy × Verbose Test (0,149) e blob ×
Duplicate Assert (0,162) passam do r detectável da sua linha, com p ajustado de 0,153 e
0,165. Estar acima do detectável não é critério de significância: diz só que, se o efeito
for desse tamanho, o desenho tem poder para vê-lo. Numa exploração com 76 testes, são
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
| `dados/cruzado.csv` | 96 linhas: as 80 células da grade (`recorte = principal`; as 4 do Default Test com p = nan), 8 sem o filtro (`sensibilidade_sem_filtro`) e 8 só `caminho_exato` (`sensibilidade_caminho_exato`), com rho, p, p ajustado, IC e r detectável |
