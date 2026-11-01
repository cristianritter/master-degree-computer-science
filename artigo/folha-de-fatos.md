# Folha de fatos

Todo número que o artigo cita, com a origem de cada um. **Gerado** por
`python artigo/tools/folha_de_fatos.py --gravar` — não editar à mão. O artigo usa as
macros de `fatos.tex` (coluna *macro*), nunca o número digitado.

Os valores são recalculados pelo próprio script a partir dos dados versionados; o
`steps/conferir_cobertura.py` exige que cada um case com a saída dos comandos dos
steps, o que faz desta folha uma segunda apuração.

## Coleta (step 1)

| macro | valor | o que é | origem |
|---|---:|---|---|
| `\FreposMlcq` | 522 | repositórios referenciados pelo MLCQ | `steps/step1-coleta-jnose/dados/repos_map.csv` |
| `\FreposHashOk` | 451 | espelho no commit exato do MLCQ (analisados) | `steps/step1-coleta-jnose/dados/repos_map.csv` |
| `\FreposHashDiverge` | 10 | espelho existe, mas em outro commit | `steps/step1-coleta-jnose/dados/repos_map.csv` |
| `\FreposSemEspelho` | 61 | sem espelho | `steps/step1-coleta-jnose/dados/repos_map.csv` |
| `\FreposColetados` | 451 | repositórios com coleta concluída | `steps/step1-coleta-jnose/reports/run_log.csv` |
| `\FhorasColeta` | 4,4 | horas de processamento da coleta, somando todas as tentativas | `steps/step1-coleta-jnose/reports/run_log.csv` |
| `\FreposJunitQuatro` | 398 | repositórios detectados como JUnit 4 | `steps/step1-coleta-jnose/reports/run_log.csv` |
| `\FreposJunitCinco` | 36 | repositórios detectados como JUnit 5 | `steps/step1-coleta-jnose/reports/run_log.csv` |
| `\FreposJunitTres` | 17 | repositórios detectados como JUnit 3 | `steps/step1-coleta-jnose/reports/run_log.csv` |
| `\FarquivosRemovidosNpe` | 25 | arquivos removidos antes da análise por derrubarem o JNose (NPE) | `steps/step1-coleta-jnose/reports/run_log.csv` |
| `\FreposRemovidosNpe` | 11 | repositórios com arquivo removido | `steps/step1-coleta-jnose/reports/run_log.csv` |
| `\FclassesTeste` | 107.535 | classes de teste analisadas pelo JNose | `steps/step2-binding/dados/test_classes.csv` |
| `\FreposComTeste` | 430 | repositórios com pelo menos uma classe de teste | `steps/step2-binding/dados/test_classes.csv` |
| `\FsmellsHabilitados` | 20 | test smells habilitados (padrão do JNose menos o Unknown Test) | `steps/step2-binding/tools/comum.py (SMELLS)` |
| `\Focorrencias` | 2.150.044 | ocorrências de test smell | `steps/step2-binding/dados/test_classes.csv` |
| `\FpctAssertionRoulette` | 39,5% | parte das ocorrências que é Assertion Roulette | `steps/step2-binding/dados/test_classes.csv` |
| `\FpctMagicNumber` | 18,0% | parte das ocorrências que é Magic Number Test | `steps/step2-binding/dados/test_classes.csv` |
| `\FocorrenciasDefaultTest` | 41 | ocorrências de Default Test na coleta inteira | `steps/step2-binding/dados/test_classes.csv` |
| `\FclassesAninhadas` | 6.842 | classes cujo nome reportado é o de uma classe aninhada (defeito do flowClass) | `steps/step2-binding/dados/test_classes.csv` |
| `\FpctClassesAninhadas` | 6,4% | idem, em porcentagem | `steps/step2-binding/dados/test_classes.csv` |
| `\FreposAninhadas` | 320 | repositórios com classe aninhada | `steps/step2-binding/dados/test_classes.csv` |
| `\FquedaEager` | 28× | queda de Eager Test por classe nas linhas aninhadas | `steps/step2-binding/dados/test_classes.csv` |
| `\FquedaLazy` | 23× | queda de Lazy Test por classe nas linhas aninhadas | `steps/step2-binding/dados/test_classes.csv` |
| `\FunknownClasses` | 142 | classes que o detector de Unknown Test zeraria | `steps/step1-coleta-jnose/tools/efeito_unknown_test.py` |
| `\FpctUnknownClasses` | 0,13% | idem, em porcentagem | `steps/step1-coleta-jnose/tools/efeito_unknown_test.py` |
| `\FunknownRepos` | 51 | repositórios afetados | `steps/step1-coleta-jnose/tools/efeito_unknown_test.py` |
| `\FunknownOcorrencias` | 5.500 | ocorrências dos outros smells que ele apagaria | `steps/step1-coleta-jnose/tools/efeito_unknown_test.py` |
| `\FpctUnknownOcorrencias` | 0,26% | idem, em porcentagem | `steps/step1-coleta-jnose/tools/efeito_unknown_test.py` |
| `\FexcedeMetodosAninhadas` | 2.388 | classes aninhadas com mais métodos com smell do que o n_metodos do JNose | `steps/step2-binding/dados/test_smell_occurrences.csv.gz e test_classes.csv` |
| `\FpctExcedeMetodosAninhadas` | 34,9% | idem, em porcentagem das classes aninhadas | `steps/step2-binding/dados/test_smell_occurrences.csv.gz e test_classes.csv` |
| `\FexcedeMetodosNormais` | 15 | classes sem aninhada com mais métodos com smell do que o n_metodos do JNose | `steps/step2-binding/dados/test_smell_occurrences.csv.gz e test_classes.csv` |

## MLCQ (step 2)

| macro | valor | o que é | origem |
|---|---:|---|---|
| `\FamostrasMlcq` | 4.770 | amostras do MLCQ | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FunidadesMlcq` | 9.517 | unidades de rótulo (amostra, smell) | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FamostrasUmSmell` | 23 | amostras julgadas para um só dos dois smells da granularidade | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FrevisoesMlcq` | 14.739 | revisões do MLCQ | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FescalaMax` | 3 | maior código da escala de severidade (critical) | `steps/step2-binding/tools/comum.py (SEVERIDADES)` |
| `\FrevisoresMlcq` | 26 | revisores distintos | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FunidadesUmRevisor` | 7.051 | unidades com um único revisor | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FpctUnidadesUmRevisor` | 74,1% | idem, em porcentagem | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FamostrasCrosscheck` | 1.227 | amostras levadas ao crosscheck (todas já sinalizadas antes) | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FnoneRevisados` | 1.037 | unidades com none isolado revisadas de novo por causa do outro smell | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FpctNoneSeSustenta` | 97,8% | em que o none isolado coincide com a maioria final | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FpctDisputadas` | 67,3% | positivas com 2+ revisores em que algum revisor disse none | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FestratoNegUm` | 7.048 | unidades no estrato negativo_1_review | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FestratoNegConf` | 817 | unidades no estrato negativo_confiavel | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FestratoPosConf` | 896 | unidades no estrato positivo_confiavel | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FestratoDisputado` | 753 | unidades no estrato disputado | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |
| `\FestratoPosUm` | 3 | unidades no estrato positivo_1_review | `steps/step2-binding/dados/mlcq_samples.csv e mlcq_reviews.csv` |

## Binding e auditoria (step 2)

| macro | valor | o que é | origem |
|---|---:|---|---|
| `\FparesBinding` | 16.869 | pares (produção, teste) no binding | `steps/step2-binding/dados/binding.csv` |
| `\FparesAuditados` | 293 | pares auditados | `steps/step2-binding/dados/auditoria_binding_auto.csv` |
| `\FparesPorEstratoAuditoria` | 50 | pares sorteados por estrato amostrado (os de censo têm menos) | `steps/step2-binding/dados/auditoria_binding_auto.csv` |
| `\FmaxTestes` | 10 | teto de classes de teste por arquivo de produção no ramo ampliado | `steps/step2-binding/tools/gerar_analises.py` |
| `\FprecisaoDet` | 94,2% | precisão do binding no ramo deterministico ("o teste tem a classe como alvo") | `steps/step2-binding/dados/auditoria_binding_auto.csv` |
| `\FprecisaoDetBaixo` | 90,9% | limite inferior do IC95% estratificado da precisão (deterministico) | `steps/step2-binding/dados/auditoria_binding_auto.csv` |
| `\FprecisaoDetAlto` | 97,5% | limite superior do IC95% estratificado da precisão (deterministico) | `steps/step2-binding/dados/auditoria_binding_auto.csv` |
| `\FprecisaoAmp` | 10,1% | precisão do binding no ramo ampliado ("o teste tem a classe como alvo") | `steps/step2-binding/dados/auditoria_binding_auto.csv` |
| `\FprecisaoAmpAmplo` | 94,8% | precisão no ramo ampliado sob "o teste exercita a classe" | `steps/step2-binding/dados/auditoria_binding_auto.csv` |
| `\FprecisaoAmpBaixo` | 5,4% | limite inferior do IC95% estratificado da precisão (ampliado) | `steps/step2-binding/dados/auditoria_binding_auto.csv` |
| `\FprecisaoAmpAlto` | 14,9% | limite superior do IC95% estratificado da precisão (ampliado) | `steps/step2-binding/dados/auditoria_binding_auto.csv` |
| `\FprecisaoCaminhoExato` | 98,0% | precisão do estrato caminho_exato | `steps/step2-binding/dados/auditoria_binding_auto.csv` |

## Amostra de análise (step 2, tabelas derivadas)

| macro | valor | o que é | origem |
|---|---:|---|---|
| `\FarquivosDet` | 730 | arquivos de produção no ramo deterministico | `steps/step2-binding/dados/analise_deterministico.csv` |
| `\FreposDet` | 246 | repositórios no ramo deterministico | `steps/step2-binding/dados/analise_deterministico.csv` |
| `\FclassesTesteDet` | 768 | classes de teste ligadas no ramo deterministico | `steps/step2-binding/dados/analise_deterministico.csv` |
| `\FrotuloPositivoDet` | 204 | arquivos com rótulo agregado acima de zero (deterministico) | `steps/step2-binding/dados/analise_deterministico.csv` |
| `\FpctRotuloPositivoDet` | 27,9% | idem, em porcentagem | `steps/step2-binding/dados/analise_deterministico.csv` |
| `\FcomAninhadaDet` | 53 | arquivos com algum teste de classe aninhada (deterministico) | `steps/step2-binding/dados/analise_deterministico.csv` |
| `\FarquivosUmaAmostraDet` | 710 | arquivos com uma única amostra do MLCQ (determinístico) | `steps/step2-binding/dados/analise_deterministico.csv` |
| `\FrDetectavelDet` | 0,104 | menor r detectável com 80% de poder, N do ramo deterministico | `fórmula de poder do step 2 (poder_analise.py)` |
| `\FarquivosAmp` | 1.369 | arquivos de produção no ramo ampliado | `steps/step2-binding/dados/analise_ampliado.csv` |
| `\FreposAmp` | 323 | repositórios no ramo ampliado | `steps/step2-binding/dados/analise_ampliado.csv` |
| `\FclassesTesteAmp` | 3.193 | classes de teste ligadas no ramo ampliado | `steps/step2-binding/dados/analise_ampliado.csv` |
| `\FrotuloPositivoAmp` | 384 | arquivos com rótulo agregado acima de zero (ampliado) | `steps/step2-binding/dados/analise_ampliado.csv` |
| `\FpctRotuloPositivoAmp` | 28,0% | idem, em porcentagem | `steps/step2-binding/dados/analise_ampliado.csv` |
| `\FcomAninhadaAmp` | 254 | arquivos com algum teste de classe aninhada (ampliado) | `steps/step2-binding/dados/analise_ampliado.csv` |
| `\FrDetectavelAmp` | 0,076 | menor r detectável com 80% de poder, N do ramo ampliado | `fórmula de poder do step 2 (poder_analise.py)` |

## Resultados (step 3)

| macro | valor | o que é | origem |
|---|---:|---|---|
| `\FrhoDensidadeDet` | 0,044 | Spearman densidade × rótulo agregado (deterministico) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FpDensidadeDet` | 0,238 | p bicaudal, idem | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FicDensidadeBaixo` | −0,029 | IC95%, limite inferior (densidade) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FicDensidadeAlto` | 0,116 | IC95%, limite superior (densidade) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FparcialDensidade` | 0,051 | Spearman parcial densidade × rótulo, controlando n_metodos | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FrhoBrutoDet` | 0,087 | Spearman bruto × rótulo agregado (deterministico) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FpBrutoDet` | 0,019 | p bicaudal, idem | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FicBrutoBaixo` | 0,014 | IC95%, limite inferior (bruto) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FicBrutoAlto` | 0,158 | IC95%, limite superior (bruto) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FparcialBruto` | 0,052 | Spearman parcial bruto × rótulo, controlando n_metodos | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FrhoDistintosDet` | 0,072 | Spearman distintos × rótulo agregado (deterministico) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FpDistintosDet` | 0,051 | p bicaudal, idem | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FicDistintosBaixo` | 0,000 | IC95%, limite inferior (distintos) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FicDistintosAlto` | 0,144 | IC95%, limite superior (distintos) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FparcialDistintos` | 0,042 | Spearman parcial distintos × rótulo, controlando n_metodos | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FrhoDensidadeAmp` | −0,004 | Spearman densidade × rótulo agregado (ampliado) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FpDensidadeAmp` | 0,888 | p bicaudal, idem | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FrhoBrutoAmp` | 0,008 | Spearman bruto × rótulo agregado (ampliado) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FpBrutoAmp` | 0,775 | p bicaudal, idem | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FrhoDistintosAmp` | −0,013 | Spearman distintos × rótulo agregado (ampliado) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FpDistintosAmp` | 0,641 | p bicaudal, idem | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FrhoBrutoTamanho` | 0,560 | Spearman contagem bruta × tamanho do teste (n_metodos) | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FrhoDensidadeTamanho` | −0,087 | Spearman densidade × tamanho do teste | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FrhoRotuloMetodos` | 0,078 | Spearman rótulo × n_metodos do teste | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FrhoRotuloLoc` | 0,090 | Spearman rótulo × LOC do teste | `steps/step3-analise/analises/01-correlacao-agregada/dados/exploracao.csv` |
| `\FtestesPorSmell` | 76 | testes da análise por test smell (duas famílias) | `steps/step3-analise/analises/02-por-test-smell/dados/por_test_smell.csv` |
| `\FnominaisPorSmell` | 6 | desses, com p < 0,05 sem ajuste | `steps/step3-analise/analises/02-por-test-smell/dados/por_test_smell.csv` |
| `\FmenorPajPorSmell` | 0,379 | menor p ajustado por BH na análise por test smell | `steps/step3-analise/analises/02-por-test-smell/dados/por_test_smell.csv` |
| `\FdeltaBrutoExtremos` | 0,127 | r bisserial confirmados × limpos, bruto (determinístico) | `steps/step3-analise/analises/03-extremos/dados/extremos.csv` |
| `\FpajBrutoExtremos` | 0,039 | p ajustado, idem | `steps/step3-analise/analises/03-extremos/dados/extremos.csv` |
| `\FnConfirmados` | 136 | arquivos confirmados (determinístico) | `steps/step3-analise/analises/03-extremos/dados/extremos.csv` |
| `\FnLimpos` | 526 | arquivos limpos (determinístico) | `steps/step3-analise/analises/03-extremos/dados/extremos.csv` |
| `\FdeltaDensidadeExtremos` | 0,069 | r bisserial confirmados × limpos, densidade (determinístico) | `steps/step3-analise/analises/03-extremos/dados/extremos.csv` |
| `\FpajDensidadeExtremos` | 0,215 | p ajustado, idem | `steps/step3-analise/analises/03-extremos/dados/extremos.csv` |
| `\FdeltaDisputados` | 0,017 | r bisserial confirmados × só disputados, densidade | `steps/step3-analise/analises/04-disputados/dados/disputados.csv` |
| `\FdeltaDetectavelDisputados` | 0,244 | menor r bisserial detectável com 80% de poder, idem | `steps/step3-analise/analises/04-disputados/dados/disputados.csv` |
| `\FnDisputados` | 66 | arquivos só disputados (determinístico) | `steps/step3-analise/analises/04-disputados/dados/disputados.csv` |
| `\FtestesGrade` | 76 | testes da grade code smell × test smell | `steps/step3-analise/analises/05-code-x-test-smell/dados/cruzado.csv` |
| `\FmenorPajGrade` | 0,153 | menor p ajustado por BH na grade | `steps/step3-analise/analises/05-code-x-test-smell/dados/cruzado.csv` |
| `\FacimaDetectavelGrade` | 2 | células da grade com |rho| acima do r detectável | `steps/step3-analise/analises/05-code-x-test-smell/dados/cruzado.csv` |
| `\FmargemEquivalencia` | 0,10 | margem do TOST: |rho| de efeito pequeno (Cohen) | `steps/step3-analise/analises/06-robustez/robustez.py` |
| `\FreplicasBootstrap` | 2.000 | réplicas do bootstrap por repositório | `steps/step3-analise/analises/06-robustez/robustez.py` |
| `\FmaiorEfeitoDet` | 0,105 | maior |rho| compatível com os dados, densidade (limite do IC90%, deterministico) | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FbootBaixoDet` | −0,028 | IC95% do bootstrap por repositório, limite inferior, densidade (deterministico) | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FbootAltoDet` | 0,119 | IC95% do bootstrap por repositório, limite superior, densidade (deterministico) | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FmaiorEfeitoAmp` | 0,048 | maior |rho| compatível com os dados, densidade (limite do IC90%, ampliado) | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FbootBaixoAmp` | −0,054 | IC95% do bootstrap por repositório, limite inferior, densidade (ampliado) | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FbootAltoAmp` | 0,047 | IC95% do bootstrap por repositório, limite superior, densidade (ampliado) | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FpTostDensidadeDet` | 0,065 | p do TOST na margem, densidade (determinístico) | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FicNoventaBaixo` | −0,017 | IC90%, limite inferior, densidade (determinístico) | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FrhoSemAninhadaDet` | 0,041 | Spearman densidade × rótulo sem arquivos com classe aninhada (determinístico) | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FnSemAninhadaDet` | 677 | N desse recorte | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FpSemAninhadaDet` | 0,283 | p bicaudal, idem | `steps/step3-analise/analises/06-robustez/dados/robustez.csv` |
| `\FtestesTotal` | 235 | testes estatísticos rodados no step 3 (caderno) | `soma das linhas com p nos CSVs das análises 01 a 05 e com p_tost na 06` |

## Censo humano do binding (step 2)

| macro | valor | o que é | origem |
|---|---:|---|---|
| `\FparesSegundoAvaliador` | 48 | pares julgados também pelo avaliador 2 | `steps/step2-binding/dados/auditoria_humana_avaliador2.csv` |
| `\FparesPorEstratoSegundo` | 8 | pares por estrato na subamostra do avaliador 2 | `steps/step2-binding/dados/auditoria_humana_avaliador2.csv` |
| `\FestratosAuditoria` | 6 | estratos da auditoria do binding | `steps/step2-binding/dados/auditoria_humana_avaliador2.csv` |
| `\FprecisaoHumanaDet` | 90,2% | precisão humana, ramo determinístico, critério estrito, sobre os pares decididos | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaDetInf` | 90,2% | idem, limite inferior: todo '?' contado como n | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaDetSup` | 90,2% | idem, limite superior: todo '?' contado como s | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaAmp` | 7,2% | precisão humana, ramo ampliado, critério estrito, sobre os pares decididos | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaAmpInf` | 7,1% | idem, limite inferior: todo '?' contado como n | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaAmpSup` | 7,3% | idem, limite superior: todo '?' contado como s | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FinterrogacoesEstrito` | 1 | pares com veredito final '?', critério estrito | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FerrosHumanosDet` | 13 | pares do ramo determinístico em que o teste não tem a classe como alvo (todos: o teste não cita a classe) | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FconcordanciaHumanoAuto` | 87,7% | concordância humano final × julgamento automatizado, critério estrito | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FkappaHumanoAuto` | 0,752 | kappa humano final × julgamento automatizado, critério estrito | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaDetAmplo` | 100,0% | precisão humana, ramo determinístico, critério amplo, sobre os pares decididos | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaDetAmploInf` | 90,2% | idem, limite inferior: todo '?' contado como n | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaDetAmploSup` | 100,0% | idem, limite superior: todo '?' contado como s | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaAmpAmplo` | 82,1% | precisão humana, ramo ampliado, critério amplo, sobre os pares decididos | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaAmpAmploInf` | 81,1% | idem, limite inferior: todo '?' contado como n | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FprecisaoHumanaAmpAmploSup` | 82,2% | idem, limite superior: todo '?' contado como s | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FinterrogacoesAmplo` | 20 | pares com veredito final '?', critério amplo | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FconcordanciaHumanoAutoAmplo` | 86,4% | concordância humano final × julgamento automatizado, critério amplo | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |
| `\FkappaHumanoAutoAmplo` | 0,277 | kappa humano final × julgamento automatizado, critério amplo | `steps/step2-binding/dados/auditoria_humana_avaliador1.csv` |

## Pendentes

Macros que o artigo já usa e cujo dado ainda não existe: no PDF aparecem como
`[?? chave]`. Saem desta lista quando a planilha do avaliador 2 voltar.

| macro | o que será |
|---|---|
| `\FconcordanciaEstrito` | concordância entre avaliadores, critério estrito (%) |
| `\FkappaEstrito` | kappa de Cohen entre avaliadores, critério estrito |
| `\FconcordanciaAmplo` | concordância entre avaliadores, critério amplo (%) |
| `\FkappaAmplo` | kappa de Cohen entre avaliadores, critério amplo |
