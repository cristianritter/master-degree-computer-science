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

## Evidência do julgamento e material dos avaliadores — 31/10/2026

Decidido durante o julgamento do avaliador 1, antes de o avaliador 2 começar. Critérios e
procedimento não mudam; muda o que conta como evidência e, por consequência, o `?`.

- **A evidência é o dossiê**, não os fontes completos. `?` passa a valer quando o dossiê
  não permite decidir. Abrir os 293 pares a mão não é viável, e um `?` que significasse
  "não abri o arquivo" mediria o esforço do avaliador, não o par.
- **Dossiê com contexto.** `dossie_auditoria.py --contexto` acrescenta ao dossiê simples o
  tipo da classe de produção (classe, classe abstrata, interface e seus métodos com corpo),
  a instrução completa de cada menção (uma chamada quebrada em várias linhas aparece
  inteira), o corpo dos métodos do próprio teste que devolvem o tipo (`createFoo()`), e o uso
  das variáveis declaradas com o tipo ou que recebem algo onde o nome aparece (inclusive
  `Foo.class` passado a uma fábrica): os métodos chamados nelas e as chamadas a que são
  passadas como argumento. Continua sendo evidência: não há heurística de decisão.
- **Avaliador 1.** Os vereditos `s`/`n` do censo foram dados com o dossiê simples e ficam
  como estão. Os pares com `?` são rejulgados com o dossiê com contexto
  (`python tools/auditoria_humana.py --revisao` gera `dossie_revisao_avaliador1.txt`).
- **Avaliador 2.** Recebe `pacote-avaliador2.zip` (`python tools/auditoria_humana.py
  --pacote`): a planilha dos 48 pares em branco e o dossiê `--cego --contexto` desses pares.
  Não recebe os fontes e não abre os links da planilha.
- **Efeito do `?` na precisão.** `--apurar` reporta, além da precisão sobre os pares
  decididos, os limites com todo `?` contado como `n` (inferior) e como `s` (superior), por
  estrato e global. O artigo traz os três números.

## Regra para teste que não cita a classe — 31/10/2026

Quando o teste não cita o nome da classe de produção nenhuma vez fora de comentário e literal
(o dossiê mostra `0 linhas` de menção):

- `correto_estrito` = `n`: um teste cujo alvo é a classe a cita; o nome dos arquivos não
  basta;
- `correto_amplo` = `?`: a classe ainda pode ser executada por interface, reflexão, injeção
  ou superclasse do teste, o que o dossiê não mostra.

Vale para os dois avaliadores. O efeito é conservador no estrito (o par conta como erro) e
retira o par do denominador no amplo, com os limites acima. No censo do avaliador 1 são 13
pares.
