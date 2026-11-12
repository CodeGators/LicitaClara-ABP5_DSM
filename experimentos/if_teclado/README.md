# Experimento independente — Isolation Forest de teclados USB

Diagnóstico do CATMAT **451817**, teclado padrão USB com fio, por unidade.
Não altera banco, frontend, modelos publicados ou parâmetros da aplicação.

## Abrir o resultado entregue

- `analise_if_teclado.ipynb`: notebook com código, explicações, tabelas e gráficos executados.
- `analise_if_teclado.html`: mesma análise para abrir no navegador, sem executar Python.
- `recorte_teclado.csv`: 311 registros rastreáveis, incluindo descrições e preços extremos.
- `origem.json`: assinatura do grupo, critérios temporais, contagens e hashes das fontes.

O recorte reproduz a coorte técnica já preparada na V2: **254 registros de treino**
(jul–dez/2025), **44 de avaliação** (jul–ago/2026) e **13 referências de setembro/2026**.
Os 13 registros de setembro vêm dos arquivos `material`; não são uma consulta aos
itens/resultados publicados no banco. Este notebook não permite concluir que o
ranking operacional inteiro esteja correto ou errado.

Não se excluem extremos por preço, não se usa avaliação/setembro no treinamento
nem na calibração e não se ajustam hiperparâmetros olhando os resultados posteriores.
A separação de treino e avaliação por compra e por período é verificada.

## Executar do zero

Na raiz do repositório, com Python 3.12 e `uv` já instalados:

```bash
uv run --locked --all-packages --extra validation --with-requirements experimentos/if_teclado/requirements.txt python experimentos/if_teclado/executar.py
```

O `uv` usa dependências extras em um ambiente temporário; não é necessário alterar
`pyproject.toml` ou `uv.lock`. O notebook usa as versões de ML do ambiente bloqueado
do projeto e registra as versões efetivas no resultado.
Os nove ZIPs de `material` usados no recorte estão em `datasets/equipe` e são
obrigatórios para a conferência independente de hashes e das 311 linhas de origem.
Não é necessário iniciar Docker, backend ou frontend.

Para editar e executar por células:

```bash
uv run --locked --all-packages --extra validation --with-requirements experimentos/if_teclado/requirements.txt python -m jupyterlab experimentos/if_teclado/analise_if_teclado.ipynb
```

Use **Restart Kernel and Run All** para reproduzir a análise inteira.
Selecione o kernel Python desse ambiente. O script `executar.py` fixa o
interpretador atual explicitamente e evita usar um kernel antigo de outro ambiente.

## O que é comparado

1. Mesmo grupo e mesmos períodos, com hashes, IDs e matrizes reconciliados.
2. IF apenas com `ln(preço / mediana do treino)`.
3. IF com preço e `ln(1 + quantidade)`, como na configuração operacional.
4. Medida `-score_samples` e percentil do treino, calculados pelas funções do projeto.
5. Contagem de Score 100 exato, ≥99 e ≥99,995 (possível arredondamento para 100,00).
6. Referência estatística IQR sobre log do preço, calculada somente no treino.
7. Sondas artificiais fora do treinamento e da calibração.
8. Cinco sementes predefinidas; reprodutibilidade e verificações do percentil.

Parâmetros: 200 árvores, amostra máxima `min(256, 254) = 254`, seed principal 42.
Profundidade real máxima de 8; comprimento ajustado e fator `c(n)` são diferentes.

As tabelas completas, gráficos e resumo da execução ficam em
`data/experimentos/if_teclado/`, pasta local ignorada pelo Git.
As sondas artificiais têm arquivo separado e identificação explícita.

## Interpretação

Uma saída variada mostra que o modelo não atribuiu 100 a todos neste recorte;
isso não prova acurácia ou validade comercial. Concordância entre sementes ou
com o IQR também não demonstra acerto. Descrições genéricas, marcas e possíveis
compras de conjuntos exigem revisão documental. Não corrigir preço/quantidade
nem remover registros só porque parecem discrepantes.

A coorte foi extraída das matrizes temporais V2 já existentes, com seu manifesto
registrado em `origem.json`. As descrições e valores exportados foram reconciliados
com os arquivos originais. Portanto, esta é uma investigação do modelo e da escala
sobre a seleção atual, não uma nova implementação independente da seleção dos grupos.

## Resultado da execução entregue

| Variante | Avaliação (44 registros) | Referências de setembro (13 registros) |
|---|---|---|
| Apenas preço | 0 em 100; faixa 3,543–98,819 | 0 em 100; faixa 3,543–97,638 |
| Preço + quantidade | 0 em 100; faixa 5,906–98,425 | 0 em 100; faixa 24,409–98,425 |

Nas cinco sementes predefinidas, nenhum registro posterior ao treino recebeu 100
em nenhuma das duas variantes. O maior registro do próprio treino recebeu 100
na calibração, comportamento esperado para esta distribuição empírica.
Algumas sondas artificiais extremas chegaram a 100, mostrando que a saturação
continua possível. Esses resultados não demonstram acurácia, não justificam
excluir extremos e não diagnosticam por si só a tela operacional.
