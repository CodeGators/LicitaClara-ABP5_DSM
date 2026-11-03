# Achados da leitura dos documentos oficiais

Revisão realizada pelo assistente, com conhecimento dos rankings. Não é revisão humana independente nem comprovação de irregularidade. A corroboração de chaves, preço, quantidade e unidade foi obtida nos 18 casos; **isso não confirmou que todos sejam produtos equivalentes**.

## Quantidade atípica que já estava prevista

Compra `98769105901712024`, item 33, caso `01c07d7c28af0c52089c`: a relação de itens prevê **44.467 unidades** de marca-texto amarelo, com entrega em Maringá/PR. A estimativa era R$ 0,88 por unidade; o resultado consultado informa R$ 0,56. O modelo destacou a combinação de quantidade grande e preço baixo. O documento confirma o planejamento dessa quantidade, não um problema de digitação da quantidade. Ainda seria necessário avaliar a necessidade e a execução da contratação para julgar sua adequação. [Edital e relação de itens, PDF interno `RelacaoItens98769105901712024000.pdf`, página 7](https://pncp.gov.br/api/pncp/v1/orgaos/76282656000106/compras/2024/516/arquivos/1).

## Especificação diferente apesar do mesmo código de catálogo

Compra `38025706000672026`, item 17, caso `d9fb091e10cd7de5a83d`: a referência de pesquisa de preços descreve marca-texto amarelo. Entretanto, o termo descreve **detector de falsidade em papel-moeda em formato de caneta**, com garantia mínima de 20 mil testes. Os R$ 1,00 e dez unidades coincidem com o resultado oficial, mas não autorizam comparar esse objeto com um marca-texto comum. Esse caso estava no top-5 do IF original. É uma divergência documental que precisa de esclarecimento, não fraude identificada. [Termo, página 4](https://pncp.gov.br/api/pncp/v1/orgaos/96291141000180/compras/2026/6394/arquivos/6).

Compra `38918406000352026`, item 11, caso `e173028921b187804539`: o termo descreve **destaca-texto verde**, enquanto a pesquisa de preços o agrupou como amarelo. O próprio termo usa CATMAT 486374 para os itens 10 (amarelo) e 11 (verde). O resultado de R$ 1,80 e dez unidades confere, mas a cor do item 11 não corresponde ao grupo analisado. [Termo, páginas 1 e 2](https://pncp.gov.br/api/pncp/v1/orgaos/10764033000161/compras/2026/30/arquivos/3).

## Consequência para o projeto

CATMAT, descrição padronizada da pesquisa de preços e unidade iguais não bastam para garantir equivalência comercial. **Até esclarecer essas duas divergências, os respectivos itens não devem alimentar a comparação de marca-texto amarelo.** Não alterar os resultados originais retrospectivamente: registrar exclusões e nova versão da base.

Os dois casos com divergência também possuem resultado após setembro/2026 e já ficaram fora do ensaio corretivo por data de resultado. Isso não prova que os demais registros estejam semanticamente corretos; o treino também precisa de amostra documental. A exclusão pela data não substitui um controle de especificação.

O IF pode destacar dados que merecem conferência, incluindo problemas de qualidade de dados. Isso ainda não demonstra detecção de sobrepreço, fraude ou superioridade sobre uma regra simples. Os PDFs e textos estão preservados fora do Git; páginas, hashes e observações constam de [achados_documentais.json](achados_documentais.json).
