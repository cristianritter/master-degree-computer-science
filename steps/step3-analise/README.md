# Step 3 — Análise

Responde se existe relação entre **test smell** (no teste) e **code smell** (na classe de
produção), usando as duas tabelas que o step 2 entregou.

**Este step é exploratório.** Avançar por um caminho, olhar o resultado e voltar para pegar
outro é esperado — o que precisa existir é a justificativa de cada decisão e o registro do
que foi percorrido. O mapa das opções está na seção 12 do README do step 2; o caderno das
tentativas está na seção 4 daqui.

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
│   └── caracterizar.py    distribuicoes, antes de qualquer teste
└── dados/
    └── caracterizacao.csv  as estatisticas descritivas, para conferencia
```

`comum.py` carrega o `comum.py` do step 2 por caminho para reusar a lista dos 13 smells,
em vez de manter uma cópia que pode divergir — mesmo padrão que o step 2 usa com o step 1.

---

## 4. Caderno de tentativas

Uma linha por análise rodada, **incluindo as que não deram em nada**. Serve para o artigo
poder dizer quantos caminhos foram percorridos, com número em vez de estimativa (step 2,
seção 12.0).

| # | data | ramo | rótulo | desfecho | recorte | resultado |
|---|---|---|---|---|---|---|
| — | 18/09/2026 | — | — | — | — | caracterização; nenhum teste rodado ainda |

---

## 5. Ressalvas herdadas

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
