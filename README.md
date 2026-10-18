# master-degree-computer-science

Estudo da relação entre code smell percebido por desenvolvedores (MLCQ) e test smell
(JNose) em projetos Java. Cada etapa mora em `steps/`, com README, scripts e dados.

## Reprodutibilidade

Todo número escrito na documentação sai de um comando versionado. Quatro verificadores
garantem isso, e cada um termina com código 1 se encontrar divergência:

| comando | o que confere |
|---|---|
| `python steps/step1-coleta-jnose/tools/conferir_coleta.py` | os números do README do step 1 |
| `python steps/step2-binding/tools/conferir_dados.py` | os números do README e das notas do step 2 |
| `python steps/step3-analise/tools/conferir_resultados.py` | os números dos READMEs do step 3 |
| `python steps/conferir_cobertura.py` | que nenhum número dos documentos (steps e `artigo/`) fique sem origem em algum comando |

Os três primeiros conferem valores. O quarto confere cobertura: procura números que
nenhum comando produz, ou seja, que só poderiam ter sido digitados à mão. Os números que
não são dados do estudo (anos, referências, configuração) ficam em
`steps/cobertura_ignorar.txt`, cada um com o motivo.
