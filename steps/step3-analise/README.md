# Step 3 — Análise

Responde se existe relação entre **test smell** (no teste) e **code smell** (na classe de
produção), usando as duas tabelas que o step 2 entregou.

**Este step é exploratório.** Avançar por um caminho, olhar o resultado e voltar para pegar
outro é esperado — o que precisa existir é a justificativa de cada decisão e o registro do
que foi percorrido. O mapa das opções está na seção 12 do README do step 2; o caderno de
tentativas está na seção 4 daqui.

Entrada: `steps/step2-binding/dados/analise_deterministico.csv` e `analise_ampliado.csv`
Saída: `analises/*/dados/`

---

## 1. As análises

Cada análise tem pasta própria, com o script, os dados que ele produz e um README que
explica a pergunta, o resultado e a leitura. **Este arquivo é só o índice.**

| # | pergunta | resposta | documento |
|---|---|---|---|
| **00** | que forma têm as variáveis, e que teste elas permitem? | paramétrico descartado; tamanho do teste é confundidor | [caracterização](analises/00-caracterizacao/) |
| **01** | test smell correlaciona com code smell? | a associação aparente é **tamanho do teste**; isolando qualidade, r = 0,047 (IC até 0,120) | [correlação agregada](analises/01-correlacao-agregada/) |
| **02** | algum dos 13 smells se comporta diferente? | nenhum sobrevive ao FDR; Eager e Lazy, os melhores candidatos, são os mais próximos de zero | [por test smell](analises/02-por-test-smell/) |
| **03** | classes com code smell confirmado têm testes piores? | não; o grupo negativo tem densidade ligeiramente maior | [extremos](analises/03-extremos/) |
| **04** | entre as sinalizadas, o test smell prediz quais a maioria confirmou? | **inconclusiva** — poder insuficiente, não nulo | [disputados](analises/04-disputados/) |

### O que o conjunto diz

Três operacionalizações independentes (01, 02, 03) deram nulo. A quarta (04) tem o melhor
desenho e o pior poder, e não decide.

O acúmulo importa: um nulo pode ser operacionalização infeliz; três nulos por caminhos
diferentes apontam para o mesmo lugar. Com a precisão do binding medida (94,2%) e o poder
calculado, **a leitura é que, nestes dados, densidade de test smell e severidade de code
smell não têm relação detectável** — com o limite superior quantificado em r ≈ 0,12.

Isso não é o mesmo que "não existe relação no mundo". As ressalvas da seção 6 limitam o
alcance, em especial o fato de que o MLCQ anota **percepção de revisor**, não defeito
observado.

### O achado que não é nulo

A análise 01 mediu um confundidor que vale por si: **contagem de test smell correlaciona
0,554 com o tamanho do teste**, e code smell correlaciona 0,079–0,091 com o mesmo tamanho.
Isso basta para produzir uma correlação espúria de 0,092 entre os dois.

Estudos que contam ocorrências de test smell sem normalizar por tamanho estão medindo
tamanho. É um resultado metodológico, e é reprodutível em qualquer dataset que use contagem
bruta.

---

## 2. Estrutura

```
step3-analise/
├── README.md                   este indice
├── tools/                      codigo compartilhado por todas as analises
│   ├── comum.py                caminhos, leitura das tabelas do step 2, precisao de cada ramo
│   ├── variaveis.py            as definicoes de desfecho e rotulo, iguais para todos
│   ├── estat.py                Spearman, Mann-Whitney, IC de Fisher, parcial, FDR
│   └── conferir_resultados.py  reapura todo numero afirmado nos READMEs
└── analises/
    ├── 00-caracterizacao/      README.md + caracterizar.py + dados/
    ├── 01-correlacao-agregada/ README.md + explorar.py + dados/
    ├── 02-por-test-smell/      README.md + por_test_smell.py + dados/
    ├── 03-extremos/            README.md + extremos.py + dados/
    └── 04-disputados/          README.md + disputados.py + dados/
```

**Por que `variaveis.py` mora em `tools/` e não dentro de uma análise.** As definições de
"densidade de test smell" e "rótulo agregado" são vocabulário, não método: se cada análise
definisse a sua, os resultados não seriam comparáveis entre si — e comparar
operacionalizações é justamente o ponto deste step. Mudar algo ali muda todas as análises,
de propósito.

`comum.py` carrega o `comum.py` do step 2 por caminho para reusar a lista dos 13 smells,
em vez de manter uma cópia que pode divergir — mesmo padrão que o step 2 usa com o step 1.

---

## 3. Ambiente

| Componente | Versão |
|---|---|
| Python | 3.12.10, biblioteca padrão apenas |

Nenhuma dependência externa: Spearman, Mann-Whitney com correção de empates, intervalo por
z de Fisher, correlação parcial e Benjamini-Hochberg estão implementados em `estat.py`.
Decisão consciente — evita que reproduzir o step exija montar ambiente, e mantém cada
fórmula visível no fonte em vez de escondida numa chamada de biblioteca. Se a análise
exigir modelo mais pesado (regressão com excesso de zeros), a dependência entra aí,
declarada.

As fórmulas usam aproximação normal, adequada para os N deste step (730 e 1.369). Com N
muito pequeno a aproximação pioraria; os scripts recusam grupo menor que 5 e correlação com
menos de 10 pares.

---

## 4. Caderno de tentativas

Uma linha por análise rodada, **incluindo as que não deram em nada**. Serve para o artigo
poder dizer quantos caminhos foram percorridos, com número em vez de estimativa (step 2,
seção 12.0).

| # | data | análise | testes | resultado |
|---|---|---|---:|---|
| 1–40 | 18/09 | 01 — correlação agregada | 40 | 4 significâncias nominais, todas em desfecho sensível a tamanho; sem ajuste |
| 41–92 | 18/09 | 02 — por test smell | 52 | nenhum sobrevive ao FDR (menor p ajustado 0,283) |
| 93–98 | 18/09 | 03 — extremos | 6 | nenhum p < 0,05 |
| 99–104 | 18/09 | 04 — disputados | 6 | nenhum p < 0,05, e todos abaixo do detectável |

**104 testes rodados no total.** Os 40 da primeira análise saíram sem ajuste e estão
reportados assim; os 64 seguintes já saem com p ajustado por Benjamini-Hochberg dentro de
cada família. Quando a exploração fechar, o artigo reporta o total e declara o regime como
exploratório — é o que o volume exige.

> **Este número já foi corrigido uma vez.** A primeira versão dizia "22 testes, 3
> significâncias", contando só a rodada em que `--por-smell` tinha sido usado num ramo só.
> O `conferir_resultados.py` acusou a divergência quando a rodada completa foi gravada. É
> exatamente o erro que o caderno existe para impedir: subcontar tentativas sem perceber.

---

## 5. Reproduzir do zero

O step 3 não recoleta nada: lê as duas tabelas do step 2. Se elas não existirem,
`gerar_analises.py` as refaz em segundos.

```bash
cd steps/step3-analise

(cd analises/00-caracterizacao      && python caracterizar.py --csv)
(cd analises/01-correlacao-agregada && python explorar.py --por-smell --csv)
(cd analises/02-por-test-smell      && python por_test_smell.py --csv)
(cd analises/03-extremos            && python extremos.py --csv)
(cd analises/04-disputados          && python disputados.py --csv)

python tools/conferir_resultados.py
```

Todos levam segundos, nenhum depende de rede. `conferir_resultados.py` reapura cada número
afirmado nos READMEs e falha com código 1 se algum divergir — rodá-lo sem ter rodado as
análises acusa divergência, que foi o que aconteceu ao montar o caderno.

---

## 6. Ressalvas herdadas

Documentadas no step 2 e no `NOTAS-METODOLOGICAS.md`, repetidas porque afetam a
interpretação de qualquer resultado deste step:

- **Precisão do binding**: 94,2% no ramo determinístico. Os ~6% de pares falsos atenuam a
  correlação medida.
- **O ramo ampliado responde outra pergunta**: 10,1% de precisão para "este teste testa
  esta classe", 94,8% para "este teste exercita esta classe".
- **`sev_media` não é imune ao desenho amostral do MLCQ**: a média segue condicionada ao
  roteamento do crosscheck. A análise 04 é a única que neutraliza isso — e é a que não tem
  poder.
- **O MLCQ anota percepção de revisor**, não defeito observado. Um nulo aqui é sobre
  percepção de code smell, não sobre defeito.
- **Recall do binding não foi medido.**
- **A auditoria dos 293 pares é automatizada**, não humana.
