# Abordagem do artigo

Enquadramento do artigo, decidido depois dos experimentos e do levantamento de literatura.

Mantido separado da documentação dos steps de propósito: os steps registram o que foi
feito e o que foi medido; este arquivo registra o que fazer com isso.

---

## A tese

> **Severidade de code smell percebida por desenvolvedores profissionais não se associa à
> densidade de test smell nos testes dedicados à classe. A associação que aparece em
> contagem bruta é efeito do tamanho do teste.**

O nulo é a espinha do artigo. Três lições de medição, aprendidas ao responder a pergunta,
entram como contribuições metodológicas.

Ela encaixa os dois trabalhos relacionados e o nosso resultado sem contradizer nenhum:

- Tahir et al. (2016) acharam associação entre **complexidade objetiva** da classe de
  produção e número de tipos de test smell — sem normalizar por tamanho do teste.
- Spadini et al. (2018) acharam associação entre presença de test smell e **defeito**,
  controlando tamanho.
- Nós não achamos associação entre **severidade percebida de code smell** e densidade de
  test smell, e mostramos que a associação bruta que aparece é efeito de tamanho.

Percepção humana de code smell e complexidade métrica não são a mesma coisa — e essa
distinção é o que a área chama de *lacuna de concordância*.

## Os resultados que sustentam

| # | resultado | evidência |
|---|---|---|
| 1 | nulo com limite superior quantificado | densidade: rho 0,050, IC [−0,022, 0,123], poder para detectar r ≥ 0,104; nulo também em cada um dos quatro smells (teto do IC 0,13 a 0,15) |
| 2 | a associação bruta é tamanho do teste | rho 0,554 test smell × tamanho; 0,078–0,090 code smell × tamanho; parcial cai a 0,062 (n.s.); confirmados × limpos separam em contagem (delta 0,138) e não em densidade |
| 3 | binding por referência estática mede outro construto | 94,8% de precisão para "exercita", 10,1% para "testa" |
| 4 | o rótulo `any > none` do MLCQ é circular com o desenho amostral | unidades com um único revisor têm 0,0% de positivos; toda amostra do crosscheck já era positiva. O próprio desenho permite medir a confiabilidade de um "none" isolado: 97,8% |

Três operacionalizações independentes convergiram para o nulo (correlação contínua, smells
individuais com FDR, comparação de extremos em densidade). A quarta, com melhor desenho
(confirmados × só disputados), ficou inconclusiva por poder.

## As contribuições

O que temos e os trabalhos relacionados não têm:

1. **Precisão do binding medida e auditada** — 293 pares, 6 estratos, 94,2% ponderado no
   ramo determinístico, com censo humano e segundo avaliador
   (`steps/step2-binding/PROTOCOLO-AUDITORIA-HUMANA.md`).
2. **Poder estatístico calculado** — o nulo é interpretável porque sabemos o que o desenho
   detectaria.
3. **Ground truth de percepção profissional** — 14.739 revisões do MLCQ, sobre 9.517
   unidades (amostra, smell), contra métricas calculadas ou heurísticas de defeito.
4. **Escala** — a análise principal cobre 730 arquivos de 246 repositórios, contra 5 e 10
   sistemas dos trabalhos citados.
5. **Rastro completo** — 164 testes registrados, incluindo os que não deram em nada.

## Destino

ICSME 2027 (A1), com SANER 2028 como plano B e ESEM como alternativa A2. Texto em inglês.
Detalhes no documento de eventos-alvo.

## Riscos

- **O nulo é sobre percepção, não sobre defeito.** Um revisor pode dizer que medimos a
  opinião de desenvolvedores sobre design, não qualidade. É verdade, e precisa estar no
  título ou no abstract.
- **Cobertura de 37,5%** do binding. Os 62,5% restantes misturam classe sem teste e falha
  do método.
- **Recall do binding não medido.**
- **Arquivos do mesmo repositório não são independentes.** 113 dos 246 repositórios
  contribuem com um único arquivo, e os 10 maiores somam 20,5% dos arquivos.
- **164 testes num espaço de ~200 combinações** — o artigo tem que declarar regime
  exploratório.

## O que não fazer

**Rodar mais experimentos.** As operacionalizações já convergiram, e cada teste novo piora
o problema de comparações múltiplas sem mudar a conclusão. As duas células da grade 4 × 13
acima do r detectável (feature envy × Verbose Test, blob × Duplicate Assert) são hipóteses
para um estudo confirmatório, não achados.

**Apresentar como artigo metodológico sobre normalização.** O trabalho mais citado da área
já controla por tamanho. O resultado 2 é confirmação com mecanismo medido, não descoberta.

## O que falta antes de escrever

1. **Censo humano da auditoria e segundo avaliador**, conforme o protocolo.
2. **Revisão de literatura com protocolo**, ao menos snowballing a partir de Tahir e
   Spadini, para sustentar que o pareamento percepção × test smell não foi estudado.
3. **Medição de recall do binding** (meia tarde): sortear arquivos não ligados e procurar
   teste à mão.
