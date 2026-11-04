# Validação inicial do núcleo de ML — protocolo v1

Registrado antes do experimento histórico em 20/10/2026. Esta avaliação interrompe a expansão da API para testar viabilidade dos dados e do Isolation Forest. Não publica scores de produção nem altera bases importadas.

## Pergunta

Com itens de um CATMAT, especificação e fornecimento compatíveis, um Isolation Forest produz uma priorização reproduzível que acrescente informação à regra simples de preço acima da mediana histórica?

Não há rótulos confiáveis de irregularidade. Portanto, não serão reportadas acurácia, precisão de fraude, recall de fraude ou probabilidade de fraude. Desempenho em alterações sintéticas é apenas teste controlado de sensibilidade.

## Dados e cortes previamente definidos

- CATMAT piloto: 486054. Fonte principal: pesquisa de preços Compras.gov.br.
- Histórico: 01/10/2025 a 30/09/2026, adquirido com paginação e objetos/respostas originais preservados fora do Git. O piloto de setembro já importado também será auditado.
- Treino: outubro/2025–junho/2026. Avaliação futura: julho–setembro/2026. Ajustes/medianas/escalas usam somente treino. Compras que apareçam nos dois períodos são retiradas da avaliação, sem misturar grupos.
- Unidade: item/referência de compra, preservando a chave oficial de compra/item/fornecedor/forma. Versões são resolvidas por atualização da origem; empate divergente não é escolhido por preço.
- Grupo estrito: CATMAT + descrição detalhada normalizada apenas em caixa, acentos e pontuação + unidade de fornecimento + capacidade + medida. Não inferir equivalência entre textos, caixas e unidades. Ausência de unidade ou descrição impede comparação.
- Capacidade zero em UN é mantida como código da fonte, sem convertê-la em quantidade de embalagem; não converter CX para UN. Resultados dependem de posterior confirmação documental das condições comerciais.
- Compras com mais de cinco referências no mesmo grupo de especificação são segregadas para revisão de cobertura antes do modelo principal, para impedir concentração/pseudorreplicação. Essa regra não afirma que sejam irregulares.
- Um grupo só entra no experimento principal com pelo menos 100 exemplos de treino, 30 de avaliação, 20 compras de treino, 10 de avaliação, 3 órgãos e 3 fornecedores no treino. Nenhuma compra pode representar mais de 10% do treino. Estes são limites operacionais deste piloto, não garantia estatística universal.
- Se nenhum grupo passar, o resultado principal será INCONCLUSIVO POR DADOS. Um ensaio exploratório menor pode ser executado e será identificado separadamente, sem reduzir retrospectivamente os critérios para declarar sucesso.

## Comparação e parâmetros

Referência simples: preço unitário / mediana histórica do grupo, ordenado do maior para o menor. Referência bilateral adicional: valor absoluto do log dessa razão, para não confundir objetivo de sobrepreço com anomalias de preço baixo.

Atributos candidatos do modelo: log(preço/mediana de treino), log(1+quantidade). Quantidade ausente não vira zero: o modelo que a usa exige presença. Uma versão com somente preço será explicitamente comparada à regra de preço. Não inserir CNPJ, IDs ou códigos de órgão como números contínuos. Participantes, contratos e HHI ficam indisponíveis neste ensaio até cobertura comprovada.

Isolation Forest: `contamination='auto'`; `n_estimators` 200/500; `max_samples` min(64,n)/min(256,n); `max_features=1.0`; sementes 11, 23, 42, 71, 101. Nenhuma escolha será apresentada como percentual conhecido de fraude. Scores serão `-score_samples`, apenas para ordenação; não haverá escala artificial 0–100.

## Critérios e limites

1. **Execução técnica:** scores finitos; artefato carregado reproduz scores; dados de teste não alteram referências; parâmetros, hashes e versões registrados.
2. **Estabilidade:** medir Spearman entre scores e Jaccard dos top-k, com k=min(10,max(3,ceil(10% do teste))). Referências operacionais: mediana Spearman ≥0,80 e mediana Jaccard ≥0,60. Se falhar, a configuração não é aprovada para publicação.
3. **Informação adicional:** comparar top-k e correlação com a regra simples e com a referência bilateral. Sobreposição ≥90% com regra unilateral será tratada como possível redundância, não como ganho comprovado. Diversidade do ranking também não prova ganho.
4. **Sensibilidade controlada:** alterar somente preços de cópias de exemplos de teste, multiplicando por 3/10, e medir deslocamento do score/posição. Os exemplos sintéticos não entram na avaliação real nem constituem fraude rotulada.
5. **Utilidade real:** preparar amostra de união dos rankings e controles para revisão sem mostrar algoritmo/score. Revisão documental humana permanece necessária; sem ela, não declarar ganho de utilidade, taxa de acerto ou conclusão de auditoria.

Decisão pode ser: inviável com este recorte, inconclusiva por dados/revisão, ou apta a piloto revisado. Mesmo um ensaio estável não prova detecção de fraude. Não ajustar os critérios retrospectivamente para produzir aprovação.

## Extensão de disponibilidade (antes de avaliar um segundo CATMAT)

Se o CATMAT piloto não atingir os limites, uma segunda coorte poderá ser escolhida somente por disponibilidade: maior número de compras distintas na classe 7510 (artigos de escritório) em setembro/2026, com unidade UN, no ZIP mensal já coletado; desempate pelo código em ordem crescente. A lista de candidatos e seu hash serão salvos antes da consulta histórica. Usar o mesmo período, cortes, grupos e critérios, sem escolher um item por resultados do modelo. Reportar separadamente a falha do piloto e o resultado da segunda coorte; uma segunda coorte não transforma retroativamente o piloto em aprovado.

Snapshots adquiridos agora podem conter revisões publicadas depois da data de corte. Registrar essa contagem. O corte por data da compra impede usar referências futuras no cálculo, mas não constitui backtest estritamente ponto-no-tempo sem snapshots antigos; nenhuma alegação de previsão operacional futura será baseada só neste experimento.
