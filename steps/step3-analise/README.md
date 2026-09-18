# Step 3 — Análise

Responde se existe relação entre **test smell** (no teste) e **code smell** (na classe de
produção), usando as duas tabelas que o step 2 entregou.

**Este step é exploratório.** Avançar por um caminho, olhar o resultado e voltar para pegar
outro é esperado — o que precisa existir é a justificativa de cada decisão e o registro do
que foi percorrido. O mapa das opções está na seção 12 do README do step 2; o caderno das
tentativas está na seção 6 daqui.

Entrada: `steps/step2-binding/dados/analise_deterministico.csv` e `analise_ampliado.csv`
Saída: `dados/`

---

## 1. Ambiente

| Componente | Versão |
|---|---|
| Python | 3.12.10, biblioteca padrão apenas |

Nenhuma dependência externa até aqui: as estatísticas descritivas e os testes são
implementados no próprio código, sem `numpy`/`scipy`. Isso é decisão consciente — evita que
reproduzir o step exija montar ambiente, e mantém cada fórmula visível no fonte em vez de
escondida numa chamada de biblioteca. Se a análise exigir modelo mais pesado (regressão com
excesso de zeros, por exemplo), a dependência entra aí, declarada.

---

## 2. O que existe antes de qualquer teste

`caracterizar.py` roda antes de tudo, e existe pelo mesmo motivo que a auditoria do step 2:
escolher o teste estatístico sem olhar a distribuição é assumir o que devia ser conferido.

```bash
python tools/caracterizar.py                    # os dois ramos
python tools/caracterizar.py --ramo deterministico --csv
```

### 2.1 As duas variáveis são fortemente assimétricas

Ramo determinístico, 730 arquivos:

| variável | zeros | mediana | p95 | máx | assimetria |
|---|---:|---:|---:|---:|---:|
| code smell agregado (`sev_media`) | 72,1% | 0,00 | 1,17 | 2,17 | 2,14 |
| `blob` | 66,3% | 0,00 | 1,04 | 1,62 | 1,61 |
| `feature envy` | 79,0% | 0,00 | 0,50 | 1,50 | 3,36 |
| Assertion Roulette | 32,6% | 4 | 77 | 533 | 6,02 |
| Lazy Test | 42,9% | 1 | 21 | **1.116** | **21,28** |
| Exception Catching Throwing | 72,1% | 0 | 11 | 213 | 16,00 |
| `ts_n_total` | 8,5% | 15 | 209 | 1.552 | 6,62 |

**Consequência direta: teste paramétrico está descartado.** Com 72% de zeros no rótulo e
assimetria de 21 numa das variáveis de desfecho, média e desvio-padrão não descrevem esses
dados. O que cabe é **Spearman** (correlação de postos) ou um modelo que trate explicitamente
o excesso de zeros. Não é uma escolha de gosto — é o que a distribuição permite.

O caso do Lazy Test com máximo 1.116 merece atenção própria: um único arquivo pode dominar
qualquer correlação não-robusta. Postos resolvem isso; média não.

### 2.2 O tamanho do teste é confundidor óbvio, e não está controlado

| | mediana | p95 | máx |
|---|---:|---:|---:|
| LOC de teste (determinístico) | 181 | 1.323 | 4.668 |
| LOC de teste (ampliado) | 426 | 4.969 | **39.546** |
| métodos de teste (determinístico) | 9 | 61 | 297 |

As tabelas do step 2 saíram com `--agregacao soma`: `ts_assertion_roulette = 77` significa
77 ocorrências somadas. Um arquivo de teste com 4.668 linhas tem mais ocorrências de tudo
que um de 50 linhas, independentemente de qualidade.

**Sem normalizar, a análise mede tamanho de teste, não qualidade de teste.** Três saídas,
nenhuma ainda escolhida:

1. `--agregacao densidade` no step 2, que divide pelo número de métodos de teste;
2. manter a soma e usar `n_metodos_teste` como covariável/controle;
3. usar `ts_n_distintos` (quantos dos 13 smells aparecem), que é menos sensível a tamanho.

A opção 3 tem um atrativo: é a única variável de desfecho **não patológica** — assimetria
0,90 no ramo determinístico, contra 6 a 21 das contagens.

### 2.3 Contaminação e estratos

| | determinístico | ampliado |
|---|---:|---:|
| arquivos com teste `nome_divergente` | 53 (7,3%) | 254 (18,6%) |
| `negativo_confiavel` | 72,6% | 72,4% |
| `disputado` | 21,9% | 22,3% |
| `positivo_confiavel` | 6,0% | 5,8% |
| `negativo_1_review` | 0,4% | 0,7% |

Análise que envolva **Eager Test** ou **Lazy Test** tem que filtrar ou estratificar por
`n_testes_nome_divergente` — no ramo ampliado isso custa 18,6% das linhas. General Fixture
não é afetado e serve como controle (step 1, seção 5).

A distribuição de estratos é praticamente idêntica nos dois ramos, o que é mais uma
evidência de que o binding não desloca o rótulo.

### 2.4 Um defeito encontrado aqui e corrigido no step 2

A caracterização mostrou `ts_n_distintos = 19` num arquivo — impossível, já que só existem
13 smells habilitados. A coluna estava **somando** a contagem de distintos de cada classe de
teste em vez de unir os conjuntos. O valor correto daquele arquivo era 10.

Corrigido em `montar_analise.py`: `ts_n_distintos` passa a ser a união (quantos dos 13
smells aparecem em ao menos uma classe ligada) e não depende mais de `--agregacao`. Os
máximos voltaram para dentro do possível — 12 no determinístico, 13 no ampliado.

> Vale registrar como o defeito apareceu: não por revisão de código, mas por olhar a
> distribuição de uma variável antes de usá-la. É o mesmo padrão da seção 4 do step 2, em
> que a discordância entre README e implementação apareceu ao montar a auditoria.

---

## 3. Estrutura

```
step3-analise/
├── README.md
├── tools/
│   ├── comum.py               caminhos, leitura das tabelas do step 2, precisao de cada ramo
│   ├── estat.py               Spearman, IC por z de Fisher e parcial, sem scipy
│   ├── caracterizar.py        distribuicoes, antes de qualquer teste
│   ├── explorar.py            rodada 1: test smell x code smell, tres desfechos
│   ├── por_test_smell.py      rodada 2a: cada um dos 13 smells isolado, com FDR
│   ├── extremos.py            rodada 2b: Mann-Whitney entre estratos extremos
│   └── conferir_resultados.py reapura todo numero deste README
└── dados/
    ├── caracterizacao.csv     as estatisticas descritivas
    ├── exploracao.csv         rodada 1, um resultado por linha
    ├── por_test_smell.csv     rodada 2a, 52 resultados com p ajustado
    └── extremos.csv           rodada 2b, 6 resultados com p ajustado
```

`comum.py` carrega o `comum.py` do step 2 por caminho para reusar a lista dos 13 smells,
em vez de manter uma cópia que pode divergir — mesmo padrão que o step 2 usa com o step 1.

---

## 4. Primeira rodada — o tamanho do teste explica a associação aparente

```bash
python tools/explorar.py --ramo deterministico --por-smell --csv
```

Spearman sobre postos, IC95% por z de Fisher. Rótulo `sev_media` contínuo, agregado.

### 4.1 O resultado

Ramo determinístico, 730 arquivos, code smell agregado:

| desfecho | N | rho | p | IC95% | rho com o tamanho do teste |
|---|---:|---:|---:|---|---:|
| `bruto` (soma das ocorrências) | 730 | 0,092 | 0,012 | [0,020, 0,164] | **0,554** |
| `densidade` (soma / métodos) | 726 | 0,047 | 0,204 | [−0,026, 0,120] | −0,077 |
| `distintos` (quantos dos 13) | 730 | 0,084 | 0,024 | [0,011, 0,155] | **0,433** |

| controlando `n_metodos_teste` | N | rho parcial | p |
|---|---:|---:|---:|
| `bruto` | 730 | 0,058 | 0,115 |
| `distintos` | 730 | 0,055 | 0,140 |

**Leitura: a associação que aparece na contagem bruta é efeito do tamanho do teste.** Os
dois desfechos que dependem de tamanho (`bruto` e `distintos`) dão significância nominal; o
desfecho normalizado por tamanho (`densidade`) não dá. Quando o tamanho é controlado
explicitamente, os dois caem para ~0,056 e deixam de ser significativos.

### 4.2 O mecanismo, medido

A confusão não é hipótese — as três pernas do triângulo estão medidas:

| par | rho |
|---|---:|
| test smell bruto × tamanho do teste | 0,554 |
| code smell × tamanho do teste (`n_metodos_teste`) | 0,079 (p = 0,032) |
| code smell × tamanho do teste (`loc_teste`) | 0,091 (p = 0,014) |

Classe de produção com mais code smell tende a ter teste maior; teste maior tem mais
ocorrências de tudo. O produto dessas duas relações gera a correlação bruta de 0,092 sem
que exista relação entre *qualidade* do teste e code smell.

### 4.3 O ramo ampliado

| desfecho | N | rho | p |
|---|---:|---:|---:|
| `bruto` | 1.369 | 0,015 | 0,568 |
| `densidade` | 1.365 | 0,003 | 0,915 |
| `distintos` | 1.369 | 0,001 | 0,973 |

Tudo em zero. É o esperado: com 10,1% de precisão para o construto "o teste testa esta
classe", a atenuação por erro de medida (`NOTAS-METODOLOGICAS.md`, seção 2) leva qualquer
relação verdadeira para perto de zero. O ramo ampliado **não contradiz** o determinístico —
ele não tem como discordar dele.

### 4.4 Por code smell individual

**Ramo determinístico.** Só `blob`/`bruto` alcança p < 0,05, e a versão em densidade do
mesmo smell é −0,005:

| smell | N | bruto | densidade | distintos |
|---|---:|---:|---:|---:|
| blob | 196 | **0,148 (p=0,038)** | −0,005 (p=0,948) | 0,100 (p=0,163) |
| data class | 114 | 0,124 (p=0,189) | 0,096 (p=0,313) | 0,174 (p=0,063) |
| feature envy | 186 | 0,069 (p=0,351) | 0,070 (p=0,343) | 0,094 (p=0,201) |
| long method | 251 | 0,117 (p=0,063) | 0,082 (p=0,199) | 0,088 (p=0,167) |

**Ramo ampliado.** Aparece a única significância fora do ramo determinístico —
`blob`/`distintos`, rho = 0,121 (p = 0,018). Ela segue exatamente o mesmo padrão: `rho` com
o tamanho do teste é 0,560, e a versão em densidade do mesmo par dá −0,058 (p = 0,259).

Mesmo padrão em tudo: **o que alcança significância é sempre o desfecho sensível a
tamanho, e sempre some quando o tamanho é normalizado.**

### 4.5 O que dá para afirmar, e o que não dá

**Não dá para afirmar que existe relação.** O único desfecho que isola qualidade de tamanho
— densidade — dá rho = 0,047 com IC [−0,026, 0,120], que inclui o zero.

**Dá para afirmar que, se existe, ela é pequena.** E isso é mais forte que um nulo comum,
por duas razões que vêm do step 2:

- *A precisão do binding está medida em 94,2%*, então o nulo não é explicável por ruído de
  ligação. Se fosse 50%, seria.
- *O poder está calculado*: este desenho detecta r ≥ 0,104 com 80% de poder. O limite
  superior do IC da densidade é 0,120.

Juntando: **qualquer associação entre densidade de test smell e severidade de code smell,
em classes com teste dedicado, é menor que r ≈ 0,12.** Isso é um achado com número, não um
"não encontramos nada".

**O que fica em aberto.** A relação pode existir sob outra operacionalização — outro
rótulo, outro recorte de smell, outra forma de agregar. É o que as próximas rodadas
exploram, e o caderno abaixo registra o que já foi tentado.

---

## 5. Segunda rodada — smells individuais e extremos de evidência

Duas hipóteses que a primeira rodada não testou, atacadas com o ajuste para comparações
múltiplas já embutido.

```bash
python tools/por_test_smell.py --csv     # analise 1
python tools/extremos.py --csv           # analise 2
```

### 5.1 Análise 1 — cada test smell isolado

Até aqui o desfecho foi sempre agregado. A pergunta agora é se **algum smell específico se
comporta diferente do conjunto** — plausível, porque Eager Test e Lazy Test dependem da
classe de produção para serem detectados, enquanto Assertion Roulette e Verbose Test são
propriedades internas do teste. Se existisse relação com code smell, os primeiros eram os
candidatos naturais.

52 testes (13 smells × bruto/densidade × com/sem o filtro de `nome_divergente`), ramo
determinístico, contra o code smell agregado. **Nenhum sobrevive à correção FDR** — o menor
p ajustado é 0,283.

Os cinco que alcançam significância nominal:

| test smell | desfecho | rho | p | p ajustado |
|---|---|---:|---:|---:|
| Magic Number Test | bruto | 0,087 | 0,019 | 0,283 |
| Assertion Roulette | bruto | 0,078 | 0,035 | 0,283 |
| Verbose Test | bruto | 0,077 | 0,037 | 0,283 |
| Magic Number Test | densidade | 0,074 | 0,046 | 0,283 |
| Magic Number Test | bruto, filtrado | 0,085 | 0,027 | 0,380 |

**O achado com mais conteúdo aqui é negativo, e é interessante.** Os dois smells que
*deveriam* ser os melhores candidatos — Eager Test e Lazy Test, os únicos que dependem da
classe de produção para serem detectados — dão rho de −0,020 e 0,038 em densidade. São os
mais próximos de zero da tabela inteira.

E o filtro de `nome_divergente` funciona como esperado, o que valida o controle do step 1:

| smell | densidade, todas as linhas | sem `nome_divergente` |
|---|---:|---:|
| Eager Test | −0,020 (N=726) | −0,028 (N=677) |
| Lazy Test | 0,038 (N=726) | 0,031 (N=677) |
| **General Fixture** (controle) | 0,008 (N=726) | 0,013 (N=677) |

General Fixture não depende da classe de produção e não deveria mudar com o filtro — não
muda. O controle se comporta como previsto.

### 5.2 Análise 2 — extremos de evidência, por Mann-Whitney

A correlação pressupõe relação monotônica ao longo de toda a faixa. O desenho do MLCQ
sustenta melhor uma comparação de extremos, usando os estratos que o step 2 definiu:
classes em que a **maioria dos revisores concordou** que há code smell contra classes em
que **2+ revisores concordaram que não há**.

O estrato negativo é especialmente forte aqui: pelo desenho amostral, qualquer sinalização
teria escalado a amostra para mais revisores, então são negativos com corroboração.

Ramo determinístico — 42 positivos, 523 negativos, 165 fora (arquivo com amostras de mais
de um estrato, ou de estrato intermediário):

| desfecho | mediana positivos | mediana negativos | delta | p | p ajustado |
|---|---:|---:|---:|---:|---:|
| bruto | 18,0 | 14,0 | 0,113 | 0,223 | 0,334 |
| densidade | 1,552 | 1,609 | 0,032 | 0,736 | 0,736 |
| distintos | 5,0 | 4,0 | 0,154 | 0,094 | 0,282 |

Ramo ampliado — 76 positivos, 976 negativos:

| desfecho | mediana positivos | mediana negativos | delta | p | p ajustado |
|---|---:|---:|---:|---:|---:|
| bruto | 46,0 | 27,0 | 0,084 | 0,222 | 0,667 |
| densidade | 1,506 | 1,543 | 0,029 | 0,673 | 0,673 |
| distintos | 5,0 | 5,0 | 0,039 | 0,571 | 0,673 |

**Nenhum resultado significativo, nem antes nem depois do ajuste.** E o detalhe mais
eloquente está nas medianas de densidade: 1,552 contra 1,609 no determinístico, 1,506
contra 1,543 no ampliado. Nos dois ramos o grupo **negativo** tem densidade de test smell
ligeiramente *maior* — diferença sem significância, mas que mostra ausência de separação,
não uma tendência fraca na direção esperada.

### 5.3 O que as duas rodadas somam

Três operacionalizações independentes da mesma hipótese, todas nulas:

| rodada | pergunta | resultado |
|---|---|---|
| 1 | densidade de test smell correlaciona com severidade de code smell? | rho 0,047, IC [−0,026, 0,120] |
| 2a | algum test smell específico correlaciona? | nenhum sobrevive ao FDR (mín. 0,283) |
| 2b | classes com code smell confirmado têm testes mais smelly? | delta ≤ 0,154, nenhum p < 0,05 |

O acúmulo importa: um nulo pode ser operacionalização infeliz, três nulos por caminhos
diferentes apontam para o mesmo lugar. Com a precisão do binding medida (94,2%) e o poder
calculado, **a leitura é que, nestes dados, densidade de test smell e severidade de code
smell não têm relação detectável.**

Isso não é o mesmo que "não existe relação no mundo" — as ressalvas da seção 8 limitam o
alcance, em especial o fato de que o MLCQ anota *percepção de revisor*, não defeito
observado.
---

## 6. Caderno de tentativas

Uma linha por análise rodada, **incluindo as que não deram em nada**. Serve para o artigo
poder dizer quantos caminhos foram percorridos, com número em vez de estimativa (step 2,
seção 12.0).

A tabela abaixo é resumo; o registro completo, um resultado por linha, está em
`dados/exploracao.csv` e é regenerado por `explorar.py --por-smell --csv`.

| # | data | ramo | rótulo | desfecho | recorte | resultado |
|---|---|---|---|---|---|---|
| 1 | 18/09 | determinístico | `sev_media` | bruto | agregado | rho 0,092 (p=0,012) — confundido por tamanho |
| 2 | 18/09 | determinístico | `sev_media` | densidade | agregado | rho 0,047 (p=0,204) — **nulo** |
| 3 | 18/09 | determinístico | `sev_media` | distintos | agregado | rho 0,084 (p=0,024) — confundido por tamanho |
| 4–6 | 18/09 | determinístico | `sev_media` | os três, parciais | agregado | 0,058 / 0,047 / 0,055 — nenhum p < 0,05 |
| 7–9 | 18/09 | ampliado | `sev_media` | os três | agregado | tudo ~0, p > 0,5 |
| 10–12 | 18/09 | ampliado | `sev_media` | os três, parciais | agregado | ~0 |
| 13–24 | 18/09 | determinístico | `sev_media` | os três | por smell (4) | só blob/bruto p<0,05 |
| 25–36 | 18/09 | ampliado | `sev_media` | os três | por smell (4) | só blob/distintos p<0,05 |
| 37–40 | 18/09 | ambos | `sev_media` | code smell × tamanho | agregado | o confundidor: 0,079 e 0,091 no determinístico |

**40 testes rodados.** Com α = 0,05, esperavam-se ~2 falsos positivos por acaso; apareceram
**4 significâncias nominais**, todas em desfecho sensível a tamanho e todas desaparecendo
quando o tamanho é normalizado ou controlado:

| ramo | recorte | desfecho | rho | p | rho com tamanho | versão em densidade |
|---|---|---|---:|---:|---:|---|
| determinístico | agregado | bruto | 0,092 | 0,012 | 0,554 | 0,047 (p=0,204) |
| determinístico | agregado | distintos | 0,084 | 0,024 | 0,433 | 0,047 (p=0,204) |
| determinístico | blob | bruto | 0,148 | 0,038 | 0,561 | −0,005 (p=0,948) |
| ampliado | blob | distintos | 0,121 | 0,018 | 0,560 | −0,058 (p=0,259) |

| 41–92 | 18/09 | determinístico | `sev_media` | cada test smell, bruto e densidade | agregado, com e sem filtro | 52 testes, **nenhum sobrevive ao FDR** |
| 93–98 | 18/09 | ambos | estrato | os três, Mann-Whitney | extremos | 6 testes, nenhum p < 0,05 |

**98 testes rodados no total.** Os 40 da primeira rodada saíram sem ajuste (e estão
reportados assim); os 58 da segunda já saem com p ajustado por Benjamini-Hochberg dentro de
cada família. Quando a exploração fechar, o artigo reporta o total e declara o regime como
exploratório — é o que o volume de testes exige.

> **Este número já foi corrigido uma vez.** A primeira versão desta seção dizia "22 testes,
> 3 significâncias", contando só a rodada em que `--por-smell` tinha sido usado num ramo só.
> O `conferir_resultados.py` acusou a divergência quando a rodada completa foi gravada. É
> exatamente o erro que o caderno existe para impedir: subcontar tentativas sem perceber.

---

## 7. Reproduzir do zero

O step 3 não recoleta nada: ele lê as duas tabelas do step 2. Se elas não existirem,
`gerar_analises.py` as refaz em segundos.

```bash
cd steps/step3-analise

# 1. as distribuicoes, antes de qualquer teste
python tools/caracterizar.py --csv

# 2. a rodada exploratoria completa: 2 ramos, 5 recortes, 3 desfechos, parciais
python tools/explorar.py --por-smell --csv

# 3. rodada 2a: cada test smell isolado, com correcao para comparacoes multiplas
python tools/por_test_smell.py --csv

# 4. rodada 2b: extremos de evidencia, Mann-Whitney
python tools/extremos.py --csv

# 5. conferir que todo numero do README ainda sai do dado
python tools/conferir_resultados.py
```

Os cinco levam segundos. Nenhum depende de rede, de clone ou do JNose — só dos dois CSVs
do step 2, cujos sha256 estão gravados nos `.params.txt` que os acompanham.

**A ordem importa.** `explorar.py --csv` reescreve `exploracao.csv`, e
`conferir_resultados.py` compara o README contra ele: rodar o verificador sem ter rodado a
exploração completa acusa divergência — que foi exatamente o que aconteceu ao montar esta
seção, e está registrado na seção 6.

---

## 8. Ressalvas herdadas

Todas já documentadas no step 2 e no `NOTAS-METODOLOGICAS.md`, repetidas aqui porque
afetam a interpretação de qualquer resultado deste step:

- **Precisão do binding**: 94,2% no ramo determinístico. Os ~6% de pares falsos atenuam a
  correlação medida — se o resultado for nulo, isso precisa entrar na discussão.
- **O ramo ampliado responde outra pergunta**: 10,1% de precisão para "este teste testa
  esta classe", 94,8% para "este teste exercita esta classe".
- **`sev_media` não é imune ao desenho amostral do MLCQ**: a média segue condicionada ao
  roteamento do crosscheck. Comparar dentro de `estrato` mitiga.
- **Recall do binding não foi medido.**
- **A auditoria dos 293 pares é automatizada**, não humana.
