# Validação do núcleo — resultado inicial

Atualização: a [revisão documental posterior](REVISAO_E_CONFIRMACAO.md) encontrou duas divergências de especificação e resultados posteriores aos cortes. O ensaio corretivo separado tem 140 referências de treino e 35 de avaliação; a publicação continua não aprovada. Os números abaixo preservam o experimento original.

Executado em 20/10/2026. **O Isolation Forest funciona tecnicamente com dados reais do Compras.gov.br. Sua utilidade para priorizar auditorias ainda não foi comprovada.** Não há percentual de acerto ou fraude detectada. A decisão registrada é `VIAVEL_TECNICAMENTE_UTILIDADE_PENDENTE`; isso permite continuar um piloto revisado, não publicar uma conclusão de auditoria.

## Dados e suficiência

O [protocolo](PROTOCOLO.md) registra critérios anteriores à avaliação histórica. Foram consultadas referências de materiais no endpoint oficial `https://dadosabertos.compras.gov.br/modulo-pesquisa-preco/1_consultarMaterial`, usando `tipo=codigoItemCatalogo`, `codigo`, `dataCompraInicio=2025-10-01`, `dataCompraFim=2026-09-30`, `pagina` e `tamanhoPagina=500`. Respostas originais, parâmetros e SHA-256 estão em `data/validacao_nucleo/`, fora do Git. Totais declarados reconciliados: uma página por CATMAT. Esse ensaio independente não modifica a base PostgreSQL da etapa 05; a aquisição histórica ainda deverá ser incorporada ao fluxo operacional do coletor.

Treino: outubro/2025–junho/2026. Avaliação: julho–setembro/2026. A referência de preço usa exclusivamente a mediana do treino. Compras presentes no treino são excluídas do teste, inclusive quando aparecem com outra especificação dentro da coorte. Não foram agrupadas embalagens diferentes nem inferida equivalência comercial pelo texto.

| Recorte | Linhas da fonte | Sem unidade, excluídas | Treino / teste do grupo avaliado | Resultado de disponibilidade |
|---|---:|---:|---:|---|
| Borracha, CATMAT 486054 | 272 | 8 | 43 / 10 | Insuficiente para ensaio principal; somente exploratório |
| Caneta marca-texto amarela, CATMAT 486374 | 386 | 3 | 142 / 41 | Atingiu os mínimos do protocolo |

Os totais da fonte incluem especificações e fornecimentos diferentes. Não são todos exemplos comparáveis. O grupo principal de marca-texto tem 120 compras no treino, 39 no teste, 97 órgãos e 101 fornecedores no treino. Nenhuma compra excede 10% do treino. A mediana de treino foi R$ 0,855 por unidade, preservada sem arredondamento no cálculo.

O piloto de borracha não foi aprovado retroativamente: possui apenas cinco compras distintas no teste e concentração acima do limite no treino. A auditoria do recorte mensal inicial também encontrou 118 de 130 referências em uma única compra; essa concentração impede usar o volume bruto como evidência de diversidade. Isso não prova erro ou irregularidade.

O segundo CATMAT foi escolhido por disponibilidade, conforme extensão registrada no protocolo, antes de avaliar seu modelo: maior número de compras distintas na classe 7510, fornecimento UN, no ZIP de setembro; empate resolvido pelo código crescente. Os três primeiros códigos tinham 13 compras; venceu 486374. A regra, candidatos e hash do ZIP estão registrados no [resultado agregado](resultado_agregado.json). Não houve escolha do item por métrica favorável do modelo.

## O que foi treinado e comparado

A unidade de análise é a referência de item, não o processo completo. Foram comparados:

- Regra simples: preço unitário / mediana histórica, priorizando preços maiores.
- Regra bilateral: valor absoluto de log(preço/mediana), considerando desvios para cima e para baixo.
- Isolation Forest com somente log(preço/mediana).
- Isolation Forest com log(preço/mediana) e log(1+quantidade).

Não foram usados participantes, estimado versus homologado, frequência fornecedor–órgão, HHI ou intervalo até contrato: a cobertura necessária ainda não está demonstrada neste ensaio. Nenhum campo ausente foi fabricado. IDs e CNPJ não são atributos numéricos do modelo.

Foram executadas quatro combinações nominais de parâmetros (200/500 árvores e amostras limitadas a 64/256 ou ao tamanho do treino), cada uma com cinco sementes: 11, 23, 42, 71 e 101. A âncora já definida era 200 árvores, `max_samples=min(256,n)`, semente 42, `max_features=1.0`, `contamination='auto'`; não se escolheu a melhor configuração pelo teste. No grupo exploratório de 43 linhas, os dois limites de amostragem coincidem e não são configurações efetivamente distintas.

Scores são `-score_samples`: valores maiores indicam maior isolamento estatístico. Não são probabilidade de fraude, nem escala de prioridade 0–100. Ver [documentação oficial do Isolation Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html).

## Resultado do grupo principal

O top-k previamente definido foi de cinco referências, entre 41 avaliadas.

| Medida | IF somente preço | IF preço e quantidade |
|---|---:|---:|
| Spearman mediano entre sementes da configuração âncora | 0,945 | 0,985 |
| Jaccard mediano dos top-5 entre sementes | 0,667 | 1,000 |
| Spearman mediano entre configurações, semente 42 | 0,966 | 0,977 |
| Casos em comum com os cinco maiores preços | 1 de 5 | 1 de 5 |
| Reprodução exata dos scores após carregar artefato | Sim | Sim |

Ambas as versões atingiram os critérios operacionais de estabilidade (Spearman ≥0,80 e Jaccard ≥0,60). **0,985 não significa 98,5% de acerto.** Mede consistência da ordenação entre sementes. Os testes de preços artificialmente multiplicados por 3 e 10 aumentaram os scores dos 14 exemplos centrais disponíveis; são verificações de sensibilidade, não estimativa de desempenho real.

O ranking com preço e quantidade inclui uma referência de R$ 0,56 com 44.467 unidades e outra de R$ 0,83 com 15.546 unidades, além de referências com pequenas quantidades. Uma compra grande pode ser perfeitamente justificável. Essa diferença em relação à regra de preço **não demonstra melhoria**: pode representar informação útil, efeito normal de escala ou ruído. Não foram calculadas contribuições SHAP; esses valores apenas descrevem os casos selecionados.

No piloto de borracha, o modelo só de preço repetiu integralmente o top-3 da regra simples. Isso reforça a necessidade de comparar com regras básicas, em vez de assumir que usar ML traz ganho.

## O que falta para validar o objetivo acadêmico

Foram preparadas duas amostras sem scores nem indicação de algoritmo: **18 casos do grupo principal**, incluindo cinco controles, e dez do exploratório, incluindo cinco controles. Estão em `data/validacao_nucleo/resultados/revisao/`. Há **zero pareceres preenchidos**. Não consultar os arquivos de ranking ou de procedência antes da revisão.

Para cada caso, um integrante da equipe deve consultar a compra/item na fonte oficial, conferir descrição, unidade/embalagem, quantidade, preço, data e condições comerciais e preencher `parecer`, `justificativa` e `evidencia_url`. Sugestões de parecer:

- `comparavel_e_justificavel`: condições conferidas e diferença explicável;
- `requer_verificacao`: sinal relevante que exige análise adicional, sem concluir irregularidade;
- `erro_dado_ou_unidade`: inconsistência documentada;
- `nao_comparavel`: especificação ou condições não equivalentes;
- `inconclusivo`: documentação insuficiente.

Preservar os originais e salvar pareceres em cópia. O comando se recusa a sobrescrever uma planilha já preenchida. Se o revisor conhece os rankings, usar outro revisor para a avaliação sem essa informação. A revisão cega reduz influência do ranking; não elimina subjetividade. Os controles são determinísticos, não uma amostra probabilística da população.

Depois dos pareceres, cruzar os IDs com a procedência reservada e comparar quantos casos `requer_verificacao` cada método colocou no top-5, registrando separadamente dados inválidos, não comparáveis e inconclusivos. Definir previamente como tratar esses estados e, de preferência, obter uma segunda revisão independente. Qualquer proporção nesse lote pequeno tem grande incerteza e não representa precisão de fraude. Não ajustar o modelo repetidamente nesses mesmos 41 exemplos; uma alteração baseada na revisão precisa de outro período ainda não usado para confirmação.

Se o IF não trouxer casos úteis além da regra simples, registrar o resultado negativo e revisar atributos/coorte. Não há justificativa para produzir um ranking de risco apenas porque a execução foi estável. A evidência atual não permite afirmar que o objetivo completo da proposta já foi entregue.

## Reprodução e limites

Na raiz do repositório:

```bash
uv sync --locked --all-packages --extra validation
uv run --locked --all-packages --extra validation python -m licita_ml.experiments.core --offline
uv run --locked --all-packages --extra validation pytest -q
```

`--offline` exige os históricos locais preservados. Sem a opção, o comando consulta a API caso falte cache; arquivos existentes têm URL e SHA-256 conferidos. Uma nova consulta futura pode retornar correções da fonte e não reproduzir o snapshot atual. Não enviar dados volumosos/modelos ao Git. Para preservar outro ensaio ou pareceres, usar `--saida data/validacao_nucleo/outra_execucao`.

Dependências fixadas no lockfile e relatório: scikit-learn 1.9.1, NumPy 2.5.4, SciPy 1.18.1, joblib 1.6.0. O JSON agregado registra hashes do protocolo, código, respostas e quatro artefatos, parâmetros, duração, pico de memória e métricas. Artefatos próprios foram carregados e seus scores reproduzidos exatamente. Não carregar arquivos joblib de origem não confiável.

Os snapshots atuais contêm atualizações posteriores a junho/2026 em 12 referências do treino principal e quatro do exploratório. **Esta avaliação não é um backtest estritamente ponto-no-tempo**, nem prova desempenho em compras futuras. Ainda faltam confirmação documental de comparabilidade, validação humana, generalização para outra janela/categoria e integração operacional. Não há Autoencoder, inferência publicada no PostgreSQL, ranking de processos, escala 0–100 ou conclusão de fraude nesta entrega.

## Verificações da implementação

Foram aprovados 61 testes locais, sem skips, além de lint e formatação. Incluem integração das etapas anteriores, segregação por unidade/especificação, exclusão de compras compartilhadas entre períodos mesmo em grupos diferentes, rejeição de versões conflitantes, referência de treino sem observações futuras, recarga do modelo e proteção dos pareceres contra sobrescrita. Os hashes do código, protocolo e quatro artefatos foram conferidos após a execução; as duas planilhas reconciliam com seus totais registrados. O pico de memória observado na execução final foi 159,95 MiB. Esses testes verificam a implementação, não substituem a validação documental do ranking. O CI foi configurado para instalar o extra `validation`; não houve execução remota nesta entrega.
