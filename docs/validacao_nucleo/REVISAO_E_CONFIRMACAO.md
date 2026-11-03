# Revisão documental e confirmação do núcleo

Executado em 20/10/2026. **O núcleo técnico foi reproduzido; o ranking ainda não está validado para publicação como prioridade de auditoria.** A revisão encontrou divergências reais de especificação e revelou a necessidade de considerar a data do resultado, além da data da compra. Não há taxa de acerto, fraude comprovada ou superioridade demonstrada sobre a regra simples.

## O que foi feito

1. Conferência dos 18 casos do experimento principal por chaves oficiais, incluindo item, fornecedor, preço homologado, quantidade e unidade.
2. Consulta de compra/itens/resultados no Compras.gov.br e do resultado diretamente no PNCP quando faltava no outro módulo.
3. Aquisição limitada de documentos ativos, extração de texto e leitura dirigida dos anexos obtidos.
4. Tentativa de confirmação do modelo original congelado em outubro/2026.
5. Replicação em histórico disjunto de outubro/2024 a setembro/2025, com os mesmos atributos e configurações predefinidos.
6. Ensaio corretivo separado, exigindo resultado conhecido até o fim de cada período.

Critérios e extensões foram anotados no [protocolo da revisão](PROTOCOLO_REVISAO_E_CONFIRMACAO.md). A revisão é assistida e conhece os rankings; **não é uma avaliação humana independente ou cega**. As planilhas cegas originais não foram modificadas e continuam sem pareceres preenchidos.

## Conferência e documentos

Os 18 casos pertencem a 17 compras. Quinze tiveram os valores corroborados nos módulos do Compras.gov.br; três exigiram resultado diretamente no PNCP. Em uma compra, o identificador numérico perdeu zero inicial: o vínculo foi recuperado somente porque identificador textual completo do item, UASG, número do item e equivalência numérica concordavam. O original e a ligação textual ficaram registrados. Versões antigas e atuais de itens foram resolvidas por atualização da fonte; empate divergente não é resolvido por preço.

**Corroboração estrutural não é confirmação de equivalência comercial.** Os preços e quantidades coincidem, mas duas especificações documentais divergem do grupo padronizado. Ver [achados e fontes](ACHADOS_DOCUMENTAIS.md):

- Uma referência de marca-texto amarelo corresponde, no termo, a um item descrito como detector de falsidade em papel-moeda em formato de caneta. Esse caso estava no top-5 do IF original.
- Outra referência agrupada como amarela está descrita como verde no termo.
- A compra de 44.467 unidades destacada pelo modelo já previa essa quantidade no edital; a grande quantidade, isoladamente, não comprova problema. Seu preço homologado de R$ 0,56 era inferior à estimativa documental de R$ 0,88.

Foram tentados 23 documentos distintos, priorizando termo de referência e edital, até dois por compra. Dez documentos tiveram texto extraído; 13 tiveram falhas de acesso/transferência dentro dos limites definidos. O lote tem anexos com texto para nove dos 18 casos; em seis foram localizadas páginas com o item/catálogo, enquanto os demais textos podem ser apenas autorizações gerais. Extração de texto não equivale a validação do objeto. **Não foi concluída leitura documental integral dos 18 casos.** Os documentos indisponíveis continuam vinculados para conferência posterior. Nenhuma falha foi transformada em parecer favorável ou desfavorável.

A [tabela dos casos](CASOS_REVISAO_ASSISTIDA.md) mostra os valores e a procedência. Ambos os top-5 originais têm os cinco preços/quantidades corroborados; isso mede cobertura documental, **não precisão**. Há zero pareceres humanos independentes. O arquivo agregado preserva os achados, incluindo os dois itens cuja comparação deve ficar suspensa até esclarecimento.

## Datas: correção necessária

O primeiro corte era pela `dataCompra`. A revisão encontrou **duas referências no treino cujo resultado é posterior a junho/2026 e seis no teste cujo resultado é posterior a setembro/2026**. Elas não poderiam ser usadas para alegar uma previsão disponível naquelas datas.

O experimento original e seus quatro artefatos foram preservados. Um ensaio separado exige `dataResultado` até o corte correspondente. O grupo principal ficou com **140 exemplos de treino e 35 de avaliação**, sem alterar atributos ou hiperparâmetros. Continuou acima dos mínimos e passou pelo critério de estabilidade. Os dois casos com divergência documental também estão entre os resultados posteriores a setembro e ficaram fora dessa avaliação corretiva; não foram excluídos por conveniência para melhorar métricas.

| Ensaio com preço e quantidade | Treino | Avaliação | Top-k | Spearman mediano entre sementes | Jaccard mediano |
|---|---:|---:|---:|---:|---:|
| Original, datas da compra | 142 | 41 | 5 | 0,985 | 1,000 |
| Corretivo, resultado até o corte | 140 | 35 | 4 | 0,983 | 1,000 |
| Replicação histórica 2024/2025 | 177 | 107 | 10 | 0,985 | 0,818 |

Esses números medem estabilidade, não acerto. O ensaio corretivo usa o mesmo snapshot e período; **não é uma avaliação independente**. Seus top-k de ambos os modelos e da regra de preço estão cobertos pela amostra original dos 18 casos, mas ainda aguardam parecer.

Mesmo com o filtro da data de resultado, permanecem revisões posteriores nos snapshots adquiridos agora. Sem snapshots efetivamente observados na época, nenhum desses ensaios constitui backtest ponto-no-tempo estrito. `dataCompra` não comprova entrega ou pagamento; preço homologado não é, por si só, valor efetivamente pago.

## Mais dados e confirmação temporal

Foram adquiridas 474 referências no histórico disjunto de outubro/2024 a setembro/2025. O grupo elegível teve 177 exemplos de treino, de outubro/2024 a junho/2025, e 107 de avaliação, de julho a setembro/2025. Foram treinados artefatos próprios dessa janela, com as mesmas configurações e sementes já definidas. **O modelo de 2025/2026 não foi usado para alegar previsão de 2025.** Essa replicação confirma execução e estabilidade em outra janela histórica, sem provar utilidade ou disponibilidade de todas as informações na época.

Para confirmar o modelo original congelado, a consulta de 01 a 19/10/2026 retornou apenas cinco referências: duas sem unidade, uma caixa e duas UN com os atributos em ordem textual diferente da chave estrita original. Nenhuma passou pela chave original; portanto **não há amostra para confirmação temporal nesse lote**. Não foi alterada a regra para produzir aprovação. As duas descrições reordenadas podem ser semanticamente equivalentes, mas eventual regra melhor de agrupamento precisa ser versionada e avaliada; mesmo duas observações ficariam muito abaixo dos mínimos.

A inferência futura não foi demonstrada em um lote elegível de outubro. Esse resultado continua inconclusivo, apesar da replicação histórica estável.

## Decisão e próximos critérios

**Não publicar ainda o ranking como risco validado de auditoria.** Podemos defender que Isolation Forest é tecnicamente executável e estável neste recorte. Ainda não podemos defender que ele detecta irregularidades ou prioriza melhor que uma comparação simples de preços.

Antes da publicação:

1. Incorporar controle de data de resultado ao fluxo analítico versionado, preservando o experimento original.
2. Melhorar comparabilidade com especificações verificadas, registrar divergências e suspender os dois itens identificados até esclarecimento. Não usar a palavra “fraudes” na descrição do detector como indício de fraude da licitação.
3. Revisar também uma amostra do treino: a inspeção de 18 casos do teste não comprova a integridade semântica das 140 referências do treino corretivo.
4. Concluir revisão independente dos casos com os mesmos critérios para modelo, regra simples e controles, sem mostrar seus rankings.
5. Comparar a utilidade dos top-k e registrar o denominador, inconclusivos e limitações. Se o modelo não acrescentar valor, registrar o resultado negativo e revisar o desenho; dados novos devem confirmar qualquer ajuste posterior.
6. Confirmar em período operacional posterior com amostra suficiente. Consultar mais vezes a API não cria observações comparáveis nem elimina atraso da fonte.

Está preparado um dossiê com as 18 compras/itens, links oficiais, documentos e páginas localizadas, sem scores ou indicação de algoritmo: `data/validacao_nucleo/revisao_assistida/dossie_revisao_independente.csv`. Veja o [guia do revisor](GUIA_REVISAO_INDEPENDENTE.md). Há zero pareceres preenchidos. O assistente não substitui essa etapa por rótulos automáticos.

## Evidências e reprodução

Resumo versionado: [revisao_e_confirmacao_agregado.json](revisao_e_confirmacao_agregado.json). Respostas HTTP, documentos, PDFs extraídos, textos, modelos novos e relatórios completos estão em `data/validacao_nucleo/revisao_assistida/`, fora do Git. URLs, horários e SHA-256 foram preservados. Falhas de anexos são registradas com o motivo.

O código do experimento original foi arquivado antes de generalizar os parâmetros de período; seu hash corresponde ao registrado no ensaio inicial. Os quatro artefatos originais permanecem com os mesmos hashes. O novo relatório registra o hash do código atual e do protocolo. O estado do PostgreSQL e a API não foram alterados; nenhum score foi publicado.

Comandos e dependências adicionais de extração estão no [README do ML](../../ml/README.md). A revisão e os ensaios podem reutilizar seus snapshots locais; não é necessário repetir a coleta completa para consultar as evidências.

## Verificações locais

Foram aprovados 71 testes, sem skips, além de lint e formatação. Os testes cobrem chaves e zeros iniciais, versões conflitantes, preços/quantidades/unidades divergentes, períodos configuráveis, exclusão de compras já observadas, data de resultado até o corte, limites de ZIP e preservação da independência do dossiê. Foram conferidos os hashes de todos os snapshots locais desta revisão, dos três PDFs citados e dos oito artefatos (quatro originais e quatro dos novos ensaios). Os novos artefatos também reproduziram exatamente os scores após recarga. A planilha cega original permaneceu intacta. Esses controles verificam implementação e rastreabilidade; não são validação de acurácia ou utilidade.
