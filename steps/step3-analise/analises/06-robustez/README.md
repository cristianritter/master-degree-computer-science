# Análise 06 — Robustez do nulo

**Pergunta.** O nulo da análise 01 em densidade resiste às três objeções que um revisor faz
a um resultado nulo?

**Resposta curta.** Resiste. Os dados excluem correlação acima de 0,105 no ramo
determinístico. Reamostrar por repositório não muda o intervalo, e tirar os arquivos com
classe aninhada também não. A equivalência na margem convencional de efeito pequeno
(|rho| = 0,10) fica no limiar e não é declarada.

```bash
python robustez.py --csv
```

Leva cerca de um minuto, por causa do bootstrap.

---

## As três objeções

| objeção | como se responde |
|---|---|
| "ausência de evidência não é evidência de ausência" | IC90% de Fisher e TOST (dois testes unilaterais a 5%) na margem \|rho\| = 0,10, o efeito pequeno de Cohen |
| arquivos do mesmo repositório não são independentes | bootstrap por repositório: 2000 réplicas, semente 42, reamostrando repositórios inteiros; IC95% percentil |
| o defeito de classe aninhada do JNose contamina a medida | o mesmo teste sem os arquivos com algum teste em `nome_divergente` |

A margem 0,10 é a convenção de efeito pequeno, não foi escolhida para este resultado. Por
isso o resultado vem também na forma que dispensa margem: o maior efeito que os dados ainda
admitem, o limite do IC90% mais distante de zero.

## Resultado

Ramo determinístico, densidade:

| recorte | N | repos | rho | IC95% Fisher | IC90% | p TOST | IC95% bootstrap |
|---|---:|---:|---:|---|---|---:|---|
| todas | 726 | 245 | 0,044 | [−0,029, 0,116] | [−0,017, 0,105] | 0,065 | [−0,028, 0,119] |
| sem classe aninhada | 677 | 236 | 0,041 | [−0,034, 0,116] | [−0,022, 0,104] | 0,063 | [−0,030, 0,122] |

- **Equivalência.** Os dados excluem \|rho\| acima de 0,105. Na margem 0,10 o TOST dá
  p = 0,065: não dá para declarar equivalência a efeito nulo nessa margem, mas qualquer
  efeito compatível com os dados fica no limite do que Cohen chama de pequeno. É o que o
  artigo afirma.
- **Repositório.** O IC do bootstrap por repositório é só um pouco mais largo que o de
  Fisher. A dependência entre arquivos do mesmo projeto não muda a conclusão.
- **Classe aninhada.** Sem os 53 arquivos afetados, rho vai de 0,044 para 0,041.

Bruto e distintos, no ramo determinístico, mantêm o padrão da análise 01 também no bootstrap:
o IC do bruto fica acima de zero (efeito de tamanho do teste), e o de distintos encosta em
zero.

## Ramo ampliado

| recorte | N | repos | rho | IC90% | p TOST | IC95% bootstrap |
|---|---:|---:|---:|---|---:|---|
| todas | 1.365 | 323 | −0,004 | [−0,048, 0,041] | <0,001 | [−0,054, 0,047] |

Equivalente a zero na margem 0,10. Não reforça o determinístico: com 10,1% de precisão para
"o teste testa esta classe", o ramo mede outra coisa (step 2, seção 6).

Os dados das 12 linhas (dois ramos, dois recortes, três desfechos) estão em
`dados/robustez.csv`.
