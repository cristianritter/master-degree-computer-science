# master-degree-computer-science

Estudo da relação entre code smell percebido por desenvolvedores (MLCQ) e test smell
(JNose) em projetos Java. Cada etapa mora em `steps/`, com README, scripts e dados.

## Reprodutibilidade

Todo número escrito na documentação sai de um comando versionado. Seis verificadores
garantem isso, e cada um termina com código 1 se encontrar divergência:

| comando | o que confere |
|---|---|
| `python steps/step1-coleta-jnose/tools/conferir_coleta.py` | os números do README do step 1 |
| `python steps/step2-binding/tools/conferir_dados.py` | os números do README e das notas do step 2 |
| `python steps/step3-analise/tools/conferir_resultados.py` | os números dos READMEs do step 3 |
| `python steps/step3-analise/tools/validar_estat.py` | que as estatísticas implementadas no step 3 batem com o scipy, nos dados reais |
| `python artigo/tools/folha_de_fatos.py --conferir` | que `artigo/folha-de-fatos.md` e `artigo/latex/fatos.tex` estão em dia com os dados, e que o texto do artigo não tem número digitado |
| `python steps/conferir_cobertura.py` | que nenhum número dos documentos (steps e `artigo/`) fique sem origem em algum comando |

Os três primeiros conferem valores, e o quarto confere as fórmulas que os produzem. O
quinto mantém a folha de fatos, de onde o artigo tira cada número por macro, sem digitar
nenhum. O último confere cobertura: procura números que nenhum comando produz, ou seja,
que só poderiam ter sido digitados à mão. Os números que
não são dados do estudo (anos, referências, configuração) ficam em
`steps/cobertura_ignorar.txt`, cada um com o motivo.
