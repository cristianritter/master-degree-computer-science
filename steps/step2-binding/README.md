# Step 2 — Binding entre code smells e test smells

Liga as anotações de code smell do **MLCQ** (código de produção) aos test smells coletados
pelo **JNose** no step 1 (código de teste), produzindo um conjunto de dados normalizado
onde cada arquivo de produção anotado aparece ao lado das classes de teste que o
exercitam.

**Este step não produz análise.** Ele produz o dado sobre o qual a análise vai rodar, e os
números sobre si mesmo — cobertura por estratégia e precisão auditada. A escolha de regra
de rótulo e de agregação é parâmetro de linha de comando, não conteúdo dos CSVs.

Entrada: `MLCQ/MLCQCodeSmellSamples.xlsx` e `steps/step1-coleta-jnose/reports/`
Saída: `dados/`

| | |
|---|---|
| Revisões do MLCQ | 14.739 |
| Amostras do MLCQ | 4.770 |
| Amostras em repositório disponível (`HASH_OK`) | 4.300 |
| Arquivos de produção anotados distintos | 4.559 |
| Classes de teste normalizadas | 107.535 |
| Ocorrências de test smell normalizadas | 2.059.905 |
| Amostras com classe de teste identificada | **1.611 (37,5% das disponíveis)** |
| Pares (produção, teste) no binding | 16.869 |

---

## 1. Ambiente

| Componente | Versão |
|---|---|
| Python | 3.12.10 (`openpyxl`) |
| git | para a estratégia 3, que clona os espelhos |

Nenhuma dependência do JNose: o step 2 lê os CSVs que o step 1 já exportou. A única
exceção é `refs_producao.py`, que clona os espelhos e reusa duas funções do
`jnose_batch.py` do step 1 (`_sem_comentarios` e `rmtree`).

| Variável | Padrão |
|---|---|
| `JNOSE_PROJECTS` | `~/.jnose_projects` (onde a estratégia 3 clona) |

---

## 2. Normalização

### `dados/mlcq_reviews.csv` — 14.739 linhas, 1 por revisão

Nada agregado. Existe para que a agregação seja auditável e refazível.

### `dados/mlcq_samples.csv` — 4.770 linhas, 1 por amostra

Carrega **várias colunas de rótulo lado a lado** — `sev_max`, `sev_media`, `sev_mediana`,
`pos_any`, `pos_maioria`, `pos_unanime`, `pos_any_major` — e nenhuma delas é "o" rótulo.
A razão está na seção 3, e as colunas estão no dicionário da seção 7.

### `dados/test_classes.csv` — 107.535 linhas, 1 por classe de teste

O `byclasstest` do step 1 com três mudanças:

1. **Caminhos absolutos viram relativos ao repositório**, no mesmo formato do campo `path`
   do MLCQ. É o que permite o binding por caminho exato.
2. **O nome da classe é recomputado** do basename do `PathFile`, corrigindo o defeito do
   `flowClass` documentado no step 1 (seção 5) — em arquivo com classe aninhada o JNose
   reporta o nome do *helper*. São 6.842 linhas (6,4%). O nome original fica em
   `nome_jnose` e a flag `nome_divergente` marca as linhas afetadas.
3. **As 8 colunas de smell não habilitadas são descartadas.** Estão zeradas em todas as
   107.535 linhas — conferido, não assumido. Um zero estrutural lido como "smell ausente"
   seria erro silencioso.

> **A correção do nome recupera a identidade da classe, não os valores de smell.** O
> `ProductionFileName` foi resolvido a partir do nome errado e fica vazio em 93,8% dessas
> linhas, derrubando Eager Test 28× e Lazy Test 23×. Qualquer análise que envolva
> Eager/Lazy Test tem que filtrar ou estratificar por `nome_divergente` — é para isso que
> `montar_analise.py --excluir-nome-divergente` existe. Corrigir de verdade exigiria
> consertar o `jnose-core` e repetir as ~35 h de coleta.

### `dados/test_smell_occurrences.csv.gz` — 2.059.905 linhas, 1 por ocorrência

Nível de método (`testSmellMethod`, faixa de linhas, hashes), para drill-down posterior. O
campo `methodCode` — quase todo o 1,4 GB do step 1 — **não** é copiado; os hashes ficam, e
o step 1 continua sendo a fonte do código quando ele for necessário. 109 MB.

> **Este é o único arquivo não versionado inteiro.** 104 MB passam do limite de 100 MB por
> blob do GitHub, então o repositório guarda três partes de 45 MB
> (`test_smell_occurrences.csv.gz.part00`, `.part01`, `.part02`) e o SHA-256 do arquivo
> montado em `test_smell_occurrences.csv.gz.sha256`. Reconstituir é uma concatenação:
>
> ```bash
> cd dados
> cat test_smell_occurrences.csv.gz.part0* > test_smell_occurrences.csv.gz
> sha256sum -c test_smell_occurrences.csv.gz.sha256
> ```
>
> A ordem é a do glob e a divisão é por byte — as partes não são gzip válido isoladamente.
> Nenhum script do step 2 lê esse arquivo; ele existe para o drill-down posterior. Quem
> preferir regerá-lo roda `normalizar_jnose.py` (~1,5 min).

---

## 3. O rótulo do MLCQ é circular com o desenho amostral

A regra intuitiva é "se algum revisor marcou severidade > `none`, a classe tem o smell".
Ela **não é defensável neste dataset**, e o motivo está no apêndice do próprio MLCQ
(`enrollment/MadeyskiLewowskiMLCQAppendix.pdf`, seção 2.2, fase 4):

> The last 5115 samples (date range: 26.07.2019-13.09.2019) were selected to perform a
> crosscheck — **only from samples already graded to a severity higher than 'none'**.
> Samples selected from crosscheck were those that had only 1 review or 2 reviews with
> different severities.

Revisores extras foram alocados **só para amostras que alguém já havia marcado como
positiva**. O número de revisores é consequência do rótulo, não evidência independente
dele. Conferido nos dados: das 1.227 amostras com revisão a partir de 26.07.2019,
**1.227 (100%) já eram positivas antes dessa data, e nenhuma era negativa.** O apêndice
descreve exatamente o que os dados fazem — por isso `foi_crosscheck` é derivado por
`review_timestamp`, não por contagem de revisores.

O efeito:

| revisores | amostras | positivas por `any > none` | por maioria | severidade média |
|---:|---:|---:|---:|---:|
| 2 | 3.511 | **0,0%** (1 de 3.511) | 0,0% | 0,000 |
| 4 | 209 | 97,6% | 4,8% | 0,764 |
| 6 | 702 | **100,0%** | 21,2% | 0,593 |
| 8 | 262 | **100,0%** | 25,2% | 0,756 |
| 10 | 43 | **100,0%** | 18,6% | 0,798 |

`any > none` não é critério de rotulagem: é quase literalmente um detector de "esta
amostra foi para o crosscheck". As amostras de 2 revisões têm 0% de positivos porque, por
construção, qualquer flag ali escalava a amostra para mais revisores.

E o crosscheck foi feito **justamente para julgar aqueles flags** — a regra do máximo
descarta o veredito dele, que em geral não confirmou:

| regra | blob | data class | feature envy | long method | geral |
|---|---:|---:|---:|---:|---:|
| `any > none` | 27,8% | 40,3% | 20,0% | 18,4% | **25,8%** |
| maioria > none | 2,9% | 7,8% | 2,9% | 7,0% | **5,2%** |
| unânime > none | 0,2% | 0,3% | 0,5% | 0,5% | **0,4%** |

Em todo o MLCQ existem **19 amostras com positivo unânime**. Dos positivos pela regra do
máximo, 97–99% são disputados — outro revisor olhou a mesma classe e disse `none`.

O risco disso não é "positivos demais": 25,8% é prevalência boa para estatística. O risco
é **precisão baixa no rótulo**, que causa atenuação — a correlação medida é enviesada na
direção de zero. Num artigo cujo achado pode ser um nulo, isso torna o nulo
não-interpretável: não se distingue "não há relação" de "há relação, mas o rótulo é
ruidoso demais".

### A coluna `estrato`

Em vez de escolher um limiar, `mlcq_samples.csv` classifica cada amostra pela força da
evidência:

| estrato | amostras | o que é |
|---|---:|---|
| `negativo_confiavel` | 3.515 | 2+ revisores, nenhum marcou > `none`. O desenho amostral os torna especialmente fortes: qualquer flag teria escalado a amostra. Negativo confiável é raro em dataset de code smell — é um ativo, não um resto. |
| `disputado` | 985 | alguém marcou > `none`, mas não a maioria. É aqui que as duas regras discordam, e é a "lacuna de concordância" da literatura. |
| `positivo_confiavel` | 247 | a maioria marcou > `none`. |
| `negativo_1_review` | 23 | revisor único, negativo. Sem corroboração. |

A análise principal compara os extremos; o estrato disputado é uma RQ secundária de graça
(*densidade de test smell prediz quais casos disputados a maioria confirmou?*).

---

## 4. O binding

### `dados/binding.csv` — 1 linha por par (arquivo de produção, classe de teste)

Muitos-para-muitos de propósito. 3,0% dos arquivos de produção têm mais de uma classe de
teste apontando para eles (legitimamente até 8), e colapsar isso numa linha por classe
forçaria a decidir agora como agregar vários testes, deixando a decisão enterrada no dado.
Ela fica em `montar_analise.py`.

**O par sai sempre como caminho, e a comparação com o MLCQ é por caminho.** O
`ProductionFileName` do JNose é caminho completo, e o campo `path` do MLCQ é relativo ao
repositório; reduzidos ao mesmo formato eles coincidem exatamente, porque o `HASH_OK`
garante o mesmo commit.

Casar **teste** por nome, porém, inventa ligações: 2.956 basenames de teste aparecem em
mais de um arquivo dentro do mesmo repositório — `AppTest` ocorre **159 vezes** em
`maven-plugins`. A estratégia `convencao` procura `XTest` por basename no repositório, e
por isso carrega uma coluna `evidencia` que diz se o teste está no mesmo pacote da
produção:

| evidência da `convencao` | pares | o que é |
|---|---:|---|
| `caminho_espelhado` | 50 | teste e produção no mesmo caminho de pacote |
| `so_basename` | 43 | só o nome coincide; o pacote é outro |

As duas existem porque nenhuma das duas é descartável. `so_basename` inclui erro real —
`NorTranslatorTest` de `/ppc` casando com o `NorTranslator` de `/mips`, no mesmo
repositório — e também ligação legítima: a árvore de testes do JDK não espelha a de
produção, e `LinkedList.java` ↔ `LinkedListTest.java` é correto ali. Distinguir as duas é
trabalho da auditoria, que por isso as trata como estratos separados.

> Esta separação foi acrescentada depois da primeira versão do step, ao montar a
> ferramenta de auditoria: o README afirmava que a `convencao` casava por caminho, e a
> implementação casava por basename. O código e a documentação discordavam em silêncio, e
> foi o preparo da conferência par a par que expôs isso — antes de qualquer par ter sido
> julgado.

O método de cada par é uma **coluna**, não um pressuposto, porque os métodos têm precisão
diferente e o artigo precisa poder mostrar que o achado se mantém em mais de um:

| método | o que é | cobertura |
|---|---|---|
| `caminho_exato` | o `ProductionFileName` que o próprio JNose resolveu | 675 pares, 15,8% das amostras |
| `convencao` | `X.java` ← `XTest` / `XTests` / `XTestCase` / `XIT` / `XITCase`, casando por basename no repositório, com o espelhamento de pacote como evidência | +93 pares, +1,7% |
| `referencia_estatica` | a classe de teste referencia o tipo de produção no código | ver abaixo |

`caminho_exato` é viesado: a resolução parte do nome da classe, errado nas 6.842 linhas de
classe aninhada, onde `production` fica vazio em 93,8% — a ausência de ligação não é
aleatória.

#### O que o `ProductionFileName` do JNose é, de fato

É tentador tratá-lo como oráculo — a ferramenta foi validada por outros estudos, então o
que ela diz sobre a classe de produção estaria chancelado. **Não está**, e a distinção
importa o suficiente para ser verificada em vez de suposta. Desmontando o
`jnose-core-0.9.4.jar` que o step 1 usou, o método `JNoseCore.getFileProduction` carrega:

```
TEST_PREFIX  TEST_SUFFIX  TESTS_PREFIX  TESTS_SUFFIX  TEST_CASE_PREFIX  TEST_CASE_SUFFIX
^.*test\d*$   ^.*tests\d*$   ^.*testcase\d*$   ^test.*   ^tests.*   ^testcase.*
```

e opera com `Files.walk`, `getFileName` e `endsWith`, falhando com a mensagem
`getFileProduction: error finding file`. Ou seja: **tira o prefixo/sufixo `Test` do nome da
classe e varre a árvore do projeto atrás de um `.java` com o nome restante.** É convenção
de nomenclatura mais busca por basename — a mesma regra da estratégia `convencao`, só que
aplicada ao nome da classe (errado em 6,4% das linhas) em vez do caminho.

O que a literatura validou no JNose/TestSmellDetector é a **detecção de test smells**. O
`getFileProduction` é utilitário interno, não oráculo de binding validado. Citá-lo como
autoridade seria uma afirmação que o revisor derruba abrindo o mesmo jar.

Isso não desqualifica `caminho_exato` — regra determinística e documentada é exatamente o
que se quer. Só muda o que se pode escrever sobre ela: "aplicamos a convenção de
nomenclatura que a ferramenta implementa", não "a ferramenta identificou a classe testada".

Somadas, as duas primeiras ligam **759 de 4.300 amostras (17,7%)**, e quase não se somam
(15,8% + 1,7%): erram nos mesmos casos. Não é falta de estratégia, é falta de sinal — foi
o que motivou a estratégia 3.

### Cadeia de atrito

O recorte que o artigo tem que declarar:

Com as três estratégias:

```
4.770  amostras no MLCQ
4.300  em repositório disponível (HASH_OK)
1.611  com classe de teste identificada       (37,5% dos disponíveis)
         positivo_confiavel     93 de  225   (41,3%)
         disputado             345 de  891   (38,7%)
         negativo_confiavel  1.164 de 3163   (36,8%)
         negativo_1_review       9 de   21   (42,9%)
```

Só com `caminho_exato` + `convencao` eram 759 amostras (17,7%) e 44 positivos confiáveis —
o que não sustentava análise por smell. **O gargalo do artigo era a cobertura do binding,
não a regra de rótulo**, e é por isso que a estratégia 3 foi construída antes de fechar a
agregação. Decidir o rótulo primeiro significaria escolhê-lo para caber num N
artificialmente pequeno.

Note que a cobertura é **praticamente igual nos quatro estratos** (36,8% a 42,9%). Isso é
tranquilizador: se o binding tivesse mais facilidade em achar teste para classe suja, ele
introduziria viés direto na RQ.

### `dados/production_files.csv` — 1 linha por arquivo de produção anotado

Mantém os **não ligados**, com motivo. "Classe com code smell não tem teste" é
potencialmente um achado, não refugo:

| `motivo_sem_ligacao` | arquivos | |
|---|---:|---|
| (ligado) | 1.549 | 34,0% |
| `sem_ligacao_resolvida` | 2.482 | 54,4% |
| `repo_indisponivel` | 458 | 10,0% |
| `projeto_sem_classe_de_teste` | 70 | 1,5% |

`projeto_sem_classe_de_teste` são os **21 repositórios** (de 451 analisados com sucesso)
em que o JNose não detectou nenhuma classe de teste.

> Distinguir `projeto_sem_classe_de_teste` de `sem_ligacao_resolvida` importa: o primeiro é
> observação sobre o projeto, o segundo é limitação do método. Somá-los seria reportar
> falha de matching como ausência de teste.

### Estratégia 3: referência estática

`refs_producao.py` clona cada espelho e pergunta uma coisa só: **este arquivo de teste
referencia este tipo de produção?** Não depende de o teste se chamar `XTest` nem de o
`jnose-core` ter resolvido o nome da classe.

Três evidências, da mais forte para a mais fraca, gravadas em `refs_producao.csv`:

| evidência | critério |
|---|---|
| `import_fqn` | o teste tem `import <pacote>.<Tipo>;` exato. Sem ambiguidade. |
| `wildcard` | o teste tem `import <pacote>.*;` e menciona o identificador `<Tipo>`. |
| `mesmo_pacote` | teste e produção declaram o mesmo `package` e o teste menciona `<Tipo>`. Java não exige import nesse caso, então é ligação legítima — mas é a única das três que casa identificador solto, e a mais sujeita a falso positivo. |

A menção ao identificador é buscada no código **sem comentários nem literais**, reusando o
`_sem_comentarios()` do step 1 — a mesma função já validada lá contra o oráculo de
JavaParser. Reusar evita ter duas heurísticas de texto diferentes no mesmo experimento.

#### Clone esparso

O step 1 clonava o repositório inteiro porque o JNose precisa varrer o projeto. Aqui
sabemos exatamente quais arquivos vamos abrir — as classes de teste do `test_classes.csv`
e os arquivos de produção anotados — então o clone é parcial (`--filter=blob:none`) com
`sparse-checkout` restrito a essa lista. Em `test-smells-SapMachine` (fork do OpenJDK) a
diferença medida foi de **mais de 20 min e >1 GB para 19 s e 39 MB**.

Duas pegadinhas, ambas tratadas no código:

- `--filter=blob:none` deixa o repositório dependente do remoto para buscar blobs depois
  (*promisor remote*), e o `checkout` dispara essa busca. O `http.sslBackend` tem que
  ficar **gravado na config do clone**, não passado com `-c` na linha do `clone`, senão o
  fetch seguinte falha com erro de certificado.
- `--no-cone` porque os caminhos são arquivos avulsos espalhados, não diretórios; no modo
  cone o git só aceita prefixos de diretório.

O HEAD é reconferido contra o `repos_map` do step 1 a cada clone. O step 1 já validou
isso, mas o espelho pode ter recebido commits depois — e nesse caso os caminhos do MLCQ
não valeriam mais e o par seria fictício. Divergência vira `ERRO` no log, não par.

#### Resultado do lote

451 repositórios, **450 de primeira e 1 recuperado**, 41,5 min no total, 5,5 s por
repositório em média (máximo 316 s). O erro foi `test-smells-atlas`: os caminhos iam ao
`git` em modo texto, que no Windows usa cp1252, e esse repositório tem nome de arquivo
fora dessa página de código. Corrigido passando a lista como UTF-8 explícito.

| evidência | pares | |
|---|---:|---|
| `import_fqn` | 14.221 | 84,8% |
| `mesmo_pacote` | 2.407 | 14,4% |
| `wildcard` | 135 | 0,8% |

#### O trade-off: cobertura contra concentração

> **A estratégia 3 não afirma que o teste *testa* aquela classe.** Referenciar é condição
> necessária, não suficiente. No piloto, `CanalEntry.java` — um DTO de protocolo — ficou
> ligado a **18 classes de teste que só o importam**.

Sem filtro, os 16.869 pares se espalham por 1.549 arquivos de produção — **10,9 classes de
teste por arquivo**, o que é implausível como "teste dedicado". A coluna `t/prod` abaixo é
o indicador de risco: quanto mais alta, mais provável que a ligação seja referência
incidental.

| configuração | amostras | % HASH_OK | pos_cf | neg_cf | pares | t/prod |
|---|---:|---:|---:|---:|---:|---:|
| só `caminho_exato` + `convencao` | 759 | 17,7% | 44 | 550 | 768 | 1,1 |
| + refs, todas as evidências | 1.611 | 37,5% | 93 | 1.164 | 16.869 | 10,9 |
| + refs, só `import_fqn` | 1.382 | 32,1% | 81 | 997 | 14.860 | 11,2 |
| **+ refs, máx. 10 testes** | **1.422** | **33,1%** | **79** | **1.027** | **3.335** | **2,4** |
| + refs, máx. 5 testes | 1.264 | 29,4% | 67 | 914 | 2.164 | 1,8 |
| + refs, máx. 3 testes | 1.135 | 26,4% | 61 | 820 | 1.629 | 1,5 |
| + refs `import_fqn`, máx. 3 | 1.010 | 23,5% | 55 | 733 | 1.376 | 1,4 |
| + refs, máx. 1 teste | 713 | 16,6% | 37 | 524 | 691 | 1,0 |

**`--max-testes 10` é o melhor ponto de troca**: custa 4,4 pontos de cobertura (37,5% →
33,1%) e reduz os pares a um quinto, derrubando a concentração de 10,9 para 2,4 testes por
arquivo. Filtrar por `import_fqn` sozinho não ajuda — a concentração *sobe* (11,2), porque
o import exato é justamente o mecanismo pelo qual um DTO é referenciado por todo mundo.

A tabela é regerada por `conferir_dados.py --secao 4`. **Ela não substitui a auditoria da
seção 5** — mede concentração, que é um indício de imprecisão, não a imprecisão em si.

---

## 5. Auditoria da precisão

`auditar_binding.py` sorteia pares estratificados por (método, evidência) e gera
`dados/auditoria_binding.csv` com a coluna `correto` em branco e as URLs dos dois arquivos
no espelho, **no commit da coleta** — a conferência é um clique, não um clone.

```bash
python tools/auditar_binding.py                  # 50 por estrato, semente 42
python tools/auditar_binding.py --por-estrato 30  # amostra menor
python tools/auditar_binding.py --apurar         # precisão por estrato, com IC95%
```

Com o binding completo são **6 estratos e 293 pares** no padrão:

| estrato | pares no binding | sorteados |
|---|---:|---:|
| `caminho_exato` | 675 | 50 |
| `convencao/caminho_espelhado` | 50 | **50 (censo)** |
| `convencao/so_basename` | 43 | **43 (censo)** |
| `referencia_estatica/import_fqn` | 14.092 | 50 |
| `referencia_estatica/mesmo_pacote` | 1.875 | 50 |
| `referencia_estatica/wildcard` | 134 | 50 |

São **293 pares**. Os dois estratos de `convencao` são censo — todos os pares são
conferidos, então ali não há erro de amostragem e a precisão sai exata, sem intervalo.

293 pares a ~1 min cada é meio dia de trabalho. `--por-estrato 30` reduz para ~183 ao custo
de alargar o intervalo de confiança dos estratos amostrados de ~±14 pp para ~±18 pp no pior
caso (p≈0,5); os dois de `convencao` seguem sendo censo.

A amostragem é deliberadamente **não proporcional**: as estratégias raras precisam de N
próprio para ter precisão estimável — proporcional daria 2 pares de `convencao`. O peso de
cada estrato no universo fica na coluna `peso_no_universo`, e `--apurar` usa esse peso para
a precisão global. As linhas saem em ordem embaralhada para o auditor não inferir o estrato
pela posição.

Sem isso o artigo escreveria "assumimos que o binding está correto" — a frase que um
revisor ataca primeiro. Com isso ele reporta precisão observada por estratégia e trata o
resto como ameaça à validade declarada. O custo é uma tarde de trabalho manual.

### Resultado: os três estratos determinísticos

`dados/auditoria_binding_auto.csv`, apurado por
`auditar_binding.py --apurar --arquivo dados/auditoria_binding_auto.csv`:

| estrato | pares | auditados | corretos | precisão | |
|---|---:|---:|---:|---:|---|
| `caminho_exato` | 675 | 50 | 49 | **98,0%** | IC95% 94,1%–100% |
| `convencao/caminho_espelhado` | 50 | 50 | 42 | **84,0%** | censo, exato |
| `convencao/so_basename` | 43 | 43 | 20 | **46,5%** | censo, exato |
| **ponderado** | **768** | 143 | | **94,2%** | |

**`caminho_exato` é sólido.** O único erro dos 50 é o modo de falha previsto pelo
`getFileProduction`: `TestSchema` (de `exec.physical.impl`, no Drill) teve o `Test`
removido e a varredura por basename parou em `store/pcapng/schema/Schema.java`, de outro
pacote. Nome genérico, casado por nome de arquivo.

**Os 8 erros de `caminho_espelhado` são todos do Guava, e todos do mesmo tipo:** o
repositório mantém duas cópias de cada classe, uma JRE (`guava/src`) e uma Android
(`android/guava/src`), com o mesmo pacote Java. O binding cruzou as variantes — ligou o
teste Android à cópia JRE e vice-versa. Fora do Guava, o estrato não errou. É achado
específico de repositório com *flavors*, não falha geral da regra.

**`so_basename` não se sustenta: 46,5%.** Dos 23 erros, 15 são homônimo em outro pacote
(`admin.v1` × `admin.v2` no Pulsar, `mips` × `ppc` no binnavi, a interface
`com.ibm.dtfj.image.ImageFactory` × a implementação `...image.j9.ImageFactory` no OpenJ9) e
8 são testes que não mencionam a classe uma única vez. Os acertos são quase todos JDK e
libcore, onde a árvore de testes legitimamente não espelha a de produção.

> **Consequência prática.** `so_basename` são 43 dos 16.869 pares (0,25%) e 43 dos 768
> pares determinísticos (5,6%). Excluí-los sobe a precisão determinística de 94,2% para
> **97,0%** e custa pouquíssima cobertura. A coluna `evidencia` do `binding.csv` permite
> essa exclusão sem regerar nada — é decisão da análise, e está medida.
> (97,0% sobre os 725 pares restantes: 675 de `caminho_exato` e 50 de `caminho_espelhado`.)

Os três estratos de `referencia_estatica` (150 pares) seguem pendentes, e neles o critério
não é "a regra casou o arquivo certo" mas "referenciar conta como testar", que precisa ser
declarado antes de julgar.

---

## 6. As duas tabelas derivadas

`montar_analise.py` produz os **únicos artefatos derivados**, e eles são descartáveis.
`gerar_analises.py` roda as duas configurações oficiais de uma vez:

```bash
python tools/gerar_analises.py
```

```
dados/analise_deterministico.csv    730 linhas,   768 pares, 1,05 teste por arquivo
dados/analise_ampliado.csv        1.369 linhas, 3.335 pares, 2,44 testes por arquivo
```

### Por que duas, e não uma

Porque "este teste testa esta classe" tem duas respostas defensáveis, e **escolher entre
elas é decisão da análise, não da coleta**:

| | `analise_deterministico` | `analise_ampliado` |
|---|---|---|
| métodos | `caminho_exato` + `convencao` | + `referencia_estatica`, com `--max-testes 10` |
| regra | posição do arquivo pela convenção de nomenclatura | + o teste referencia estaticamente o tipo |
| julga intenção? | **não** — regra fechada, reexecutável | sim: referenciar não é testar |
| arquivos de produção | 730 | 1.369 |
| pares | 768 | 3.335 |
| testes por arquivo | 1,05 | 2,44 |

A determinística é a que se defende sem auditoria de intenção: ou o arquivo está onde a
convenção prevê, ou não está. A ampliada dobra a cobertura ao custo de um construto mais
frouxo.

**O que as duas têm em comum importa tanto quanto o que as separa:** o binding não desloca
a prevalência de code smell. Entre as amostras `HASH_OK`, as ligadas só pelas
determinísticas e as ligadas com a estratégia 3:

| | amostras | `pos_any` | `pos_maioria` | `pos_any_major` | `pos_unanime` |
|---|---:|---:|---:|---:|---:|
| HASH_OK (todas) | 4.300 | 1.116 (26,0%) | 225 (5,2%) | 719 (16,7%) | 17 (0,4%) |
| só determinísticas | 759 | 206 (27,1%) | 44 (5,8%) | 142 (18,7%) | 7 (0,9%) |
| com estratégia 3 | 1.611 | 438 (27,2%) | 93 (5,8%) | 286 (17,8%) | 10 (0,6%) |

Ligar ou não ligar é praticamente independente do rótulo (26,0% → 27,1% → 27,2%), o que
afasta a suspeita de que o binding ache teste mais facilmente para classe suja.

> **Prevalência igual não é resultado igual.** As duas diferem justamente no lado do
> desfecho: 768 pares contra 3.335, 1,05 contra 2,44 testes por arquivo. O test smell
> agregado vem de conjuntos de teste diferentes, e as duas podem dar respostas diferentes
> na etapa 3. É para isso que existem as duas — se o achado sobrevive às duas, é robusto à
> definição de binding; se não sobrevive, a diferença é resultado, não acidente.

E o "positivo confiável é escasso" não é limitação do binding: `maioria > none` rotula 5,2%
de **todo** o MLCQ (247 de 4.770). 759 × 5,8% = 44. Com `--rotulo sev_media` a pergunta
nem se coloca — todas as linhas ligadas entram, com severidade contínua.

### Nenhuma regra de rótulo fica congelada

Cada code smell aparece com **todas as regras lado a lado** — `cs_blob_any`,
`cs_blob_maioria`, `cs_blob_unanime`, `cs_blob_any_major`, `cs_blob_sev_media` — pelo mesmo
motivo que `mlcq_samples.csv` carrega as suas: a escolha é a decisão mais discutível do
dataset (seção 3) e não deve ficar enterrada num artefato. `cs_blob` é apelido da regra
pedida em `--rotulo`, para quem quer uma coluna só.

Pelo mesmo motivo o defeito de classe aninhada entra como **coluna**
(`n_testes_nome_divergente`) em vez de filtro: excluir na geração é irreversível, e
General Fixture continua confiável nessas linhas. Análise que envolva Eager/Lazy Test tem
que filtrar ou estratificar por ela — ou regerar com `--excluir-nome-divergente`.

### Proveniência

Cada CSV sai com um `.params.txt` ao lado contendo a linha de comando exata, o commit do
repositório (marcado se `tools/` tinha mudança não commitada), a versão do Python, o
**sha256 de cada entrada** (`mlcq_samples.csv`, `test_classes.csv`, `binding.csv`), a
cobertura resultante e os pares descartados por filtro. Sem o hash das entradas,
"repetível" é promessa; com ele, quem repetir sabe se partiu do mesmo dado.

### Outras configurações

```bash
python tools/montar_analise.py --rotulo maioria --agregacao densidade
python tools/montar_analise.py --metodos caminho_exato --excluir-nome-divergente
python tools/montar_analise.py --max-testes 5 --saida analise_max5.csv
```

| parâmetro | opções |
|---|---|
| `--rotulo` | `any`, `maioria` (padrão), `unanime`, `any_major`, `sev_media` |
| `--agregacao` | `soma` (padrão), `max`, `media`, `densidade` (por método de teste) |
| `--metodos` | um ou mais de `caminho_exato`, `convencao`, `referencia_estatica` |
| `--max-testes` | descarta produção com mais de N testes ligados |
| `--excluir-nome-divergente` | ignora as classes afetadas pelo defeito de classe aninhada |
| `--estratos` | quais estratos de evidência incluir |

O padrão é `maioria` porque é a única regra que usa o veredito do crosscheck. **Não é a
regra certa — é a menos circular.** Para um estudo de correlação, `--rotulo sev_media` é
provavelmente melhor que qualquer dicotomização: usa as 14.739 revisões, preserva todas as
linhas ligadas e elimina a discussão de limiar. As dicotomizações entram como análise de
sensibilidade.

### Duas armadilhas que a tabela evita

**"Não anotado" não é "negativo".** O MLCQ anotou amostras específicas para smells
específicos: um arquivo avaliado para `blob` não diz nada sobre `data class`. Cada code
smell tem coluna própria com três estados — vazio (não avaliado), 0 (avaliado, negativo
pela regra escolhida) e 1 (positivo). Tratar vazio como 0 inventaria milhares de negativos.

**Smells de método agregados para a classe.** `long method` e `feature envy` são anotados
por função, e a unidade do estudo é a classe: várias amostras de função colapsam num
arquivo de produção, e `n_amostras` registra quantas.

---

## 7. Dicionário de colunas

Toda coluna de todo artefato. `path` e `production_path` são sempre **relativos à raiz do
repositório, com barra inicial e barras normais** — o mesmo formato do campo `path` do
MLCQ.

### `mlcq_reviews.csv` — 1 linha por revisão

| coluna | conteúdo |
|---|---|
| `review_id` | `id` da planilha do MLCQ |
| `sample_id` | amostra revisada; junta com `mlcq_samples.csv` |
| `reviewer_id` | revisor (26 no total no MLCQ) |
| `smell` | `blob`, `data class`, `feature envy` ou `long method` |
| `severidade` | `none`, `minor`, `major`, `critical` |
| `severidade_num` | 0–3, na ordem acima |
| `review_timestamp` | data/hora da revisão |
| `is_crosscheck` | 1 se a revisão é de 26.07.2019 em diante (fase 4 do MLCQ, seção 3) |

### `mlcq_samples.csv` — 1 linha por amostra

| coluna | conteúdo |
|---|---|
| `sample_id` | identidade da amostra |
| `smell` | o code smell avaliado nesta amostra |
| `granularidade` | `class` (blob, data class) ou `function` (feature envy, long method) |
| `code_name` | nome qualificado do elemento, como o MLCQ traz |
| `path` | arquivo de produção, relativo ao repositório |
| `start_line`, `end_line` | faixa do elemento anotado |
| `mlcq_repo` | `owner/repo` original do MLCQ |
| `github_repo` | espelho correspondente, do `repos_map` do step 1 |
| `repo_status` | `HASH_OK`, `NOME_HASH_DIVERGE` ou `SEM_REPO` (step 1) |
| `commit_hash` | commit rotulado pelo MLCQ |
| `is_industry_relevant` | flag do MLCQ |
| `n_reviews` | quantas revisões esta amostra recebeu |
| `n_revisores` | revisores distintos (difere de `n_reviews` se alguém revisou duas vezes) |
| `severidades` | todas as severidades, decrescente, separadas por `\|` |
| `n_positivos` | revisões com severidade > `none` |
| `n_major_ou_mais` | revisões com severidade ≥ `major` |
| `n_reviews_crosscheck` | revisões na fase 4 |
| `sev_max` | maior severidade (0–3) |
| `sev_media` | média das severidades |
| `sev_mediana` | mediana; com N par cai no meio ponto, e isso é informação |
| `pos_any` | 1 se alguém marcou > `none` — **circular com o desenho amostral, ver seção 3** |
| `pos_maioria` | 1 se a maioria marcou > `none` |
| `pos_unanime` | 1 se todos marcaram > `none` (19 amostras em todo o MLCQ) |
| `pos_any_major` | 1 se alguém marcou ≥ `major` |
| `foi_crosscheck` | 1 se tem alguma revisão da fase 4 |
| `estrato` | `negativo_confiavel`, `disputado`, `positivo_confiavel`, `negativo_1_review` |

> **Nenhuma coluna `pos_*` é "o" rótulo.** A escolha é parâmetro de `montar_analise.py`.

### `test_classes.csv` — 1 linha por classe de teste

| coluna | conteúdo |
|---|---|
| `github_repo` | espelho (o campo `App` do JNose) |
| `path` | arquivo de teste, relativo ao repositório |
| `nome_arquivo` | basename sem `.java` — **o nome correto** |
| `nome_jnose` | o `TestFileName` que o JNose reportou |
| `nome_divergente` | 1 quando os dois diferem → defeito de classe aninhada (seção 2) |
| `production_path` | arquivo de produção que o JNose resolveu; vazio em 53,6% |
| `tem_production` | 1 se `production_path` está preenchido |
| `loc` | linhas da classe de teste |
| `n_metodos` | métodos da classe de teste |
| `ts_assertion_roulette` … `ts_verbose_test` | **13 colunas**, contagem de cada test smell habilitado |
| `n_smells_distintos` | quantos dos 13 têm contagem > 0 |
| `n_smells_total` | soma das 13 contagens |

### `test_smell_occurrences.csv.gz` — 1 linha por ocorrência

| coluna | conteúdo |
|---|---|
| `github_repo`, `path`, `nome_arquivo`, `production_path` | como em `test_classes.csv` |
| `junit` | `JUnit3`, `JUnit4` ou `JUnit5`, detectado pelo JNose |
| `loc`, `n_metodos` | da classe de teste |
| `smell` | qual dos 13 |
| `metodo` | método de teste onde o smell ocorre (`testSmellMethod`) |
| `linha_inicio`, `linha_fim` | faixa de linhas da ocorrência |
| `method_name_hash`, `method_name_full_hash`, `method_code_hash`, `full_hash` | hashes do JNose, para deduplicar |

> O campo `methodCode` do step 1 **não** é copiado (é quase todo o 1,4 GB). Os hashes ficam
> e o step 1 continua sendo a fonte do código.

### `binding.csv` — 1 linha por par (produção, teste)

| coluna | conteúdo |
|---|---|
| `github_repo` | espelho |
| `production_path` | arquivo de produção anotado no MLCQ |
| `test_path` | classe de teste ligada a ele |
| `metodo` | `caminho_exato`, `convencao` ou `referencia_estatica` |
| `evidencia` | só para `convencao`: `caminho_espelhado` (mesmo pacote) ou `so_basename` (só o nome coincide). Vazio nos outros métodos — a evidência da estratégia 3 mora em `refs_producao.csv` |
| `ambiguo` | 1 se aquele método ligou **mais de uma classe de teste** a esta produção. Não é erro — uma classe pode ter vários testes — e **não** significa "escolheu o arquivo errado" |
| `n_candidatos` | quantas classes de teste aquele método ligou a esta produção |

### `production_files.csv` — 1 linha por arquivo de produção anotado

| coluna | conteúdo |
|---|---|
| `github_repo`, `production_path` | o arquivo |
| `n_amostras` | amostras do MLCQ que caem nele (várias, para smells de método) |
| `sample_ids` | os `sample_id`, separados por `\|` |
| `smells` | code smells avaliados nele, separados por `\|` |
| `estratos` | estratos dessas amostras, separados por `\|` |
| `sev_max` | maior severidade entre as amostras dele |
| `repo_status` | status do espelho |
| `n_testes` | classes de teste ligadas (0 se nenhuma) |
| `metodos` | métodos de binding que funcionaram, separados por `\|` |
| `motivo_sem_ligacao` | vazio se ligado; senão `sem_ligacao_resolvida`, `repo_indisponivel` ou `projeto_sem_classe_de_teste` |

### `refs_producao.csv` — estratégia 3, 1 linha por par com evidência

| coluna | conteúdo |
|---|---|
| `github_repo`, `production_path`, `test_path` | o par |
| `evidencia` | `import_fqn`, `wildcard` ou `mesmo_pacote` (seção 4) |

### `refs_log.csv` — 1 linha por repositório processado

| coluna | conteúdo |
|---|---|
| `github_repo` | espelho |
| `status` | `OK` ou `ERRO` |
| `n_producao` | arquivos de produção anotados buscados neste repositório |
| `n_testes` | classes de teste examinadas |
| `n_pares` | pares encontrados |
| `segundos` | duração |
| `detalhe` | mensagem de erro, ou quantos arquivos de produção não existiam no clone |

É o análogo do `run_log.csv` do step 1, e é o que torna a estratégia 3 retomável:
repositórios com status `OK` são pulados na execução seguinte.

### `auditoria_binding.csv` — planilha de auditoria manual

| coluna | conteúdo |
|---|---|
| `correto` | **preencher à mão**: `s`, `n` ou `?` |
| `observacao` | livre |
| `estrato_auditoria` | `metodo` ou `metodo/evidencia` |
| `peso_no_universo` | fração do `binding.csv` que este estrato representa; `--apurar` usa para a precisão global |
| `github_repo`, `production_path`, `test_path`, `metodo`, `evidencia` | o par |
| `ambiguo`, `n_testes_da_producao` | sinais de risco |
| `url_producao`, `url_teste` | links no espelho, **no commit da coleta** |

### `analise_deterministico.csv` e `analise_ampliado.csv` — derivados

Mesmas colunas nos dois; muda só qual binding alimentou as linhas (seção 6).

| coluna | conteúdo |
|---|---|
| `github_repo`, `production_path` | o arquivo de produção |
| `estratos`, `n_amostras` | de onde vêm os rótulos |
| `cs_blob`, `cs_data_class`, `cs_feature_envy`, `cs_long_method` | apelido da regra pedida em `--rotulo`. **Vazio = não avaliado, nunca 0** |
| `cs_<smell>_any`, `_maioria`, `_unanime`, `_any_major`, `_sev_media` | **todas as regras de rótulo lado a lado**, para a etapa 3 escolher sem regerar |
| `cs_*_sev_max`, `cs_*_n_reviews` | evidência por trás dos rótulos |
| `n_testes`, `test_paths` | classes de teste agregadas |
| `n_testes_nome_divergente` | quantas delas têm o nome corrompido pelo defeito de classe aninhada. **Filtrar ou estratificar por esta coluna é obrigatório em análise com Eager/Lazy Test** |
| `loc_teste`, `n_metodos_teste` | totais do lado do teste; `n_metodos_teste` é o denominador de `--agregacao densidade` |
| `ts_*` (13), `ts_n_distintos`, `ts_n_total` | test smells agregados pela regra de `--agregacao` |

O `.params.txt` ao lado traz comando, commit, versão do Python, sha256 das entradas,
cobertura e descartes.

---

## 8. Conferir os números

Todo número afirmado neste README sai de um comando:

```bash
python tools/conferir_dados.py            # tudo
python tools/conferir_dados.py --secao 3  # só a seção 3
```

O script separa **pressupostos** de **descritivos**. Os cinco pressupostos — se algum
falhar, algum script do step 2 está silenciosamente errado e o comando termina com
código 1:

| pressuposto | estado |
|---|---|
| as 8 colunas de smell desabilitadas estão todas zeradas | ok |
| `byclasstest` sem `(repo, caminho)` duplicado | ok — 107.535 linhas, 107.535 chaves |
| todo `productionFile` reduz a caminho relativo | ok — 49.903 preenchidos, 0 irreconhecíveis |
| todo `App` do `byclasstest` está no `repos_map` do step 1 | ok — 430 Apps, 0 fora |
| toda amostra crosscheckada já era positiva antes do corte | ok — 1.227 de 1.227 |

O resto são as tabelas das seções 2, 3 e 4. Três números conferem contra o README do
step 1 de forma independente — `nome_divergente` (6.842), `production` preenchido (49.903)
e as taxas por mil de Eager/Lazy/General Fixture nos dois grupos de nome — o que valida a
normalização.

---

## 9. Estrutura

```
step2-binding/
├── README.md
├── tools/
│   ├── comum.py               caminhos, repos_map, normalizacao de caminho
│   ├── normalizar_mlcq.py     -> mlcq_reviews.csv, mlcq_samples.csv
│   ├── normalizar_jnose.py    -> test_classes.csv, test_smell_occurrences.csv.gz
│   ├── refs_producao.py       estrategia 3: clona e extrai referencias test -> producao
│   ├── binding.py             -> binding.csv, production_files.csv
│   ├── auditar_binding.py     sorteia e apura a auditoria de precisao
│   ├── montar_analise.py      -> uma tabela de analise (derivado, parametrizado)
│   ├── gerar_analises.py      -> as DUAS tabelas oficiais de uma vez
│   ├── baixar_auditoria.py    baixa os arquivos dos pares sorteados (cache local)
│   ├── dossie_auditoria.py    monta a evidencia de cada par para a conferencia
│   ├── registrar_auditoria.py grava vereditos incrementalmente
│   └── conferir_dados.py      reapura todo numero deste README
└── dados/
    ├── mlcq_reviews.csv              14.739 linhas
    ├── mlcq_samples.csv               4.770 linhas
    ├── test_classes.csv             107.535 linhas
    ├── test_smell_occurrences.csv.gz  2.059.905 linhas (versionado em 3 partes)
    ├── refs_producao.csv             pares da estrategia 3
    ├── refs_log.csv                  1 linha por repositorio (retomavel)
    ├── binding.csv                   pares (producao, teste) com metodo
    ├── production_files.csv           4.559 arquivos anotados, ligados ou nao
    ├── auditoria_binding.csv         planilha de auditoria manual
    ├── analise_deterministico.csv    derivado: caminho_exato + convencao
    └── analise_ampliado.csv          derivado: + referencia_estatica, max 10 testes
```

**Fonte de verdade são os CSVs normalizados e o `binding.csv`.** As duas tabelas de
análise são regeneráveis por `gerar_analises.py` em segundos.

---

## 10. Reproduzir do zero

```bash
# 1. normalizar os dois lados
python tools/normalizar_mlcq.py
python tools/normalizar_jnose.py          # --so-classes para pular as 2M ocorrencias

# 2. binding com as duas estrategias baratas
python tools/binding.py

# 3. estrategia 3 (retomavel, pula o que ja esta OK no refs_log.csv)
python tools/refs_producao.py

# 4. incorporar a estrategia 3
python tools/binding.py

# 5. auditar a precisao (trabalho manual)
python tools/auditar_binding.py           # sorteia 250 pares estratificados
python tools/baixar_auditoria.py          # baixa os 420 arquivos para cache local
python tools/dossie_auditoria.py --de 1 --ate 25   # evidencia de cada par
#    preencher a coluna correto em dados/auditoria_binding.csv
python tools/auditar_binding.py --apurar

# 6. gerar as duas tabelas de analise
python tools/gerar_analises.py

# 7. conferir que todo numero do README ainda vale
python tools/conferir_dados.py
```

Os passos 1, 2 e 4 levam segundos (o 1 completo, ~1,5 min pelas ocorrências). O passo 3 é
o único longo — 2 a 15 s por repositório com o clone esparso — e é retomável: repositórios
já `OK` no `refs_log.csv` são pulados, interromper e reexecutar é seguro, e os clones são
removidos após cada repositório.

`binding.py` é rodado duas vezes de propósito: ele incorpora `refs_producao.csv` se o
arquivo existir e avisa qual situação encontrou.

O passo 5 é o único que exige trabalho humano. `baixar_auditoria.py` e
`dossie_auditoria.py` existem para baratear esse trabalho, não para substituí-lo: o
primeiro busca os dois arquivos de cada par uma vez (cache em `.cache-auditoria/`, fora do
git, retomável — arquivo já baixado é pulado), e o segundo mostra, para cada par, em que
linhas do teste o tipo de produção aparece e o que essas linhas fazem com ele. Nenhum dos
dois emite veredito; o julgamento é de quem audita.

---

## 11. Ressalvas conhecidas

- **Cobertura de 37,5% com as três estratégias** (17,7% sem a estratégia 3). Os 62,5%
  restantes são, em parte, classes genuinamente sem teste e, em parte, falha do método —
  `production_files.csv` separa os dois casos até onde é possível separar.
- **`positivo_confiavel` tem 93 amostras** (44 antes da estratégia 3). Dá para análise
  agregada; para análise por smell individual, feature envy segue sendo o caso magro.
- **`caminho_exato` tem ausência não-aleatória**, concentrada nas classes aninhadas
  (`nome_divergente`), que é onde o `jnose-core` falha ao resolver a produção.
- **`caminho_exato` não é oráculo validado.** O `getFileProduction` do `jnose-core` é
  convenção de nomenclatura mais busca por basename (seção 4) — o que a literatura validou
  no JNose é a detecção de test smells, não a resolução da classe de produção. A regra é
  determinística e declarável; só não pode ser citada como chancela externa.
- **A `analise_ampliado` inclui, e a `analise_deterministico` não, pares em que o teste
  apenas referencia a classe.** Nenhuma das duas é "a certa": a diferença entre elas é
  informação para a etapa 3, e é por isso que as duas são versionadas.
- **`referencia_estatica` confunde referenciar com testar.** Sem filtro a concentração é de
  10,9 testes por arquivo de produção, implausível como teste dedicado. Mede-se com a
  auditoria da seção 5; mitiga-se com `--max-testes 10`, que a derruba para 2,4. Não se
  elimina.
- **A auditoria está pela metade: 143 dos 293 pares.** Os três estratos determinísticos
  estão apurados (seção 5); os 150 de `referencia_estatica` não. Enquanto isso, nenhuma
  afirmação de precisão vale para a `analise_ampliado.csv`, e a tabela de trade-off da
  seção 4 mede concentração, não precisão.
- **O julgamento dos 143 foi automatizado, não humano.** Feito a partir do dossiê de cada
  par (pacote dos dois lados, imports, e as linhas do teste que citam o tipo), gravado em
  `auditoria_binding_auto.csv`, que é arquivo separado da planilha humana justamente para a
  distinção não se perder. O artigo deve descrevê-lo como primeira passada automatizada,
  conferida por amostragem — não como auditoria independente. Ver
  `NOTAS-METODOLOGICAS.md`, seção 9.
- **Em `referencia_estatica` o critério ainda não está fechado.** Nas determinísticas a
  pergunta é "a regra casou o arquivo certo?", que é objetiva. Ali é "referenciar conta
  como testar?", que exige arbitrar e precisa ser declarado no artigo antes de julgar.
- **Eager Test e Lazy Test não são confiáveis nas linhas `nome_divergente`** (queda de 28×
  e 23× no step 1). General Fixture fica estável e serve como controle.
- **O padrão `^.*test\d*$` do JNose** casa palavras que terminam em "test" sem serem testes
  (`Latest`, `Contest`); herdado do step 1.
- **`mesmo_pacote` casa identificador solto** e pode ligar um `<Tipo>` homônimo de outro
  pacote. É o estrato de auditoria com maior risco esperado.
- **`convencao/so_basename` (43 pares) casa `XTest` de qualquer pacote do repositório.**
  Contém erro comprovado (`NorTranslator` de `/mips` com o teste de `/ppc`) e também
  ligação legítima (árvore de testes do JDK). Os dois estratos de `convencao` são
  auditados por censo, então esse risco sai medido exatamente.
