# Step 3 — Análise

Responde se existe relação entre **test smell** (no teste) e **code smell** (na classe de
produção), usando as duas tabelas que o step 2 entregou.

**Este step é exploratório.** Avançar por um caminho, olhar o resultado e voltar para pegar
outro é esperado — o que precisa existir é a justificativa de cada decisão e o registro do
que foi percorrido. O mapa das opções está na seção 12 do README do step 2; o caderno das
tentativas está na seção 5 daqui.

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
│   ├── comum.py           caminhos, leitura das tabelas do step 2, precisao de cada ramo
│   ├── estat.py           Spearman, IC por z de Fisher e correlacao parcial, sem scipy
│   ├── caracterizar.py    distribuicoes, antes de qualquer teste
│   └── explorar.py        test smell x code smell, nas tres definicoes de desfecho
└── dados/
    ├── caracterizacao.csv  as estatisticas descritivas, para conferencia
    └── exploracao.csv      um resultado por linha, para o caderno da secao 5
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

Ramo determinístico. Só `blob`/`bruto` alcança p < 0,05, e a versão em densidade do mesmo
smell é −0,005:

| smell | N | bruto | densidade | distintos |
|---|---:|---:|---:|---:|
| blob | 196 | 0,148 (p=0,038) | −0,005 (p=0,948) | 0,100 (p=0,163) |
| data class | 114 | 0,124 (p=0,189) | 0,096 (p=0,313) | 0,174 (p=0,063) |
| feature envy | 186 | 0,069 (p=0,351) | 0,070 (p=0,343) | 0,094 (p=0,201) |
| long method | 251 | 0,117 (p=0,063) | 0,082 (p=0,199) | 0,088 (p=0,167) |

Mesmo padrão: o que sobrevive é sempre o desfecho sensível a tamanho.

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

## 5. Caderno de tentativas

Uma linha por análise rodada, **incluindo as que não deram em nada**. Serve para o artigo
poder dizer quantos caminhos foram percorridos, com número em vez de estimativa (step 2,
seção 12.0).

| # | data | ramo | rótulo | desfecho | recorte | resultado |
|---|---|---|---|---|---|---|
| 1 | 18/09 | determinístico | `sev_media` | bruto | agregado | rho 0,092 (p=0,012) — confundido por tamanho |
| 2 | 18/09 | determinístico | `sev_media` | densidade | agregado | rho 0,047 (p=0,204) — **nulo** |
| 3 | 18/09 | determinístico | `sev_media` | distintos | agregado | rho 0,084 (p=0,024) — confundido por tamanho |
| 4 | 18/09 | determinístico | `sev_media` | bruto, parcial | agregado | rho 0,058 (p=0,115) |
| 5 | 18/09 | determinístico | `sev_media` | distintos, parcial | agregado | rho 0,055 (p=0,140) |
| 6–8 | 18/09 | ampliado | `sev_media` | os três | agregado | tudo ~0, p > 0,5 |
| 9–10 | 18/09 | ampliado | `sev_media` | parciais | agregado | ~0 |
| 11–22 | 18/09 | determinístico | `sev_media` | os três | por smell (4) | só blob/bruto p<0,05 |

**22 testes rodados.** Com α = 0,05, esperava-se ~1 falso positivo por acaso; apareceram 3
significâncias nominais, todas no mesmo padrão (desfecho sensível a tamanho) e todas
desaparecendo sob controle de tamanho. Nenhum ajuste para comparações múltiplas foi
aplicado ainda — quando a exploração fechar, o artigo reporta o total e aplica correção, ou
declara o regime como exploratório.

---

## 6. Ressalvas herdadas

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
