# Step 1 — Coleta de test smells com o JNose

Extração de test smells dos repositórios do dataset **MLCQ** usando o **JNose Test 2.5.0**.

Entrada: `MLCQ/MLCQCodeSmellSamples.xlsx`
Saída: `reports/bytestsmells/` (uma linha por ocorrência de smell) e `reports/byclasstest/` (uma linha por classe de teste)

| | |
|---|---|
| Repositórios no MLCQ | 522 |
| Analisados (`HASH_OK`) | **451 (100% dos elegíveis)** |
| Ocorrências de smell coletadas | 2.150.044 |
| Classes de teste | 107.535 |
| Smells habilitados | 20 (a configuração padrão do JNose menos o Unknown Test) |
| Tempo total de execução | ~4,4 h |

Todo número deste README é reapurado por `python tools/conferir_coleta.py` (seção 7).

---

## 1. Ambiente

| Componente | Versão |
|---|---|
| Sistema | Windows 10 Enterprise 19045 |
| Python | 3.12.10 (`requests`, `openpyxl`) |
| JDK | 26.0.2 |
| JNose Test | 2.5.0 (`apps/jnose-tests-smell.zip`) |
| jnose-core (dentro do jar) | 0.9.4 |
| javaparser-core (dentro do jar) | 3.3.5 |

O JNose sobe como aplicação Spring Boot em `http://localhost:8080`, com heap limitado:

```bash
java -Xmx2g -Djavax.net.ssl.trustStoreType=WINDOWS-ROOT -jar jnose-2.5.0.jar
```

O `-Xmx2g` é necessário: sem limite, a JVM cresce ao longo do lote até sufocar a máquina.
O `trustStoreType=WINDOWS-ROOT` evita falha de TLS ao acessar o GitHub.

Os scripts localizam entradas e saídas relativamente à pasta do step. Os caminhos de
máquina são ajustáveis por variável de ambiente:

| Variável | Padrão |
|---|---|
| `JNOSE_DIR` | `C:\Users\crist\Documents\Mestrado PPGCC\jnose-tests-smell` |
| `JAVA_EXE` | `C:\Program Files\Java\jdk-26.0.2\bin\java.exe` (o `javac.exe` ao lado também é usado) |
| `JNOSE_PROJECTS` | `~/.jnose_projects` (onde os clones são feitos) |
| `JNOSE_URL` | `http://localhost:8080` |
| `JNOSE_TIMEOUT` | `1200` (segundos por análise) |
| `JNOSE_JANELA_MORTO` | `180` (ver seção 4.1) |

---

## 2. Seleção dos repositórios

O MLCQ referencia repositórios de terceiros em um commit específico. Como esses
repositórios mudam ou desaparecem, o experimento usa **espelhos sob a conta
`github.com/cristianritter`**, criados no commit de interesse. O
`dados/repos_map.csv` liga um ao outro.

```bash
python tools/mapear_repos.py --conferir   # confere que o CSV em disco é reproduzível
python tools/mapear_repos.py              # regera o CSV
```

O casamento roda em três passadas, nesta ordem:

1. **Por hash** — o HEAD do espelho é igual ao `commit_hash` do MLCQ. É o critério mais
   forte. Resolve nomes que não se parecem (`SAP/iot-starterkit` →
   `test-smells-cloud-platform-iot-starterkit`) e colisões que o nome erraria:
   `alibaba/atlas` e `apache/atlas` disputariam o mesmo `test-smells-atlas`.
2. **Por nome** — `test-smells-<repo>`, mais as resoluções registradas em
   `dados/proveniencia/matched.json` e `fuzzy.json`.
3. **Por sufixo único** — o espelho termina em `-<repo>` (`apache/fop` →
   `test-smells-xmlgraphics-fop`).

Resultado:

| Status | Repos | Entra na análise |
|---|---:|---|
| `HASH_OK` | 451 | sim |
| `NOME_HASH_DIVERGE` | 10 | não — espelho existe mas está em outro commit |
| `SEM_REPO` | 61 | não — nenhum espelho |

`dados/proveniencia/` guarda os artefatos capturados quando o mapeamento foi feito
(`mlcq_repos.json`, `gh_repos.json`, `matched.json`, `fuzzy.json`, `heads.txt`). O
script usa esses arquivos em vez de consultar a API do GitHub de novo — refazer as
chamadas hoje traria HEADs diferentes se algum espelho tiver recebido commits depois,
e o experimento precisa continuar reproduzindo o mesmo recorte.

---

## 3. Execução da coleta

```bash
python tools/jnose_batch.py                  # todos os HASH_OK ainda não concluídos
python tools/jnose_batch.py --pendentes      # reprocessa tudo que não terminou OK
python tools/jnose_batch.py storm            # filtra pelo nome do repositório
python tools/jnose_batch.py 10               # limita a quantidade
python tools/jnose_batch.py --config-padrao  # os 21 smells, em reports-config-padrao/ (seção 4.2)
```

Para cada repositório, em sequência:

1. `git clone --depth 1` do espelho e conferência do HEAD contra o commit esperado
   (divergência ⇒ `MISMATCH`, repositório pulado);
2. remoção dos arquivos que derrubariam a análise do JNose (**seção 4.1**);
3. detecção da versão de JUnit do projeto;
4. inserção do projeto direto no `jnose.db` via SQLite;
5. disparo da análise das páginas `bytestsmells` e `byclasstest`, com polling até 100%;
6. exportação dos CSVs (`bytestsmells` já sai comprimido em `.csv.gz`);
7. remoção do clone e da linha do projeto no banco.

O JNose é reiniciado a cada 15 repositórios (não libera memória entre análises) e
sempre que uma análise falha. A cada parada, o console do JNose é comprimido em
`reports/console-jnose/`. Cada tentativa registra uma linha em `reports/run_log.csv`.

### Dois defeitos do JNose contornados pelo script

- **Aba *Projects* quebrada** (incompatibilidade github-api × Jackson): não é possível
  cadastrar projeto pela interface. O script insere a linha direto no `jnose.db`.
- **Configuração de smells só em memória**: a seleção de smells é perdida a cada
  reinício. O script reaplica e **verifica** a cada execução, abortando se divergir.

### Smells habilitados (20)

`AssertionRoulette`, `ConditionalTestLogic`, `ConstructorInitialization`, `DefaultTest`,
`DependentTest`, `DuplicateAssert`, `EagerTest`, `EmptyTest`,
`ExceptionCatchingThrowing`, `GeneralFixture`, `IgnoredTest`, `LazyTest`,
`MagicNumberTest`, `MysteryGuest`, `PrintStatement`, `RedundantAssertion`,
`ResourceOptimism`, `SensitiveEquality`, `SleepyTest`, `VerboseTest`.

É a configuração padrão do JNose (`TestSmellDetectorConfig` liga os 21 smells que a
ferramenta conhece) menos o **Unknown Test**, cujo detector descarta a análise de classes
inteiras (seção 4.2). Usar a configuração padrão tira do pesquisador a escolha de quais
smells contam; a única exceção é um detector que corrompe os demais. Os CSVs trazem a
coluna do Unknown Test, zerada em todas as linhas.

---

## 4. Defeitos do JNose que afetam a coleta

### 4.1 Arquivo sem classe derruba a análise do projeto inteiro

#### Causa

O JNose seleciona candidatos a teste **pelo nome do arquivo**
(`JNoseCore.isPotentialTestFileName`, seis expressões aplicadas ao nome sem extensão,
em minúsculas):

```
^.*test\d*$    ^.*tests\d*$    ^.*testcase\d*$    ^test.*    ^tests.*    ^testcase.*
```

Depois, `isTestFile` aceita o arquivo **apenas com base nos imports de JUnit**, sem
verificar se o parser encontrou uma classe:

```java
detectJUnitVersion(cu.getImports(), testClass);          // org.junit.jupiter → JUnit5
for (NodeList<?> lista : cu.getNodeLists())              // org.junit         → JUnit4
    flowClass(lista, testClass);                         // junit.framework   → JUnit3
return junitVersion != null && junitVersion != None;     // não olha o nome
```

O nome só é preenchido dentro do `flowClass`, e **somente** para
`ClassOrInterfaceDeclaration` — que no JavaParser cobre `class` e `interface`, mas não
`@interface`, `enum` nem `record`, e o método não recursa por dentro desses nós:

```java
if (node instanceof ClassOrInterfaceDeclaration c) {
    testClass.setName(c.getNameAsString());
    flowClass(c.getMembers(), testClass);
}
```

Logo, um arquivo que case pelo nome, importe JUnit, seja parseável e **não declare
nenhuma `class` ou `interface` no nível de topo** deixa `TestClass.name` nulo. Em seguida
`JNoseCallable.call` faz `getName().toLowerCase()` e lança `NullPointerException`. O
`JNose.processarProjetos` captura a exceção num `catch (Exception)` que apenas registra
no log e segue:

```java
try { processarProjeto(p); }
catch (Exception e) { LOGGER.log(SEVERE, "Failed processing project: " + p.getName(), e); }
```

`setProcessado(true)` nunca é chamado, a porcentagem congela em 25 e o link de
resultado nunca ganha `href`. **A tela de um projeto morto é idêntica à de um projeto
processando**, e o projeto inteiro fica sem resultado, não só o arquivo.

O "25%" é um marcador de estágio fixo no código, não progresso — `processarProjeto`
faz `setProcentagem(25)`, chama `getFilesTest()` e faz `setProcentagem(100)`. Aumentar
o timeout não resolve: o trabalho já abortou nos primeiros segundos.

#### Correção

`remover_testes_sem_classe()` apaga do clone, antes da análise, exatamente os arquivos
que satisfariam essas condições. Quem decide não é uma heurística de texto: é o
`AchaNulos.java`, que roda com o **mesmo `javaparser-core` de dentro do jar do JNose** e
replica `isPotentialTestFileName`, `isTestFile` e a travessia do `flowClass` sobre o AST.
O script extrai o javaparser do jar e compila o oráculo em `.oraculo/` na primeira
chamada.

Um arquivo que o JavaParser não consegue parsear não entra: o JNose captura esse erro e
ignora o arquivo, sem derrubar o projeto. Como os arquivos removidos jamais gerariam um
`TestClass`, removê-los não tira nada da coleta — apenas evita o NPE. Foram **25 arquivos
em 11 repositórios**, registrados na coluna `detalhe` do `run_log.csv`.

#### Detecção de análise morta

Como o JNose não sinaliza falhas desse tipo, o script distingue "trabalhando" de
"morreu" olhando o processo: a cada 180 s sem conclusão, se a JVM gastou menos de 2 s
de CPU na janela **e** o `jstack` não mostra nenhum frame `io.github.arieslab`, a
análise é dada como morta (status `MORTO`). Os dois sinais juntos porque nenhum
sozinho é seguro — o `jstack` pode falhar, e uma análise legítima parada em I/O
enganaria o critério de CPU.

O limiar é conservador: a análise bem-sucedida mais lenta da coleta levou **230 s** no
total, e uma análise viva queima CPU continuamente.

#### O JNose tranca os próprios clones

A `ProjetosPage` abre um repositório jgit para cada diretório sob a pasta de projetos,
e o jgit mantém o `.pack` aberto no Windows — impedindo apagar o clone depois. Por isso
os health checks do script usam `/config`, nunca `/projects`.

### 4.2 O detector de Unknown Test zera classes inteiras

#### Causa

No jnose-core 0.9.4, o detector de Unknown Test (`UnknownTest.java`, linha 58) chama
`n.getBody().get()` sem verificar se o método tem corpo. Em método abstrato, o `Optional`
está vazio e a chamada lança `NoSuchElementException`. O JNose captura a exceção no nível
da classe e **descarta a análise da classe inteira, de todos os smells**: a classe sai no
`byclasstest` com todos os contadores zerados e some do `bytestsmells`.

#### Medida

A configuração padrão completa (21 smells) foi rodada nos mesmos 451 repositórios
(`jnose_batch.py --config-padrao`, em `reports-config-padrao/`). A única diferença entre
ela e a coleta do estudo é esse detector, e o JNose é determinístico: com a mesma
entrada, produz a mesma saída. Logo, toda diferença entre as duas é efeito dele.

```bash
python tools/efeito_unknown_test.py
```

compara as duas classe a classe, nos 20 smells em comum, e confere que a única diferença
é o efeito previsto pelo código:

| | |
|---|---:|
| Classes de teste | 107.535 |
| Classes zeradas pelo Unknown Test | **142 (0,13%)**, em 51 repositórios |
| Ocorrências dos outros 20 smells que a configuração padrão perderia | **5.500 (0,26%)** |
| Qualquer outra diferença (classes, LOC, métodos, produção, contagens) | nenhuma |

Por isso o Unknown Test fica de fora: ligado, ele não acrescenta um smell — apaga os
demais em classes com método abstrato. Só o `byclasstest` da configuração padrão é
versionado; o `bytestsmells` dela (185 MB) não entra na medida.

---

## 5. Limitação conhecida nos dados

**Não é um defeito da coleta, e afeta os 451 repositórios igualmente.** Está
documentada aqui porque muda a interpretação de `reports/byclasstest/`.

O `flowClass` não para na primeira classe: continua iterando e recursando, de modo que
a **última** `ClassOrInterfaceDeclaration` encontrada sobrescreve o nome. Em arquivos
com classe aninhada, o nome reportado é o do *helper*, não o da classe de teste:

```java
// GemfireRepositoriesRegistrarIntegrationTest.java
44: public class GemfireRepositoriesRegistrarIntegrationTest {   // a classe de teste
50:     static class Config {                                     // helper aninhado
```
→ linha no CSV: `TestFileName=Config`, `LOC=71`, `numberMethods=1`

**Alcance: 6.842 de 107.535 linhas (6,4%), em 320 dos 451 repositórios.**

O impacto não é cosmético: `ProductionFileName` é resolvido a partir desse nome, e
smells que dependem da classe de produção deixam de ser detectados.

| | linhas | production vazio | Eager Test /1k | Lazy Test /1k | General Fixture /1k |
|---|---:|---:|---:|---:|---:|
| nome bate com o arquivo | 100.693 | 50,9% | 1.138,9 | 1.189,0 | 280,1 |
| nome diverge (aninhada) | 6.842 | **93,8%** | **40,8** | **52,3** | 322,3 |

Eager Test cai 28× e Lazy Test 23×. O General Fixture fica estável, funcionando como
controle: o efeito é específico dos smells que precisam do código de produção.

**Como tratar na análise:** o nome correto é recuperável do `PathFile` (basename do
arquivo), então a identidade da classe pode ser corrigida *post hoc*. Os **valores de
smell** dessas linhas não são recuperáveis assim — ou elas são excluídas das análises
que envolvem Eager/Lazy Test, ou seria preciso corrigir o `jnose-core` e reprocessar.

### Outras ressalvas do JNose

- O padrão `^.*test\d*$` casa com palavras que terminam em "test" sem serem testes
  (`Latest`, `Contest`, `Fastest`). Um arquivo assim que importe JUnit entra na coleta.
- Versões de JUnit detectadas nos 451: JUnit4 (398), JUnit5 (36), JUnit3 (17).
  A detecção é por `contains` no nome do import, na ordem jupiter → org.junit →
  junit.framework.

---

## 6. Estrutura

```
step1-coleta-jnose/
├── README.md
├── tools/
│   ├── jnose_batch.py          orquestra a coleta
│   ├── AchaNulos.java          oráculo do filtro: JavaParser + travessia do flowClass
│   ├── mapear_repos.py         gera dados/repos_map.csv (--conferir para validar)
│   ├── efeito_unknown_test.py  mede o detector de Unknown Test (seção 4.2)
│   └── conferir_coleta.py      reapura todo número deste README
├── dados/
│   ├── repos_map.csv           522 repos do MLCQ e seus espelhos
│   ├── piloto.csv              execução piloto (Shopify/graphql_java_gen)
│   └── proveniencia/           artefatos do mapeamento
├── reports/                    a coleta do estudo (20 smells)
│   ├── bytestsmells/           451 CSVs .gz — uma linha por ocorrência de smell
│   ├── byclasstest/            451 CSVs — uma linha por classe de teste
│   ├── run_log.csv             uma linha por tentativa: status, contagens, tempo, detalhe
│   ├── logs/lote.log           saída do jnose_batch.py
│   └── console-jnose/          stdout/stderr do JNose, .gz
└── reports-config-padrao/      a configuração padrão (21 smells), só para a seção 4.2
    ├── byclasstest/            451 CSVs
    ├── run_log.csv
    ├── logs/lote.log
    └── console-jnose/
```

`reports/bytestsmells/` está comprimido (1,5 GB → 173 MB). Para ler:

```bash
gunzip -k reports/bytestsmells/apache__hadoop.csv.gz
```
```python
import pandas as pd
df = pd.read_csv("reports/bytestsmells/apache__hadoop.csv.gz", sep=";")  # lê .gz direto
```

### `run_log.csv`

Uma linha por tentativa, 455 no total; o estado de cada repositório é o da sua última
linha. O estado final é 451/451 `OK`.

| Coluna | Conteúdo |
|---|---|
| `mlcq_repo`, `github_repo` | repositório e espelho |
| `commit_esperado`, `commit_clonado` | conferência do commit |
| `junit` | versão detectada pelo script |
| `status` | `OK`, `MORTO`, `TIMEOUT`, `ERRO`, `MISMATCH` |
| `linhas_bytestsmells`, `linhas_byclasstest` | linhas exportadas |
| `segundos` | duração da tentativa |
| `detalhe` | mensagem de erro, ou quantos arquivos foram removidos |

---

## 7. Reproduzir do zero

```bash
# 1. descompactar o JNose
unzip apps/jnose-tests-smell.zip -d <destino>
export JNOSE_DIR=<destino>/jnose-tests-smell

# 2. conferir o mapeamento dos repositórios
python tools/mapear_repos.py --conferir     # deve imprimir "REPRODUZ o CSV em disco"

# 3. subir o JNose (o script sobe sozinho se estiver fora do ar)
java -Xmx2g -Djavax.net.ssl.trustStoreType=WINDOWS-ROOT -jar jnose-2.5.0.jar

# 4. coletar (~4,4 h; retomável — pula o que já está OK no run_log)
python tools/jnose_batch.py

# 5. só para a seção 4.2: a configuração padrão, nos mesmos repositórios
python tools/jnose_batch.py --config-padrao

# 6. conferir que todo número deste README ainda vale
python tools/conferir_coleta.py
```

O `conferir_coleta.py` lê só o que a coleta deixou em disco (`repos_map.csv`,
`run_log.csv`, `byclasstest/`, `bytestsmells/` e o `byclasstest/` da configuração padrão)
e falha com código 1 se algum número deste README divergir.

A coleta é retomável: o `run_log.csv` é lido no início e repositórios já `OK` são
pulados. Interromper e reexecutar é seguro.

**Requisitos de disco:** os clones são temporários (removidos após cada análise), mas o
maior repositório do lote precisa de alguns GB livres em `JNOSE_PROJECTS`.
