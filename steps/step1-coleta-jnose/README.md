# Step 1 — Coleta de test smells com o JNose

Extração de test smells dos repositórios do dataset **MLCQ** usando o **JNose Test 2.5.0**.

Entrada: `MLCQ/MLCQCodeSmellSamples.xlsx`
Saída: `reports/bytestsmells/` (uma linha por ocorrência de smell) e `reports/byclasstest/` (uma linha por classe de teste)

| | |
|---|---|
| Repositórios no MLCQ | 522 |
| Analisados (`HASH_OK`) | **451 (100% dos elegíveis)** |
| Ocorrências de smell coletadas | 2.059.905 |
| Classes de teste | 107.535 |
| Smells habilitados | 13 |
| Tempo total de execução | ~34,7 h |

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
| `JAVA_EXE` | `C:\Program Files\Java\jdk-26.0.2\bin\java.exe` |
| `JNOSE_PROJECTS` | `~/.jnose_projects` (onde os clones são feitos) |
| `JNOSE_URL` | `http://localhost:8080` |
| `JNOSE_TIMEOUT` | `1200` (segundos por análise) |
| `JNOSE_JANELA_MORTO` | `180` (ver seção 4) |

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
python tools/jnose_batch.py              # todos os HASH_OK ainda não concluídos
python tools/jnose_batch.py --pendentes  # reprocessa tudo que não terminou OK
python tools/jnose_batch.py storm        # filtra pelo nome do repositório
python tools/jnose_batch.py 10           # limita a quantidade
```

Para cada repositório, em sequência:

1. `git clone --depth 1` do espelho e conferência do HEAD contra o commit esperado
   (divergência ⇒ `MISMATCH`, repositório pulado);
2. remoção dos arquivos que travariam o JNose (**seção 4**);
3. detecção da versão de JUnit do projeto;
4. inserção do projeto direto no `jnose.db` via SQLite;
5. disparo da análise das páginas `bytestsmells` e `byclasstest`, com polling até 100%;
6. exportação dos CSVs;
7. remoção do clone e da linha do projeto no banco.

O JNose é reiniciado a cada 15 repositórios (não libera memória entre análises) e
sempre que uma análise falha. Cada execução registra uma linha em
`reports/run_log.csv`.

### Dois defeitos do JNose contornados pelo script

- **Aba *Projects* quebrada** (incompatibilidade github-api × Jackson): não é possível
  cadastrar projeto pela interface. O script insere a linha direto no `jnose.db`.
- **Configuração de smells só em memória**: a seleção dos 13 smells é perdida a cada
  reinício. O script reaplica e **verifica** a cada execução, abortando se divergir.

### Smells habilitados (13)

`AssertionRoulette`, `ConditionalTestLogic`, `DependentTest`, `DuplicateAssert`,
`EagerTest`, `ExceptionCatchingThrowing`, `GeneralFixture`, `LazyTest`,
`MagicNumberTest`, `MysteryGuest`, `RedundantAssertion`, `ResourceOptimism`,
`VerboseTest`.

Os CSVs trazem colunas para todos os smells que o JNose conhece; as não habilitadas
ficam zeradas.

---

## 4. O defeito que travava a coleta

Onze repositórios nunca terminavam: a interface ficava parada em **25%**
indefinidamente. Um deles (`apache/storm`) chegou a rodar 14 horas antes de ser
interrompido. Diagnóstico e correção:

### Causa

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

Logo, um arquivo que case pelo nome, importe JUnit e **não declare nenhuma `class` ou
`interface` no nível de topo** deixa `TestClass.name` nulo. Em seguida
`JNoseCallable.call` faz `getName().toLowerCase()` e lança `NullPointerException`. O
`JNose.processarProjetos` captura a exceção num `catch (Exception)` que apenas registra
no log e segue:

```java
try { processarProjeto(p); }
catch (Exception e) { LOGGER.log(SEVERE, "Failed processing project: " + p.getName(), e); }
```

`setProcessado(true)` nunca é chamado, a porcentagem congela em 25 e o link de
resultado nunca ganha `href`. **A tela de um projeto morto é idêntica à de um projeto
processando.**

O "25%" é um marcador de estágio fixo no código, não progresso — `processarProjeto`
faz `setProcentagem(25)`, chama `getFilesTest()` e faz `setProcentagem(100)`. Por isso
aumentar o timeout (600 s → 1200 s → 5400 s) nunca resolveu: o trabalho já havia
abortado nos primeiros segundos.

Os arquivos culpados não são classes de teste: anotações de `@Category`/`@Tag`
(`DockerTest.java`, `SpringBootTest.java`, `GemFireUnitTest.java`), enums
(`TestEnum.java`) e um arquivo do visualvm com a classe inteira comentada.

### Correção

`remover_testes_sem_classe()` apaga do clone, antes da análise, os arquivos que
satisfazem as duas condições simultaneamente: **casam com um dos seis padrões de nome**
e **têm import de JUnit** e **não declaram `class`/`interface` no topo**. Como esses
arquivos jamais gerariam um `TestClass`, removê-los não altera o resultado — apenas
evita o NPE. Foram **46 arquivos em 12 repositórios**, registrados na coluna `detalhe`
do `run_log.csv`.

### Detecção de análise morta

Como o JNose não sinaliza a falha, o script passou a distinguir "trabalhando" de
"morreu" olhando o processo: a cada 180 s sem conclusão, se a JVM gastou menos de 2 s
de CPU na janela **e** o `jstack` não mostra nenhum frame `io.github.arieslab`, a
análise é dada como morta (status `MORTO`). Os dois sinais juntos porque nenhum
sozinho é seguro — o `jstack` pode falhar, e uma análise legítima parada em I/O
enganaria o critério de CPU.

O limiar é conservador: a análise bem-sucedida mais lenta de todo o dataset levou
420 s **de trabalho real**, e uma análise viva queima CPU continuamente. Falha em
~3 min em vez de 90.

### Validação do filtro contra um oráculo

O filtro é heurística de texto (ignora comentários e literais, procura declaração de
topo). Heurística de texto erra — durante o desenvolvimento errou duas vezes, uma
delas removendo interfaces legítimas. Por isso existe o `AchaNulos.java`, que usa o
**mesmo `javaparser-core` de dentro do jar do JNose** e replica a travessia do
`flowClass` nó a nó, decidindo pelo AST:

```bash
python tools/validar_filtro.py            # os 12 repositórios que precisaram do filtro
python tools/validar_filtro.py --todos    # todos os 451 (lento: ~450 clones)
```

Resultado nos 12: **filtro e oráculo coincidem em todos**. Além disso, a contagem
fecha exatamente — para cada repositório, `oráculo + sem_junit = arquivos realmente
removidos`. Ou seja, dos 46 arquivos removidos, 25 causavam mesmo o NPE e 21 não
tinham import de JUnit (o `isTestFile` os rejeitaria de qualquer forma, então removê-los
foi desnecessário porém comprovadamente inócuo).

### Terceiro defeito: o JNose tranca os próprios clones

A `ProjetosPage` abre um repositório jgit para cada diretório sob a pasta de projetos,
e o jgit mantém o `.pack` aberto no Windows — impedindo apagar o clone depois. Por isso
os health checks do script usam `/config`, nunca `/projects`.

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
│   ├── jnose_batch.py        orquestra a coleta
│   ├── mapear_repos.py       gera dados/repos_map.csv (--conferir para validar)
│   ├── validar_filtro.py     compara o filtro com o oráculo
│   └── AchaNulos.java        oráculo: JavaParser + travessia do flowClass
├── dados/
│   ├── repos_map.csv         522 repos do MLCQ e seus espelhos
│   ├── piloto.csv            execução piloto (Shopify/graphql_java_gen)
│   └── proveniencia/         artefatos do mapeamento
└── reports/
    ├── bytestsmells/         451 CSVs .gz — uma linha por ocorrência de smell
    ├── byclasstest/          451 CSVs — uma linha por classe de teste
    ├── run_log.csv           481 tentativas: status, contagens, tempo, detalhe
    ├── logs/                 saída dos passes de execução
    └── console-jnose/        stdout/stderr do JNose .gz (evidência do NPE)
```

`reports/bytestsmells/` está comprimido (1,4 GB → 160 MB). Para ler:

```bash
gunzip -k reports/bytestsmells/apache__hadoop.csv.gz
```
```python
import pandas as pd
df = pd.read_csv("reports/bytestsmells/apache__hadoop.csv.gz", sep=";")  # lê .gz direto
```

### `run_log.csv`

Uma linha por tentativa (481 no total; 451 repositórios × novas tentativas dos que
falharam antes da correção).

| Coluna | Conteúdo |
|---|---|
| `mlcq_repo`, `github_repo` | repositório e espelho |
| `commit_esperado`, `commit_clonado` | conferência do commit |
| `junit` | versão detectada pelo script |
| `status` | `OK`, `MORTO`, `TIMEOUT`, `ERRO`, `MISMATCH` |
| `linhas_bytestsmells`, `linhas_byclasstest` | linhas exportadas |
| `segundos` | duração da tentativa |
| `detalhe` | mensagem de erro, ou quantos arquivos foram removidos |

Os status `MORTO`, `TIMEOUT` e `ERRO` presentes no histórico são de tentativas
**anteriores** à correção. O estado final é 451/451 `OK`.

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

# 4. coletar (~35 h; retomável — pula o que já está OK no run_log)
python tools/jnose_batch.py

# 5. conferir o filtro contra o oráculo
python tools/validar_filtro.py
```

A coleta é retomável: o `run_log.csv` é lido no início e repositórios já `OK` são
pulados. Interromper e reexecutar é seguro.

**Requisitos de disco:** os clones são temporários (removidos após cada análise), mas o
maior repositório do lote precisa de alguns GB livres em `JNOSE_PROJECTS`.
