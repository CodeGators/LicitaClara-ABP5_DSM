# Etapa 05 — preparação e importação

Implementada e validada em 20/10/2026. Não inclui treinamento, inferência ou rotas de negócio.

## Aquisição complementar

O coletor agora aceita o ZIP `propostas`. O padrão de `coletar` continua sendo os quatro arquivos iniciais; propostas são uma opção explícita:

```bash
uv run --locked --package licita-collector licita-collector coletar --inicio 2026-09 --fim 2026-09 --arquivos propostas
```

Para complementar as compras de um CATMAT encontrado em um arquivo `material` já coletado:

```bash
uv run --locked --package licita-collector licita-collector complementar --competencia 2026-09 --material-arquivo f2f94c2e-971d-41d4-9af0-76af3e10d8bd --catalogo 486054
```

O UUID acima é o arquivo real desta instalação; em outra instalação, use o ID emitido pela coleta de `material`. O comando verifica seu hash e obtém IDs de compra por igualdade de catálogo, preservando zeros. O período de referência é a competência informada; a API é consultada por identidade da compra, mesmo que sua publicação seja anterior.

São adquiridos, por compra: contratação, itens, resultados e contratos no Compras.gov.br; quando existe controle PNCP, metadados de anexos da compra. Para cada contrato retornado com controle PNCP, adquire detalhe contratual e metadados de anexos. Não baixa PDFs nem executa consultas nacionais irrestritas. Uma fonte sem resultados gera um envelope vazio rastreável, não registros artificiais.

Cada consulta tem escopo e lock próprios, execução e objeto versionado. Envelopes `licita-json-v1` identificam tipo, consulta, páginas, URLs e resultados. A versão atual preserva também o texto original de cada resposta JSON. Valores fracionários são lidos com `Decimal`; o resultado estruturado conserva seu texto decimal, sem passagem por `float`. Coletores antigos sem `resposta_original` continuam legíveis; o original não é reconstruído retroativamente.

A paginação confere total informado, detecta páginas repetidas, rejeita mudanças no total e limita a 100 páginas e 100 MiB por objeto. Se um endpoint ignorar a paginação e informar lote incompleto, a coleta falha em vez de confirmar dados truncados. Falhas retornam IDs e códigos sanitizados; `retomar --execucao-id` também atende esses novos conectores. Extração de ZIP é específica de CSV; JSON já pode ser lido sem extração.

## Leitura e recorte

```bash
uv run --locked --package licita-ml licita-ml preparar --inicio 2026-09-01 --fim 2026-09-30 --catalogo 486054
```

O recorte é definido pelas referências de preços desse CATMAT e suas datas de compra. Mantém referências, compras e itens vinculáveis por IDs oficiais; datas de publicação relacionadas podem cair fora do período. Não restringe a unidades `UN` nesta etapa: unidades ausentes permanecem NULL e devem impedir comparações incompatíveis na etapa analítica. Este recorte pode conter mais registros do que o piloto exploratório que selecionava somente unidades preenchidas.

Leitores `csv-v1` e `json-v1` conferem checksum/tamanho, cabeçalhos ou campos mínimos e versão do envelope. Campos adicionais são preservados em `atributos_origem`. Mudança incompatível interrompe a execução, sem publicação parcial. CSV é UTF-8, com `;` e cabeçalho; ausência de valor não é zero. Erros de formato do arquivo inteiro são diferentes de valores inválidos em uma linha.

O comando usa `PROCESSING_DATABASE_URL` e reflete apenas o contrato migrado, sem importar a aplicação FastAPI. Não executa migrações. Para produção, o backend permanece responsável pelo esquema.

## Normalização e resolução

- Identificadores oficiais são texto; não converter para inteiro, retirar zeros ou aproximar por descrição.
- Dinheiro e quantidades usam `Decimal`/`NUMERIC(28,8)`. Rejeitar NaN, infinito, valores negativos e precisão incompatível; preço de referência deve ser positivo. Zero conhecido em campos que o permitem continua zero.
- Datas são validadas explicitamente. Timestamps da fonte sem offset permanecem sem fuso; horários operacionais usam UTC.
- Unidades não são imputadas, conciliadas por texto nem convertidas automaticamente. Quantidade/capacidade desconhecida fica NULL.
- Identidades globais existentes são reutilizadas; snapshots pertencem à base. Não atualizar registros históricos ou revisar os valores de uma base anterior.

Chaves de resolução:

| Domínio | Chave |
|---|---|
| Compra | `id_compra` |
| Item | `id_compra_item` |
| Resultado | item + identificação do fornecedor + sequencial do resultado |
| Referência de preço | compra + ID da referência de item + fornecedor + forma (SISRP/SISPP) |
| Proposta | ID oficial da proposta; não somente fornecedor/item |
| Contrato | controle PNCP do contrato |
| Documento | contexto do pai PNCP + sequencial do documento |

A precedência é o maior timestamp disponível da origem. No empate, a consulta API tem precedência sobre CSV do mesmo domínio. Mesmo timestamp/prioridade com valores divergentes rejeita o grupo, sem escolher por ordem ou preço. Repetições equivalentes e versões superadas são contadas como descartadas. Os arquivos originais permanecem preservados para auditoria.

Referência de preço é independente de haver snapshot PNCP correspondente. Itens, resultados, propostas e documentos só entram nas tabelas relacionais quando o pai correto existe na mesma base. Registros sem vínculo são separados com motivo; não criar processos fictícios para satisfazer FKs. Catálogo do item só é enriquecido quando há igualdade do ID oficial com a referência selecionada.

Contratos exigem vínculo comprovado com a compra. O detalhe PNCP pode preencher `data_assinatura`; vigência não é usada como assinatura. Metadados de documentos não comprovam download do binário: chave, tamanho e hash do PDF continuam NULL.

## Reconciliação e rejeições

Para cada arquivo:

`total = filtrados + aceitos + rejeitados + descartados`

Filtrados estão fora do recorte; descartados são repetições ou versões superadas; rejeitados possuem motivo. Os números ficam no manifesto e em `importacoes.diagnostico`. Antes de confirmar a base, a contagem por tabela com `base_id` deve coincidir com o lote preparado.

`rejeicoes.jsonl` registra apenas arquivo, membro/página, linha/ordinal e código do motivo. Não replica nomes, documentos pessoais ou valores nos logs de erro. Os originais permitem localizar os dados necessários à investigação. A proveniência relaciona cada registro aceito à importação/arquivo e ordinal lógico do registro CSV (cabeçalho = 1), ou página e ordinal JSON. CSVs com campos multilinha podem ter número físico de linha diferente desse ordinal; uma origem pode produzir mais de um vínculo, como contrato e relação com o processo.

## Artefatos e reexecução

Parquets ficam em:

```text
datasets/base={fingerprint}/catalogo={codigo}/entidade={tabela}/part-00000.parquet
```

Há particionamento por versão, catálogo e entidade. O manifesto registra período, IDs/hashes dos objetos de origem, versão de leitor/transformador, hash do código, filtros, política de resolução, tipos Arrow, contagens e checksums dos arquivos gerados. UUIDs são strings no Parquet; JSONB é JSON textual; dinheiro permanece decimal de escala 8.

O fingerprint considera período, catálogo, arquivos selecionados e código de transformação. Reexecutar a mesma seleção/código verifica e reutiliza a base, sem novo INSERT de domínio. Corrigir um arquivo ou mudar o código gera uma nova base; a anterior continua reproduzível com seus IDs e versão de código.

A seleção padrão utiliza a observação mais recente de cada módulo/competência, não o horário original do primeiro download. Para reproduzir uma base antiga após novas coletas, fornecer todos os IDs do manifesto via `--arquivos`. Versões empatadas no instante de observação exigem seleção explícita.

Parquets e manifesto são armazenados antes do commit SQL. Uma falha pode deixar objetos ainda sem base registrada; uma repetição usa as mesmas chaves. A publicação válida é o registro confirmado no PostgreSQL, não a existência isolada de uma pasta. Importações podem ser retomadas por repetição do comando; todos os dados de domínio são inseridos em lotes dentro de uma transação atômica, protegida por lock global de preparação.

`validada` significa integridade técnica e reconciliação. Não representa aprovação da cobertura, prontidão para treinar modelos ou conclusão de auditoria.

## Validação real

Foram processados 52 arquivos selecionados, entre ZIPs iniciais/propostas e respostas de aquisição complementar. Na execução registrada:

| Medida | Resultado |
|---|---:|
| Linhas lidas | 434.964 |
| Fora do recorte | 434.671 |
| Aceitas após resolução | 165 |
| Rejeitadas por vínculo ausente | 121 |
| Repetidas/superadas | 7 |
| Processos versionados | 7 |
| Itens versionados | 10 |
| Resultados de item | 8 |
| Referências de preços | 130 |
| Metadados de documentos | 10 |
| Vínculos de proveniência | 165 |

As 121 rejeições correspondem a 120 itens sem processo resolvido e um resultado sem item resolvido. O recorte contém referências de dez compras; três não tiveram processo resolvido no módulo PNCP. Há 120 IDs de item de referência sem snapshot de item resolvido e três referências sem unidade. Isso permanece exposto no manifesto; não impede guardar os preços independentes, mas limita análises conjuntas.

Não houve propostas ou contratos vinculáveis retornados no recorte desta execução; isso não é evidência de inexistência universal. Propostas/contratos/assinatura e seus vínculos foram exercitados com fixtures em PostgreSQL nos testes de integração. Não há modelo treinado ou score gerado.

A importação real durou aproximadamente 7,1 segundos, com pico RSS de 124,6 MiB. Os Parquets ocupam 112.473 bytes; manifesto e rejeições são medidos separadamente. As tabelas medidas do processamento, incluindo índices, passaram de 1.736.704 para 2.211.840 bytes; isso não representa todo o tamanho físico do banco/volume PostgreSQL. Métricas são observações deste piloto, não extrapolações para anos de dados.

A repetição reutilizou o mesmo ID de base e conferiu artefatos sem criar registros adicionais. Testes cobrem erro de esquema, valores inválidos, unidades ausentes, dinheiro exato, empate divergente, correção da origem, repetição e recuperação após falha no meio da importação. Evidência agregada em [validacao_etapa05.json](diagnostico/validacao_etapa05.json).

Para ampliar o histórico, repetir a coleta e complementação das competências desejadas e preparar um intervalo explícito. Permanecem os limites de 20 mil itens/linhas selecionadas por execução e de tamanho de objeto; expansão maior exige staging em disco e nova medição.
