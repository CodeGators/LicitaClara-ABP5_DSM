# Complemento da etapa 03 — propostas, contratos e documentos

Diagnóstico executado em 20/10/2026. Objetivo: resolver as duas pendências de modelagem com dados oficiais verificáveis. Não corresponde à importação de dados nem à implementação de novos conectores de produção.

## Fontes e cobertura

Compras.gov.br permanece como fonte principal de compras, itens, resultados, preços e agora propostas e contratos. **PNCP passa a ser um complemento explícito** para metadados de anexos e detalhe do contrato, incluindo assinatura. O Portal da Transparência permanece fora da integração do MVP.

| Recurso verificado | Acesso | Limite da evidência |
|---|---|---|
| Propostas | [ZIP setembro/2026](https://repositorio.dados.gov.br/seges/comprasgov/propostas/2026/09/) e [LEIAME oficial](https://repositorio.dados.gov.br/seges/comprasgov/propostas/LEIAME.md) | Arquivo integral; somente propostas de itens homologados |
| Contratos | [OpenAPI Compras.gov.br](https://dadosabertos.compras.gov.br/v3/api-docs), módulo contratos | Amostra filtrada por órgão e início de vigência; não inventário nacional |
| Documentos da compra | [Manual oficial PNCP](https://pncp.gov.br/manual/pt-br/latest/contratacao/consultar_todos_documentos_de_uma_contratacao.html) | Cinco metadados de documentos de uma compra |
| Detalhe/anexos do contrato | [Manual oficial PNCP, serviços de contratos e documentos](https://pncp.gov.br/manual/pt-br/latest/singlehtml/) | Um detalhe e quatro metadados de anexos; binários não baixados |

Respostas completas em `data/diagnostico/complementos/`, ignorado pelo Git. URLs, horários UTC, tamanhos, hashes e perfil agregado em [perfil do diagnóstico](diagnostico/perfil_complementos_etapa03.json).

Reprodução, na raiz do repositório:

```bash
python3 collector/scripts/diagnosticar_complementos.py
```

O script usa apenas a biblioteca padrão, duas tentativas por recurso, timeout de 25 segundos e limite de 10 MiB por resposta. A consulta de contratos usa exemplos fixos para repetir os vínculos; o resultado pode mudar na origem. Se os ZIPs do diagnóstico inicial existirem, também compara chaves com os itens do mesmo mês. Não grava linhas no PostgreSQL.

## Propostas e participações

O ZIP contém 10.510 linhas e 10.510 IDs de proposta, mas apenas 10.277 pares distintos de item/participante. Portanto, **não usar fornecedor + item como chave única da proposta**: isso descartaria 233 registros distintos da amostra. Há colocações além da vencedora e classificação ausente; um valor ausente não vira colocação zero.

| Campo original | Modelagem |
|---|---|
| `id` | `participacoes.chave_origem`, texto, único por fonte/base |
| `id_compra` | Resolver identidade oficial da compra e snapshot do processo |
| `id_compra_item` | Resolver identidade oficial e snapshot do item do mesmo processo/base |
| `identificacao_participante`, `nome_participante` | Preservar textos, inclusive zeros; fornecedor interno opcional até resolução validada |
| `valor_proposta_calculado` | `valor_proposta`, NUMERIC(28,8) |
| `valor_lance_calculado` | `valor_lance`, NUMERIC(28,8) |
| `valor_negociado_julgamento_calculado` | `valor_negociado`, NUMERIC(28,8) |
| `classificacao`, `situacao_proposta`, `situacao_item`, `homologado` | Campos independentes; situação preservada como código, sem rótulos presumidos |
| `data_hora_inclusao`, `data_hora_alteracao` | Timestamp sem fuso, conforme recebido; não converter para UTC sem confirmar o fuso |
| Demais campos | `atributos_origem` e original rastreável |

O LEIAME orienta a precedência de valor final: negociado, depois lance, depois proposta. Preservar os três valores e registrar essa regra no transformador; não assumir equivalência de unidades ou custo total/unitário sem validação adicional. Classificação `1` representa vencedora segundo o LEIAME, mas não substitui o relacionamento com resultados homologados.

**Cobertura:** o repositório informa itens incluídos desde 01/01/2022, já homologados. Não representa todo o histórico de lances nem garante cobertura universal. Contagem deve usar participantes distintos no conjunto coberto, sem somar linhas de propostas como se fossem empresas diferentes. Ausência de propostas não significa zero participantes. A comprovação de completude por item/processo continua sendo responsabilidade do importador e do manifesto.

**Competência:** o LEIAME informa particionamento pela inclusão do item. No ZIP de setembro, a coluna `data_hora_inclusao` contém também outubro. Preservar separadamente a competência do arquivo e as datas dos registros. Não presumir que essa coluna seja a data de inclusão do item ou que tenha a mesma semântica da publicação PNCP. A interseção com itens do mês e os vínculos compra/item estão quantificados no perfil; ausências exigem busca em outros períodos ou rejeição diagnosticada.

## Contratos e vínculos

Endpoints verificados na API Compras.gov.br:

- `/modulo-contratos/1_consultarContratos`: exige órgão e intervalo de início de vigência, com paginação.
- `/modulo-contratos/1.1_consultarContratos_Id?tipo=idCompra&codigo=...`: busca por compra; também aceita `numeroControlePncpContrato`.
- `/modulo-contratacoes/1.1_consultarContratacoes_PNCP_14133_Id`: confirma a compra correspondente.

O contrato `00394445000101-2-000222/2026` aponta para `idCompra=15200405001682027` e `numeroControlePncpCompra=00394445000101-1-000010/2027`. A compra consultada confirmou as duas chaves. O identificador de contrato é diferente do identificador de compra; não vincular por semelhança do objeto ou nome de fornecedor.

A amostra tem compra identificada como 2027, embora publicação e contrato sejam de 2026. Isso é um dado da fonte a sinalizar, não uma correção automática de ano. Comparações temporais devem validar e registrar inconsistências antes de produzir sinais.

`contratos` mantém identidade estável por fonte/chave oficial. `contratos_versoes` preserva por base número, órgão/fornecedor, objeto, vigência, valores e exclusão. Para esta fonte, preferir número de controle PNCP como chave; registros sem ele exigem regra alternativa explícita de identidade ou rejeição no importador. Não usar apenas número do contrato, que se repete entre órgãos.

`contratos_processos` guarda vínculos entre snapshots da mesma base, sem restringir a um único contrato por processo ou a um único processo por contrato. `tipo_chave_vinculo` registra `idCompra` ou `numeroControlePncpCompra`; `chave_vinculo` preserva a evidência. O importador deve conferir igualdade das chaves; a FK garante integridade da base, não verifica sozinha o significado de uma chave textual.

**Assinatura:** a API Compras.gov.br consultada expõe vigência; ela não pode substituir assinatura. O detalhe PNCP `/v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}` foi consultado e informa `dataAssinatura`, registrada separadamente em `contratos_versoes.data_assinatura` quando efetivamente adquirida. O enriquecimento deve preservar proveniência de ambas as respostas.

## Documentos

Endpoints PNCP verificados:

- `/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos`.
- `/v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/arquivos`.

Compra de exemplo: `10744098000145-1-000187/2026`; contrato de exemplo: `00394445000101-2-000222/2026`. Foram encontrados cinco e quatro anexos, respectivamente. Campos de retorno variam: tipo numérico e status ativo não vieram em todos os documentos de contrato; manter NULL nesses casos.

`documentos` guarda metadados por base, com **um único alvo**: snapshot de processo ou de contrato da mesma base. A chave deve incluir recurso pai e sequencial do documento, por exemplo `orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos/{documento}`; o sequencial isolado não é global. Usar o contexto da URL/consulta: no retorno de anexos contratuais, campos chamados `anoCompra` e `sequencialCompra` reproduzem o contexto do contrato do exemplo.

URL oficial e título não comprovam aquisição do binário. `chave_objeto`, `sha256` e `tamanho_bytes` permanecem todos NULL até o download validado, ou devem ser preenchidos juntos. A aquisição futura de PDF/anexos terá validação própria; o coletor de ZIPs/CSV não deve ser reutilizado para PDFs sem adaptação. Registros existentes são snapshots: atualização de status/URL/conteúdo deve gerar nova base/versionamento.

## Migração e entrega

A revisão `0004_complementos` acrescenta cinco tabelas e quatro alvos opcionais à proveniência: participação, versão contratual, vínculo contrato/processo e documento. Mantém exatamente um alvo por registro e unicidade com NULLs não distintos. As novas FKs impedem cruzamento entre bases e entre item e processo incorretos.

Para respostas JSON, `membro_arquivo` identifica o conjunto de registros e `numero_linha` será o ordinal positivo do registro, conforme contrato do importador; não fingir que o JSON possui linhas CSV. Objetos originais e seus hashes continuam preservados pelo controle de aquisição.

Permissões seguem os domínios existentes: processamento insere, API lê, coletor acessa apenas metadados de coleta. Nenhum papel runtime recebe UPDATE/DELETE nas novas tabelas. Ao aplicar migração, executar o comando administrativo de permissões. O downgrade recusa remoção quando houver proveniência dos novos domínios, para não descartá-la silenciosamente.

A etapa 03 entrega **esquema e restrições validados**, com cobertura documentada. Ampliar os conectores para os novos recursos, importar linhas, reconciliar cobertura e calcular atributos são tarefas seguintes. O coletor de produção continua atendendo os quatro ZIPs originais; os novos recursos foram acessados somente pelo diagnóstico.
