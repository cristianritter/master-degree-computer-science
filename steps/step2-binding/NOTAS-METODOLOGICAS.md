# Notas metodológicas — o que cada decisão do step 2 significa no artigo

Este arquivo não documenta código (isso é o `README.md`). Ele explica **os conceitos por
trás das decisões**, com os números deste dataset como exemplo, e indica o que dá e o que
não dá para escrever no artigo em cada caso.

Ordem sugerida de leitura: 1 → 2 → 3 são o essencial; o resto é consulta.

---

## 1. Precisão e recall: as duas maneiras de o binding errar

O binding afirma pares: *"a classe de teste T testa a classe de produção P"*. Ele pode
errar de duas formas independentes, e elas têm nomes próprios porque exigem medidas
diferentes.

**Precisão** (também *valor preditivo positivo*, PPV): dos pares que o binding afirmou,
quantos são verdadeiros?

```
precisão = pares afirmados que são verdadeiros / pares afirmados
```

**Recall** (também *revocação*, *sensibilidade*): das ligações que existem de verdade no
mundo, quantas o binding encontrou?

```
recall = ligações verdadeiras encontradas / ligações verdadeiras existentes
```

Uma analogia: você pede ao binding uma lista de nomes. Precisão é "quantos nomes da lista
estão certos". Recall é "quantos dos nomes que deveriam estar na lista ele achou". Dá para
ter precisão perfeita listando um nome só (recall péssimo), e recall perfeito listando
todo mundo (precisão péssima). Por isso as duas se reportam juntas.

**Neste step:**

| | mede o quê | estado |
|---|---|---|
| precisão | os 16.869 pares afirmados estão certos? | **a auditoria da seção 5 do README mede isso** |
| recall | quantas ligações verdadeiras ficaram de fora? | **não medido** — são as 62,5% de amostras sem teste identificado |

O recall não é medido porque a auditoria sorteia *entre os pares que existem*. Para
estimá-lo seria preciso outro desenho: sortear arquivos de produção **não ligados** e
procurar à mão se existe teste para eles. É viável e não foi feito.

**No artigo:** reporte precisão com o número da auditoria, e trate o recall como ameaça
declarada, usando a cadeia de atrito (4.770 → 4.300 → 1.611) e o `motivo_sem_ligacao` do
`production_files.csv`, que separa `repo_indisponivel`, `projeto_sem_classe_de_teste` e
`sem_ligacao_resolvida`. **Não escreva "cobertura de 37,5%" como se fosse recall** — parte
das 62,5% são classes que genuinamente não têm teste, e isso é achado, não falha.

---

## 2. Atenuação: por que erro de medida é fatal para um resultado nulo

Este é o conceito mais importante do arquivo, e é o que justifica a auditoria existir.

Quando a variável que você mede tem erro aleatório, a correlação que você calcula fica
**sistematicamente menor** que a correlação verdadeira. O efeito é puxado na direção de
zero. Isso se chama **atenuação por erro de medida** (*regression dilution*, na literatura
de epidemiologia).

Por que acontece, sem fórmula: se metade dos pares do binding é falsa, metade dos test
smells que você atribui à classe P na verdade vieram do teste de outra classe qualquer.
Esses valores são ruído em relação a P — não têm relação nenhuma com o code smell de P.
Misturar sinal com ruído dilui o sinal. Quanto mais ruído, mais a correlação medida se
aproxima de zero.

**A consequência prática, e é séria:**

- Se o seu resultado for **positivo** ("há relação"), a atenuação trabalha a seu favor: o
  efeito verdadeiro é ainda maior que o medido. Erro de medida não cria correlação do nada.
- Se o seu resultado for **nulo** ("não há relação"), você não consegue distinguir duas
  explicações completamente diferentes:
  1. não existe relação entre test smell e code smell;
  2. existe relação, mas o binding é ruidoso demais para ela aparecer.

Sem o número da precisão, a explicação (2) fica em aberto e o revisor tem razão em
levantá-la. Com precisão medida em 90%, você pode argumentar que 10% de ruído não apaga um
efeito que existisse. Com precisão medida em 55%, você mesmo sabe que o nulo não é
interpretável — e isso é melhor descobrir agora do que na revisão.

**No artigo:** se o resultado for nulo, a seção de ameaças à validade **precisa** citar
atenuação e o número da precisão. É a diferença entre "não encontramos relação" e "não
encontramos relação, e medimos o quanto nosso instrumento poderia estar escondendo uma".

---

## 3. Determinístico não é o mesmo que correto

Uma regra determinística é uma regra que, com a mesma entrada, dá sempre a mesma saída —
é reprodutível e auditável. Isso é **independente** de ela estar certa: uma regra pode
errar de forma perfeitamente consistente.

Exemplo deste dataset: o `getFileProduction` do `jnose-core` tira o sufixo `Test` do nome
da classe e varre a árvore do projeto atrás de um `.java` com o nome restante. Regra
fechada, 100% reprodutível — e capaz de casar o arquivo errado sempre que dois módulos do
mesmo repositório têm classes de mesmo nome.

O caso concreto encontrado aqui: a estratégia `convencao` do `binding.py` indexava os
testes por **basename no repositório inteiro**, apesar de o README afirmar que o binding é
por caminho. Resultado, no mesmo repositório:

```
prod : .../reil/translators/mips/NorTranslator.java
teste: .../reil/translators/mips/NorTranslatorTest.java     correto
teste: .../reil/translators/ppc/NorTranslatorTest.java      outra classe, outro pacote
```

A regra é determinística e errou em silêncio. Ela só apareceu porque a auditoria obrigou a
olhar par a par — antes mesmo de qualquer par ser julgado.

Cuidado com a leitura ingênua da coluna `ambiguo`: ela marca **arquivo de produção com mais
de uma classe de teste ligada pelo mesmo método** (42 pares em `caminho_exato`, 26 em
`convencao`), o que muitas vezes é legítimo — uma classe pode ter vários testes. Ela não
mede "a regra escolheu o arquivo de produção errado"; para isso serve a auditoria.

Vale notar também que 62,4% dos pares de `convencao` envolvem classes de teste cujo nome o
`jnose-core` reporta errado (defeito de classe aninhada, step 1 seção 5).

**No artigo:** "aplicamos uma regra determinística" é argumento de *reprodutibilidade*, não
de *corretude*. As duas precisam ser defendidas separadamente — a primeira pelo código
publicado, a segunda pela auditoria.

---

## 4. Intervalo de confiança: o que "±8 pp" quer dizer

A auditoria confere 50 pares por estrato, não os 14.092 de `import_fqn`. O resultado é uma
**estimativa**, e o intervalo de confiança é a maneira honesta de dizer o quanto ela pode
estar longe do valor real.

Lendo "precisão de 90% (IC95%: 82%–98%)": se repetíssemos o sorteio de 50 pares muitas
vezes, em 95% delas o intervalo construído desse jeito conteria a precisão verdadeira.
Informalmente: o valor real está provavelmente nessa faixa, e é irresponsável reportar
"90%" sem ela.

Com n=50 por estrato, a margem depende do resultado:

| precisão observada | IC95% |
|---|---|
| 95% | ±6,0 pp |
| 90% | ±8,3 pp |
| 80% | ±11,1 pp |
| 50% | ±13,9 pp |

A margem é menor perto dos extremos porque há menos variabilidade possível ali. Se reduzir
para 30 pares por estrato (`--por-estrato 30`), a margem no pior caso sobe para ~±18 pp.

> "pp" é **ponto percentual**, a unidade da diferença entre duas porcentagens. Sair de 80%
> para 88% é subir 8 pp (e não "8%", que seria 86,4%).

**No artigo:** sempre com IC. "Precisão de 88%" sem intervalo é número sem qualificação.

---

## 5. Amostragem estratificada e não-proporcional

**Estrato** é um subgrupo definido antes de sortear. Aqui os estratos são as combinações
(método de binding, tipo de evidência).

**Amostragem proporcional** sortearia de cada estrato na proporção em que ele aparece no
universo. Seria péssimo aqui: `convencao` tem 0,6% dos pares, então daria **2 pares** — e
com 2 pares não se estima precisão nenhuma.

**Amostragem não-proporcional** (o que foi feito) sorteia 50 de cada estrato,
independentemente do tamanho. Cada estrato ganha precisão estimável com margem parecida.
O preço é que a média simples dos cinco estratos **não** é a precisão do binding: é preciso
ponderar cada estrato pelo seu peso real no universo, e é para isso que existe a coluna
`peso_no_universo`:

| estrato | peso na precisão global |
|---|---:|
| `referencia_estatica/import_fqn` | 83,5% |
| `referencia_estatica/mesmo_pacote` | 11,1% |
| `caminho_exato` | 4,0% |
| `referencia_estatica/wildcard` | 0,8% |
| `convencao` | 0,6% |

Consequência que vale entender: **a precisão global é quase inteiramente a do
`import_fqn`.** Reportar só o número global esconderia o desempenho das outras quatro
estratégias. Reporte a tabela por estrato; o global é resumo, não substituto.

**No artigo:** descreva o desenho ("amostra estratificada não-proporcional, 50 pares por
estrato, ponderada pelo peso do estrato no universo"). É desenho padrão e defensável, mas
precisa ser declarado — senão parece que você sorteou 250 pares ao acaso.

---

## 6. Prevalência, poder estatístico e o "44 positivos"

**Prevalência** é a proporção de casos positivos. Aqui: quantos arquivos de produção têm o
code smell, pela regra de rótulo escolhida.

A prevalência depende inteiramente da regra:

| regra | positivos entre as 4.300 amostras disponíveis |
|---|---|
| `pos_any` (alguém marcou > none) | 26,0% |
| `pos_any_major` (alguém marcou ≥ major) | 16,7% |
| `pos_maioria` (a maioria marcou > none) | 5,2% |
| `pos_unanime` (todos marcaram) | 0,4% |

**Poder estatístico** é a capacidade de detectar um efeito que existe. Ele depende do N
total *e* da prevalência: 1.000 casos com 2 positivos têm poder quase nulo, porque quase
não há variação para explicar. É por isso que `pos_unanime` (17 positivos em todo o
dataset) é inútil como variável principal — não por ser errada, mas por não ter poder.

Foi daí que veio o número que te chamou atenção: 759 amostras × 5,8% = **44 positivos**.
Não é falha do binding. É a prevalência da regra da maioria (5,2% em todo o MLCQ) aplicada
a um N de 759.

**A saída:** com `--rotulo sev_media` a questão não se coloca. Em vez de dicotomizar em
positivo/negativo, cada arquivo entra com a severidade média das suas revisões (0 a 3),
como valor contínuo. Todas as linhas ligadas entram na análise, sem limiar para discutir,
e as 14.739 revisões são usadas em vez de descartadas. As dicotomizações entram depois
como **análise de sensibilidade** ("o achado se mantém se dicotomizarmos?").

---

## 7. Viés de seleção: por que a tabela de prevalência tranquiliza

**Viés de seleção** acontece quando o critério que decide *quem entra na análise* é
correlacionado com o que você está estudando. Exemplo do que seria desastroso aqui: se o
binding achasse teste mais facilmente para classes com code smell, a amostra analisada
teria mais smell que a população, e a relação medida seria artefato do binding.

Os números dizem que isso não acontece:

| | amostras | `pos_any` | `pos_maioria` |
|---|---:|---:|---:|
| todas as disponíveis (HASH_OK) | 4.300 | 26,0% | 5,2% |
| só as ligadas pelas determinísticas | 759 | 27,1% | 5,8% |
| ligadas com a estratégia 3 | 1.611 | 27,2% | 5,8% |

Ligar ou não ligar é praticamente independente do rótulo. A mesma verificação por estrato
de evidência está no README (cobertura de 36,8% a 42,9% nos quatro estratos).

**No artigo:** é uma tabela pequena que vale a pena incluir, porque antecipa a pergunta
"sua amostra analisada é representativa das anotações do MLCQ?" com evidência em vez de
argumento. `conferir_dados.py --secao 6` regenera esses números.

---

## 8. Validade: os três tipos que aparecem neste step

Vocabulário padrão de engenharia de software experimental, útil para organizar a seção de
ameaças:

**Validade de construto** — o que você mede é mesmo o conceito que você diz medir?
- *Onde aperta aqui:* `referencia_estatica` mede "o teste referencia o tipo", mas o
  construto pretendido é "o teste testa a classe". Referenciar é condição necessária, não
  suficiente. O caso do DTO ligado a 18 testes é falha de construto.
- *Onde está bem:* o test smell vem do JNose, ferramenta validada **para isso**.

**Validade interna** — a relação que você observa é causada pelo que você pensa, ou por um
terceiro fator / pelo desenho?
- *Onde aperta:* o rótulo do MLCQ é circular com o desenho amostral (README seção 3) —
  `any > none` é quase um detector de "esta amostra foi ao crosscheck".
- *Onde está bem:* a tabela de prevalência da seção 7 acima afasta viés de seleção pelo
  binding.

**Validade externa** — o resultado generaliza para além da amostra?
- *Onde aperta:* 451 repositórios Java de código aberto, selecionados pelo MLCQ com
  critérios próprios. Não generaliza para código proprietário, nem para outras linguagens.

**No artigo:** cada ameaça precisa vir com o que você fez a respeito. "Ameaça reconhecida e
não mitigada" é aceitável; ameaça não mencionada é o que derruba submissão.

---

## 9. Concordância entre avaliadores

Se **uma** pessoa (ou um modelo) julga os 250 pares, o resultado é "precisão segundo aquele
julgamento". Isso é legítimo, mas é um julgamento só, e julgamento tem erro.

**Concordância entre avaliadores** (*inter-rater agreement*) mede o quanto dois avaliadores
independentes chegam à mesma conclusão. A medida usual não é a porcentagem crua de
concordância, e sim o **kappa de Cohen**, que desconta a concordância que aconteceria por
acaso. Interpretação convencional: κ > 0,80 quase perfeita, 0,60–0,80 substancial,
0,40–0,60 moderada.

Isso importa porque o próprio MLCQ vive esse problema: 97–99% dos positivos pela regra do
máximo são *disputados* — outro revisor olhou a mesma classe e disse `none`. Julgar code
smell é subjetivo, e o dataset registra isso.

**Caminho barato aqui:** uma passada completa feita por mim, você confere todos os `?` e
uma amostra dos `s`. A taxa de discordância vira número reportável, e o artigo descreve o
procedimento honestamente ("primeira passada automatizada, conferida por amostragem pelo
autor") em vez de chamar de auditoria independente.

**No artigo:** descreva quem julgou e como. Não chame de auditoria manual o que foi
automatizado — é exatamente o tipo de detalhe que, descoberto pelo revisor, custa a
credibilidade do resto.

---

## 10. O que NÃO dá para escrever

Lista curta de afirmações tentadoras que este dataset não sustenta:

1. **"O JNose identificou a classe de produção testada."** O `getFileProduction` é
   convenção de nomenclatura mais busca por basename (README seção 4). A validação da
   ferramenta na literatura é sobre detecção de test smells.
2. **"Assumimos que o binding está correto."** É a frase que a auditoria existe para
   substituir.
3. **"X% das classes com code smell não têm teste."** O binding não distingue "sem teste"
   de "teste não encontrado" em todos os casos — só o `projeto_sem_classe_de_teste`
   (70 arquivos, 1,5%) é observação sobre o projeto.
4. **"A classe tem o smell porque um revisor marcou."** Com 2 revisores, qualquer flag
   escalava a amostra ao crosscheck; `any > none` é quase um marcador de crosscheck.
5. **"Não anotado = negativo."** O MLCQ anotou amostras específicas para smells
   específicos. Por isso as colunas `cs_*` têm três estados, e vazio nunca vira 0.
6. **"Eager Test e Lazy Test nas linhas de classe aninhada."** Caem 28× e 23× por defeito
   do `jnose-core`. Filtrar ou estratificar por `n_testes_nome_divergente` é obrigatório.

---

## 11. Glossário rápido

| termo | em uma linha |
|---|---|
| precisão (PPV) | dos pares afirmados, quantos estão certos |
| recall | das ligações verdadeiras, quantas foram achadas |
| atenuação | erro de medida puxa a correlação medida na direção de zero |
| IC95% | faixa que conteria o valor real em 95% das repetições do sorteio |
| pp (ponto percentual) | unidade da diferença entre duas porcentagens |
| estrato | subgrupo definido antes de sortear |
| prevalência | proporção de casos positivos |
| poder estatístico | capacidade de detectar um efeito que existe |
| viés de seleção | quem entra na análise depende do que se está estudando |
| validade de construto | o que se mede é o conceito pretendido |
| validade interna | a relação observada é a que se pensa |
| validade externa | o resultado generaliza |
| kappa de Cohen | concordância entre avaliadores, descontando o acaso |
| análise de sensibilidade | refazer com outra decisão para ver se o achado sobrevive |
