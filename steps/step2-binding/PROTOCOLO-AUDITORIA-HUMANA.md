# Protocolo da auditoria humana do binding — 17/10/2026

Registrado **antes de qualquer par ser julgado por humano**. O que está aqui não muda
depois de ver os vereditos; se algo precisar mudar, a mudança entra como seção nova, datada,
sem apagar esta.

## Por que existe

A auditoria da seção 5 do `README.md` (293 pares, 6 estratos) foi julgamento automatizado
(`dados/auditoria_binding_auto.csv`). O artigo trata a precisão do binding como validação do
instrumento e apresenta a diferença entre "exercita" (94,8%) e "testa" (10,1%) como
contribuição. As duas afirmações passam a ser sustentadas por julgamento humano:

- **censo**: o avaliador 1 julga os 293 pares. A precisão reportada é a humana;
- **concordância entre humanos**: o avaliador 2 julga uma subamostra de 48 pares;
- o julgamento automatizado vira segunda leitura, com concordância calculada sobre os 293.

## Materiais

| arquivo | quem usa | conteúdo |
|---|---|---|
| `dados/auditoria_humana_avaliador1.csv` | avaliador 1 | os 293 pares |
| `dados/auditoria_humana_avaliador2.csv` | avaliador 2 | 48 pares: 8 por estrato, semente 42 |
| `tools/dossie_auditoria.py --cego --indices N` | os dois, opcional | evidência do par N, sem o estrato |

Gerados por `python tools/auditoria_humana.py --gerar`. A coluna `par` é o número da linha em
`auditoria_binding.csv`.

## Cegamento

As planilhas **não** trazem estrato, método de binding, evidência, peso nem sinais de risco
(`ambiguo`, `n_testes_da_producao`). Saber que um par veio de
`referencia_estatica/import_fqn` já sugere a resposta no critério estrito.

Durante o julgamento, nenhum avaliador abre:

- `auditoria_binding_auto.csv` (vereditos automatizados e justificativas);
- `auditoria_binding.csv` (traz o estrato de cada par);
- a planilha do outro avaliador.

O dossiê é evidência, não veredito: mostra pacotes, imports e as linhas do teste que citam o
tipo. Usado com `--cego`, não mostra o estrato.

**Limitação declarada do avaliador 1.** O primeiro autor conhece o resultado agregado da
auditoria automatizada (94,2%; 94,8% × 10,1%) e alguns casos citados na documentação
(`RouteBuilder` do Camel, as variantes JRE/Android do Guava). Não conhece os vereditos par a
par. O avaliador 2 deve ser alguém que **não** leu os relatórios do estudo, e a concordância
entre os dois é o controle desse risco.

## Critérios

Todo par recebe **dois** vereditos, `s`, `n` ou `?`. Os avaliadores não sabem de qual
estratégia o par veio, então os dois critérios valem para todos os pares.

| coluna | pergunta | conta como `n` |
|---|---|---|
| `correto_estrito` | a classe de produção é o **alvo** do teste? | fixture, valor de entrada ou saída, infraestrutura, andaime; arquivo errado (homônimo de outro pacote, variante de outro *flavor* do mesmo repositório) |
| `correto_amplo` | o teste **executa código** da classe, ainda que como fixture? | homônimo ou arquivo errado, import morto, mock/stub da classe, menção sem uso (só tipo em assinatura, só constante) |

`?` vale só quando a evidência disponível (os dois arquivos no commit da coleta) não permite
decidir. Não serve para "parece que sim". Toda resposta `?` leva uma justificativa em
`observacao`.

## Procedimento

1. O avaliador 1 julga os 293 pares, nos dois critérios, de forma independente.
2. O avaliador 2 julga os 48 pares, nos dois critérios, de forma independente, sem contato
   com o avaliador 1 sobre os pares.
3. Só depois dos passos 1 e 2 fechados, os dois discutem cada divergência dos 48 e registram
   o consenso em `consenso_estrito` e `consenso_amplo`. Sem consenso, fica `?`.
4. `python tools/auditoria_humana.py --apurar`.

## O que se calcula

| medida | sobre | como |
|---|---|---|
| concordância entre humanos | 48 pares, vereditos **independentes** (antes do consenso) | concordância percentual e kappa de Cohen, por critério |
| veredito final | 293 pares | consenso, nos 48 onde existe; avaliador 1 no resto |
| precisão humana | 293 pares, veredito final | por estrato e global ponderada pelo peso do estrato no binding, como em `auditar_binding.py` |
| concordância humano × automatizado | 293 pares | concordância percentual e kappa, por critério |

- Pares com `?` saem do denominador da precisão e do kappa, e são contados e reportados.
- Kappa e concordância percentual são **sempre reportados juntos**. Em estratos com
  prevalência extrema o kappa fica baixo, ou indefinido, mesmo com concordância alta
  (paradoxo do kappa). A amostra de 48 é estratificada justamente para equilibrar a
  prevalência.
- O kappa entre humanos é calculado **antes** do consenso. Calcular depois mediria o acordo
  da discussão, não o dos julgamentos.

## Regras de decisão fixadas agora

- **A precisão reportada no artigo é a humana** (veredito final), nos dois critérios. A
  automatizada aparece só como concordância.
- **Divergência humano × automatizado não é adjudicada**: prevalece o humano. O arquivo
  automatizado não é alterado.
- Se a concordância entre humanos for baixa, ela é reportada como está, e a precisão segue
  sendo a do veredito final. Não há repetição do julgamento até a concordância melhorar.
- Os critérios não mudam depois que o primeiro par for julgado. Caso não previsto aqui é
  decidido em `observacao`, par a par, e listado no artigo se for recorrente.

## Como descrever no artigo

> Binding precision was assessed by a human census of the 293 audited pairs (first author),
> blind to the binding strategy, under two criteria (target vs. exercised). A second rater,
> not involved in the study, independently judged a stratified subsample of 48 pairs (8 per
> stratum); inter-rater agreement is reported as percent agreement and Cohen's kappa,
> computed before consensus. Disagreements were resolved by discussion.
