"""Gera as DUAS tabelas de analise do step 2, uma por definicao de binding.

    dados/analise_deterministico.csv   caminho_exato + convencao
    dados/analise_ampliado.csv         + referencia_estatica, com teto de concentracao

Existem duas porque a pergunta "este teste testa esta classe?" tem duas respostas
defensaveis, e o step 2 nao e o lugar de escolher (ver README, secao 6):

  deterministico  regra fechada e reproduzivel sem julgar intencao: o teste esta no lugar
                  que a convencao de nomenclatura preve. E a mesma regra que o proprio
                  jnose-core aplica no getFileProduction. Cobertura menor, construto limpo.

  ampliado        acrescenta "o teste referencia estaticamente o tipo", que dobra a
                  cobertura mas confunde referenciar com testar; o teto de --max-testes 10
                  corta o caso do DTO referenciado por dezenas de testes.

As duas saem com TODAS as regras de rotulo lado a lado e com n_testes_nome_divergente,
entao a etapa 3 escolhe rotulo, filtro e definicao de binding sem refazer nada aqui.
Se o achado da etapa 3 sobrevive as duas, ele e robusto a definicao de binding; se nao
sobrevive, a diferenca e resultado, nao acidente.

Uso:
    python gerar_analises.py
"""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))

CONFIGS = [
    ("deterministico", ["--metodos", "caminho_exato", "convencao"]),
    ("ampliado", ["--metodos", "caminho_exato", "convencao", "referencia_estatica",
                  "--max-testes", "10"]),
]


def main():
    for nome, args in CONFIGS:
        saida = "analise_%s.csv" % nome
        print("=" * 70)
        print("%s  ->  dados/%s" % (nome, saida))
        print("=" * 70)
        cmd = [sys.executable, os.path.join(AQUI, "montar_analise.py"),
               "--rotulo", "sev_media", "--saida", saida] + args
        r = subprocess.run(cmd)
        if r.returncode != 0:
            sys.exit("falhou em %s" % nome)
        print()


if __name__ == "__main__":
    main()
