# Diagnóstico complementar — Compras.gov.br

Verificado em 19/10/2026 por Codex, com consultas e downloads locais autorizados pelo usuário. Complementa o [diagnóstico do Portal da Transparência](DIAGNOSTICO_FONTE_LICITACOES.md) e a etapa 01 do [checklist](TODO_IMPLEMENTACAO_BACKEND_E_DADOS.md).

## Conclusão

Há um caminho oficial para dados recentes e os campos que faltavam: utilizar os módulos de contratações, resultados, catálogo CATMAT e pesquisa de preços do Compras.gov.br. Os endpoints testados responderam sem token; isso não é garantia de disponibilidade permanente nem de cobertura de todas as compras brasileiras.

O repositório mensal é viável para carga histórica. A API pode complementar consultas e validar registros. A documentação de arquivos consultada anteriormente descreve nomes antigos; os nomes e caminhos atuais foram descobertos no índice oficial e confirmados por download.

A limitação de abril de 2024 pertence ao pacote histórico examinado do Portal da Transparência. Ela não se aplica à disponibilidade observada do Compras.gov.br. Não é necessário descartar o histórico coletado nem obrigar todo registro recente a ter vínculo com ele.

## Fontes e endpoints verificados

- [OpenAPI do Compras.gov.br](https://dadosabertos.compras.gov.br/v3/api-docs).
- [Documentação interativa](https://dadosabertos.compras.gov.br/swagger-ui/index.html).
- [Repositório oficial de ZIPs](https://repositorio.dados.gov.br/seges/comprasgov/).
- [Contratações e resultados — orientação do repositório](https://repositorio.dados.gov.br/seges/comprasgov/pncp/LEIAME.md).
- [Pesquisa de preços — orientação do repositório](https://repositorio.dados.gov.br/seges/comprasgov/pesquisa_precos/LEIAME.md).
- [Propostas — orientação do repositório](https://repositorio.dados.gov.br/seges/comprasgov/propostas/LEIAME.md), consultada, mas sem download ou validação de participações nesta etapa.

Endpoints efetivamente testados sob `https://dadosabertos.compras.gov.br`:

| Endpoint | Filtro usado | Resultado observado |
| --- | --- | --- |
| `/modulo-contratacoes/1_consultarContratacoes_PNCP_14133` | Publicação entre 01 e 30/09/2026, modalidade 6 | Primeira página com 100 registros; API informou 10.429 no filtro |
| `/modulo-contratacoes/2_consultarItensContratacoes_PNCP_14133` | Inclusão entre 01 e 30/09/2026, material, com resultado | Primeira página com 100 registros; API informou 29.348 |
| `/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133` | Resultado entre 01 e 30/09/2026 | Primeira página com 100 registros; API informou 177.262 |
| `/modulo-contratacoes/1.1_consultarContratacoes_PNCP_14133_Id` | `tipo=idCompra`, código de compra obtido na amostra de itens | Uma compra vinculada |
| `/modulo-contratacoes/3.1_consultarResultadoItensContratacoes_PNCP_14133_Id` | Mesma compra do exemplo | Quatro resultados; um corresponde ao primeiro item amostrado |
| `/modulo-material/4_consultarItemMaterial` | `codigoItem=486054` | Um registro CATMAT com classe, grupo, PDM e especificação |
| `/modulo-pesquisa-preco/1_consultarMaterial` | Catálogo 486054, compras de setembro de 2026 | Primeira página com 100 registros; API informou 130 |

As páginas são amostras por ordem da API, não seleção aleatória. As três consultas por data têm universos distintos e não devem ser comparadas como se fossem a mesma população. Os totais podem mudar com atualizações da fonte.

O preço unitário homologado e o fornecedor coincidiram entre o primeiro item amostrado e seu resultado vinculado. É uma checagem concreta de um exemplo, não uma reconciliação completa da API.

## Arquivos mensais completos

ZIPs de setembro de 2026 baixados e validados por CRC; números abaixo são linhas brutas, não entidades deduplicadas.

| Arquivo | ZIP (bytes) | CSV (bytes) | Linhas | IDs distintos de compra/item |
| --- | ---: | ---: | ---: | ---: |
| Compras | 6.266.130 | 29.361.628 | 25.861 | 25.811 |
| Itens | 25.698.133 | 178.847.874 | 242.144 | 226.365 |
| Resultados | 2.236.913 | 20.724.047 | 40.682 | 40.580 itens |
| Pesquisa de preços — materiais | 19.696.451 | 129.275.984 | 114.029 | 112.538 itens |

Os quatro ZIPs totalizam cerca de 53,9 MB e os CSVs, 358,2 MB. Não há duplicatas exatas de linha nos quatro CSVs, mas há mais de uma linha para alguns IDs: investigar versões e granularidade antes de definir unicidade. O CSV de compras contém `ind_atual`, preenchido como `True` em todas as 25.861 linhas; isso não eliminou a repetição de IDs, portanto seu significado e política de seleção ainda precisam ser formalizados.

Nos itens, `cod_item_catalogo` está vazio nas 242.144 linhas. Todos têm unidade e valor estimado preenchidos, mas 34.896 linhas têm valor unitário estimado zero. Em 201.572 linhas, o valor unitário de resultado está vazio. Um item sem resultado não deve ser tratado como homologado por zero.

A ligação por IDs na mesma competência encontrou quatro IDs de compra referenciados por itens sem correspondência no arquivo de compras, um ID de compra de resultado sem correspondência e 126 IDs de item de resultado ausentes no arquivo de itens. São diferenças entre snapshots a investigar; a importação deve registrar e permitir resolver essas referências, sem inventar entidades completas.

Há 49.795 IDs de item comuns entre pesquisa de preços e itens PNCP neste mês. Não foi encontrado ID de item com códigos de catálogo divergentes dentro do arquivo de materiais. O restante pode exigir busca em outras competências ou não ter correspondência; essa contagem não valida automaticamente unidade e preço.

As compras do ZIP têm publicação entre 01 e 29/09/2026, enquanto a pesquisa de preços cobre datas de compra até 30/09. Resultados incluem datas anteriores ao mês de publicação da compra, inclusive em 2024: esses casos precisam de inspeção, não correção automática. O nome do arquivo mensal não garante cobertura integral do mês nem alinhamento entre módulos.

## Campos encontrados e limitações

| Necessidade | Evidência real | Tratamento |
| --- | --- | --- |
| Dados recentes | Compras, itens e resultados consultados para setembro de 2026 | Não limitar coleta ao pacote antigo do Portal da Transparência |
| Valor estimado | `valorUnitarioEstimado` e `valorTotal` no item; total estimado na compra | Preservar sigilo e versão; não comparar granularidades diferentes |
| Valor homologado | `valorUnitarioHomologado`, `valorTotalHomologado`, `quantidadeHomologada` nos resultados | Filtrar situações e cancelamentos antes de agregar |
| Fornecedor | Identificador e nome nos resultados | Preservar tipo de pessoa, não impor sempre CNPJ |
| Unidade no item | `unidadeMedida` preenchida nos 100 itens da amostra API | Texto pode exigir normalização e revisão |
| Catálogo no item PNCP | `codItemCatalogo`, classe e grupo vieram nulos nos 100 itens da amostra API | Não assumir preenchimento só porque o schema contém o campo |
| Catálogo na pesquisa de preços | `codigo_item_catalogo` preenchido em todas as 114.029 linhas do arquivo mensal de materiais | Fonte de referência de preços e catálogo |
| Embalagem/fornecimento | Nome, sigla e capacidade no módulo de preços | Agrupar considerando embalagem e capacidade, além do catálogo |
| Descrição do catálogo | Registro CATMAT 486054 validado | Usar código e versão do catálogo, sem vincular apenas por texto |
| Participantes não vencedores | Não aparecem como lista completa nos endpoints de resultados testados | Diagnosticar módulo de propostas antes de calcular concorrência |
| Assinatura do contrato | Não validada nesta etapa | Não substituir por abertura ou resultado |

Na amostra de 100 itens, todos têm valor estimado, resultado, fornecedor e unidade preenchidos. Há 23 itens com `orcamentoSigiloso=true`: manter esse indicador e validar seu significado no estágio do processo; valor retornado não autoriza desconsiderar o sigilo.

No arquivo completo de pesquisa de preços de materiais de setembro:

- 114.029 linhas e nenhum código de catálogo vazio.
- 22.950 siglas de unidade de fornecimento vazias.
- 29.580 nomes de unidade de fornecimento vazios.
- 95.470 siglas de unidade de medida vazias.
- `nome_unidade_medida` vazio em todas as linhas.

Campos de fornecimento e de medida têm papéis diferentes. Um nome de medida vazio não torna automaticamente inválido um preço por unidade de fornecimento conhecida, mas não permite inventar conversão. Capacidade zero não é divisor: pode representar uma unidade sem fator informado. A política de uso depende da especificação.

## Particionamento e vínculo entre fontes

Os ZIPs de contratações, itens e resultados ficam na competência da **publicação da compra no PNCP**, conforme orientação do repositório. Resultados posteriores podem atualizar arquivos antigos. Os arquivos de pesquisa de preços são particionados pela **data da compra**.

Portanto, um resultado de setembro pode pertencer ao arquivo mensal de uma compra publicada antes. Não exigir que uma mesma competência contenha os mesmos registros nos dois módulos, nem interpretar ausência nesse cruzamento como corrupção da fonte.

Preservar `id_compra`, `id_compra_item` e o número de controle PNCP. Para resultados, preservar também o sequencial e a situação. Uma chave de item pode aparecer em vários resultados legítimos; não deduplicar apenas por ela.

O vínculo PNCP com pesquisa de preços deve ser feito por identificadores e validado em quantidade, unidade, fornecedor e datas. `id_item_compra` interno do módulo de preços e `id_compra_item` composto são campos diferentes. Não presumir que são intercambiáveis.

## Recorte piloto proposto

Categoria inicial: **artigos para escritório (CATMAT classe 7510)**. Primeiro item técnico: **borracha apagadora, CATMAT 486054**, com especificação confirmada por consulta ao catálogo.

No arquivo mensal, o grupo com fornecimento `UNIDADE`, capacidade informada como zero e sem sigla de medida contém:

- 125 linhas e 125 IDs de item distintos.
- 5 compras, 5 órgãos e 13 identificadores de fornecedor distintos.
- Datas de compra de 04 a 23/09/2026.
- Preços unitários entre R$ 0,32 e R$ 225,00.

Isso permite exercitar limpeza e investigação das diferenças, mas não comprova comparabilidade plena: inspecionar descrição detalhada, quantidade, marca, documentação e eventual embalagem divergente. Cento e vinte e cinco linhas em cinco compras não equivalem a 125 contratações independentes nem demonstram suficiência para Autoencoder. A faixa de preço não comprova sobrepreço.

Dos 125 IDs do grupo piloto, apenas dois estão no ZIP PNCP da mesma competência. Consultando a API de itens por `idCompra` para as cinco compras, foram encontrados 124 dos 125 IDs; uma compra retornou zero registros nesse serviço. Isso valida enriquecimento para o exemplo e também demonstra por que o vínculo precisa atravessar competências e tratar fontes legadas ou referências não resolvidas. Não há garantia de que a diferença de preço foi explicada.

Período histórico pretendido para o piloto: **outubro de 2025 a setembro de 2026**, ampliando somente após validar os meses e a independência/cobertura dos exemplos. A escolha é uma decisão técnica inicial, revisável conforme qualidade dos dados; não há modelo treinado.

## Reprodução e artefatos

A partir da raiz do repositório:

```bash
# Uma página por domínio e um exemplo vinculado; somente biblioteca padrão Python.
python3 collector/scripts/amostrar_api_comprasgov.py --inicio 2026-09-01 --fim 2026-09-30 --codigo-catalogo 486054

# ZIPs mensais e estatísticas; --blocos usa Range + ETag para conexões instáveis.
python3 collector/scripts/diagnosticar_comprasgov.py --ano 2026 --mes 9 --blocos
python3 collector/scripts/verificar_vinculos_comprasgov.py --entrada data/diagnostico/compras/2026-09
```

Dados brutos ficam em `data/diagnostico/compras/`, ignorado pelo Git. Estatísticas versionáveis, URLs, horários, tamanhos e hashes ficam em `docs/diagnostico/`. Os scripts são instrumentos exploratórios, não o coletor de produção nem garantia de desempenho para cargas maiores.

Houve interrupção do download integral de itens. A alternativa segmentada verifica tamanho, `Content-Range`, ETag constante e CRC do ZIP antes de aceitar o arquivo. Uma execução interrompida não deve ser registrada como arquivo íntegro.

## Evidências versionadas

- [Perfil mensal, aquisição, qualidade e vínculos](diagnostico/perfil_comprasgov_202609.json).
- [Perfil das consultas API e exemplos vinculados](diagnostico/perfil_api_comprasgov_202609.json).
- [Categoria piloto e contagens iniciais](diagnostico/categoria_piloto_comprasgov.json).

Também foram convertidas e relidas amostras das primeiras 5.000 linhas de cada CSV em Parquet, com colunas string e Zstandard: compras 957.242 bytes; itens 442.623; resultados 300.831; materiais 558.465. São amostras ordenadas, não estimativa do tamanho final PostgreSQL ou de todo o dataset Parquet.

## Decisão de arquitetura e próximos passos

1. Adotar Compras.gov.br como fonte principal proposta para o piloto recente, mantendo a origem explícita. Portal da Transparência permanece fonte histórica já diagnosticada, sem junção obrigatória.
2. Coletar os pacotes mensais PNCP e pesquisa de preços com conectores separados e manifestos versionados.
3. Importar compras, itens e resultados preservando suas granularidades e versões.
4. Enriquecer catálogo por vínculo comprovado com pesquisa de preços/CATMAT; manter ausente quando não houver correspondência.
5. Implementar primeiro o fluxo com dados e atributos disponíveis. Diagnosticar propostas e contratos antes de oferecer concorrência e publicação–contrato como sinais completos.
6. Ampliar o piloto de escritório e revisar comparáveis antes de treinar detecção de anomalia de preços.

Não foi necessário criar conta, cadastrar token ou provisionar serviço pago para os testes realizados.
