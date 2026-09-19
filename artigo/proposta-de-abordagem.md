# Proposta de abordagem para o artigo — 18/09/2026

Sugestão de enquadramento, feita **depois** dos experimentos e do levantamento de
literatura, para submeter à avaliação do orientador. Não é decisão tomada.

Mantida separada da documentação dos steps de propósito: os steps registram o que foi
feito e o que foi medido; este arquivo registra uma opinião sobre o que fazer com isso.

---

## A tese sugerida

> **O que prediz test smell é tamanho e complexidade do código, não a percepção de que o
> código está ruim.**

Ela encaixa os dois trabalhos relacionados e o nosso resultado sem contradizer nenhum:

- Tahir et al. (2016) acharam associação entre **complexidade objetiva** da classe de
  produção e número de tipos de test smell — sem normalizar por tamanho do teste.
- Spadini et al. (2018) acharam associação entre presença de test smell e **defeito**,
  controlando tamanho.
- Nós não achamos associação entre **severidade percebida de code smell** e densidade de
  test smell, e mostramos que a associação bruta que aparece é efeito de tamanho.

Percepção humana de code smell e complexidade métrica não são a mesma coisa — e essa
distinção é o que a área chama de *lacuna de concordância*.

## Os quatro resultados que sustentam

| # | resultado | evidência |
|---|---|---|
| 1 | nulo com limite superior quantificado | rho 0,047, IC [−0,026, 0,120], poder para detectar r ≥ 0,104 |
| 2 | a associação bruta é tamanho do teste | rho 0,554 test smell × tamanho; 0,079–0,091 code smell × tamanho; parcial cai a 0,058 (n.s.) |
| 3 | binding por referência estática mede outro construto | 94,8% de precisão para "exercita", 10,1% para "testa" |
| 4 | o rótulo do MLCQ é circular com o desenho amostral | `any > none` é quase detector de crosscheck; 19 positivos unânimes em 4.770 |

Três operacionalizações independentes convergiram para o nulo (correlação contínua, smells
individuais com FDR, comparação de extremos). A quarta, com melhor desenho, ficou
inconclusiva por poder.

## Os diferenciais de método

O que temos e os trabalhos relacionados não têm:

1. **Precisão do binding medida e auditada** — 293 pares, 6 estratos, 94,2% ponderado.
   Tahir usa naming convention e call graph sem reportar precisão; Spadini não reporta.
2. **Poder estatístico calculado antes** — o nulo é interpretável porque sabemos o que o
   desenho detectaria.
3. **Ground truth de percepção profissional** — 14.739 revisões, 328 desenvolvedores,
   contra métricas calculadas ou heurísticas de defeito.
4. **Escala de diversidade** — 451 repositórios contra 5 e 10 dos trabalhos citados.
5. **Rastro completo** — 104 testes registrados, incluindo os que não deram em nada.

## Riscos, honestamente

- **O nulo é sobre percepção, não sobre defeito.** Um revisor pode dizer que medimos a
  opinião de desenvolvedores sobre design, não qualidade. É verdade, e precisa estar no
  título ou no abstract.
- **Cobertura de 37,5%** do binding. Os 62,5% restantes misturam classe sem teste e falha
  do método.
- **Recall do binding não medido.**
- **A auditoria dos 293 pares é automatizada**, não humana.
- **APSEC C com 20 citações não é alvo de peso.** Confrontar só o Tahir não sustenta
  submissão forte; o que sustenta é o pacote.
- **104 testes num espaço de ~200 combinações** — o artigo tem que declarar regime
  exploratório.

## O que NÃO recomendo

**Rodar mais experimentos.** As três operacionalizações já convergiram, e cada teste novo
piora o problema de comparações múltiplas sem mudar a conclusão.

**Apresentar como artigo metodológico sobre normalização.** Foi minha sugestão inicial, e o
levantamento a derrubou: o trabalho mais citado da área já controla por tamanho. O achado 2
é confirmação com mecanismo medido, não descoberta.

## O que recomendo antes de escrever

1. **Revisão sistemática de verdade**, com protocolo — o levantamento atual é dirigido e
   não serve como seção de trabalhos relacionados.
2. **Conferência humana de ~30 pares da auditoria** (uma hora) — vira taxa de concordância
   reportável e fecha a ameaça de a auditoria ser automatizada.
3. **Medição de recall do binding** (meia tarde) — sortear arquivos não ligados e procurar
   teste à mão.

Nenhuma das três é bloqueante para decidir se o artigo existe. As duas últimas são baratas
e fecham ameaças que um revisor levanta.
