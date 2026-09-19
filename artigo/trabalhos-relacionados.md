# Trabalhos relacionados — levantamento de 18/09/2026

Levantamento feito **depois** dos experimentos, para responder uma pergunta específica:
alguém já reportou associação entre test smell e qualidade do código de produção, e com que
operacionalização? A resposta define se o nosso nulo tem contra quem se posicionar.

Não é revisão sistemática. É um levantamento dirigido, e está registrado como tal.

---

## 1. O concorrente direto

**Tahir, A., Counsell, S., MacDonell, S.G. (2016). An empirical study into the relationship
between class features and test smells.** APSEC 2016, pp. 137–144.
DOI [10.1109/APSEC.2016.34](https://doi.org/10.1109/APSEC.2016.34) ·
[arXiv:2103.14781](https://arxiv.org/abs/2103.14781)

| | |
|---|---|
| veículo | APSEC — **CORE C**, conferência regional |
| impacto | **20 citações, 0 influentes** (Semantic Scholar, 09/2026) |
| escala | 5 sistemas, 975 pares classe de produção–teste unitário |
| desfecho | **número de tipos de test smell** num teste unitário |
| preditor | CC, WMC, LCOM, DIT da classe de produção (métricas objetivas) |
| método | **Spearman**, não-paramétrico |
| binding | naming convention + static call graph, **sem precisão reportada** |
| ferramentas | três detectores de test smell distintos |

**Resultado.** CC, WMC e LCOM correlacionam significativamente com o número de tipos de
test smell nos cinco sistemas; CC alta em Commons Lang, média em Dependency Finder e MOEA,
baixa em JFreeChart e JabRef. WMC alta em três sistemas. LCOM mais fraca. DIT misto, com
correlação negativa em dois sistemas.

### Por que este é o artigo a confrontar

O desfecho deles é **exatamente o nosso `ts_n_distintos`**, e o teste estatístico é o
mesmo. A diferença está no preditor: eles usam complexidade objetiva, nós usamos severidade
percebida por revisor profissional.

**E eles não controlam por tamanho.** As palavras "confound" e "normaliz" não aparecem no
texto. Mais que isso: eles descrevem a cadeia de tamanho como *explicação*, não como
ameaça:

> "The increase in the number of test cases in a unit test is somehow a reflection of the
> increase of the size and complexity of the associated production class — a large or
> complex class will require more test cases."

> "prior evidence has indicated that the larger an artefact, the greater the presence of
> faults... The same would likely be true for the presence of different test smells."

É interpretação defensável — mas deixa aberta exatamente a pergunta que medimos: **quando o
tamanho sai, sobra alguma coisa?** No nosso dado, não sobra (0,084 bruto contra 0,047 em
densidade).

---

## 2. O trabalho de referência da área

**Spadini, D., Palomba, F., Zaidman, A., Bruntink, M., Bacchelli, A. (2018). On the
Relation of Test Smells to Software Code Quality.** ICSME 2018.
[PDF](https://sback.it/publications/icsme2018a.pdf)

| | |
|---|---|
| veículo | ICSME — **CORE A** |
| impacto | **182 citações** |
| escala | 10 sistemas, mais de 1 milhão de casos de teste, múltiplos releases |
| desfecho | change-proneness e defect-proneness do teste **e da produção testada** |
| preditor | presença (binária) de 6 tipos de test smell |
| método | Wilcoxon rank sum + Cohen's d |

**Resultado.** Testes com smell são mais change- e defect-prone; produção testada por
testes smelly é mais defect-prone.

**Importante para nós: eles controlam por tamanho.** Controlam por LOC do método de teste e
por número de mudanças anteriores, citando Kitchenham et al. e Zhou et al. sobre tamanho
como efeito confundidor. O achado deles sobrevive ao controle.

> Isso limita uma pretensão que chegamos a considerar: "a área não controla por tamanho" é
> **falso**. O trabalho mais citado controla. O que não controla é o de menor impacto, que
> é justamente o mais próximo do nosso desenho.

O desfecho deles é **defeito**, não code smell. Não há conflito direto com o nosso nulo.

---

## 3. Precedente do instrumento

**Martins, L. et al. (2024). On the diffusion of test smells and their relationship with
test code quality of Java projects.** Journal of Software: Evolution and Process.
[DOI 10.1002/smr.2532](https://onlinelibrary.wiley.com/doi/abs/10.1002/smr.2532)

Montaram o dataset TSSM com **JNose** sobre 13.703 sistemas Java, correlacionando test
smells com métricas estruturais do **código de teste**. Não toca em code smell de produção.

Serve como precedente de que JNose em escala é aceito na área — o mesmo detector que o
step 1 usou.

---

## 4. O dataset de rótulo

**Madeyski, L., Lewowski, T. (2020). MLCQ: Industry-Relevant Code Smell Data Set.**
EASE 2020. [DOI 10.1145/3383219.3383264](https://dl.acm.org/doi/10.1145/3383219.3383264)

14.739 revisões de desenvolvedores profissionais sobre 4.770 amostras, com severidade.

**O MLCQ é usado na literatura para *detecção* de code smell** — machine learning, deep
learning, LLM. Não encontramos uso dele em estudo de correlação com test smell.

---

## 5. O que o levantamento conclui

**O nosso pareamento parece inédito:** severidade de code smell *percebida por revisor
profissional* × test smell. A literatura usa proxies métricos (Tahir) ou defeitos
(Spadini).

**Existe contra quem se posicionar**, e a posição é coerente com os dois:

| trabalho | preditor | achado |
|---|---|---|
| Tahir 2016 | complexidade objetiva (CC, WMC) | associação positiva, sem normalizar por tamanho |
| Spadini 2018 | presença de test smell | associação com defeitos, controlando tamanho |
| **nosso** | **percepção humana de code smell** | **sem associação, r < 0,12, binding auditado** |

A leitura que encaixa os três: **o que prediz test smell é tamanho e complexidade, não a
percepção de que o código está ruim.**

## 6. O que ainda não foi levantado

- Revisão sistemática de verdade (protocolo, strings de busca, critérios).
- Trabalhos sobre test-to-code traceability e a precisão dessas técnicas — relevante porque
  nossa auditoria de binding é diferencial, e precisa ser posicionada contra o que já se
  sabe sobre naming convention e call graph.
- Literatura sobre a lacuna de concordância entre ferramentas e percepção de desenvolvedor,
  que é o pano de fundo do nosso preditor.
