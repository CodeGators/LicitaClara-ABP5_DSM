# Coletor Compras.gov.br

CLI Python independente da aplicação FastAPI. Descobre os arquivos anunciados no repositório oficial, baixa ZIPs e registra sua proveniência no PostgreSQL. Não importa linhas para as tabelas de domínio nem executa treinamento (próximas etapas).

## Executar

Execute na raiz do repositório, com PostgreSQL migrado e `.env` configurado conforme o README principal:

```bash
uv sync --locked --all-packages
uv run --locked --package licita-collector licita-collector coletar --inicio 2026-09 --fim 2026-09
```

O padrão coleta `compra`, `compra_item`, `item_resultado` e `material`. A opção explícita `--arquivos propostas` coleta o ZIP mensal de propostas. Para um arquivo ou intervalo histórico:

```bash
uv run --locked --package licita-collector licita-collector coletar --inicio 2025-10 --fim 2026-09 --arquivos compra
uv run --locked --package licita-collector licita-collector retomar --execucao-id UUID_DA_EXECUCAO
uv run --locked --package licita-collector licita-collector reprocessar --arquivo-id UUID_DO_ARQUIVO
uv run --locked --package licita-collector licita-collector reprocessar --arquivo-id UUID_DO_ARQUIVO --extrair
```

Substitua os UUIDs pelos identificadores emitidos em JSON. Cada arquivo/mês tem uma execução, inclusive em intervalos. Código de saída 1 indica ao menos uma falha; os demais arquivos continuam. Retomar mantém o identificador original; uma execução já concluída apenas verifica o objeto armazenado. Reprocessar verifica SHA-256, tamanho e CRC sem consultar a fonte; `--extrair` publica CSVs em um diretório novo. Destinos existentes são preservados.

## Configuração e operação

`COLLECTOR_DATABASE_URL` deve usar o login restrito do coletor, sem privilégios administrativos. São usadas somente as tabelas `execucoes_coleta`, `arquivos_coletados` e `execucoes_arquivos`. Duração é calculada por `concluido_em - iniciado_em`; tamanho e hash ficam no registro do arquivo. Credenciais e mensagens de drivers não são impressas.

| Variável | Padrão |
|---|---|
| `STORAGE_BACKEND` | `local` |
| `STORAGE_ROOT` | `data/objects` |
| `COLLECTOR_TEMP_DIR` | `data/tmp/collector` |
| `COLLECTOR_EXTRACT_DIR` | `data/extracted` |
| `COLLECTOR_TIMEOUT` | 30 segundos por operação de rede |
| `COLLECTOR_ATTEMPTS` | 3 tentativas com espera progressiva limitada |
| `COLLECTOR_MAX_DOWNLOAD_BYTES` | 104857600 (100 MiB) |
| `COLLECTOR_MAX_UNCOMPRESSED_BYTES` | 2147483648 (2 GiB) |
| `COLLECTOR_MAX_MEMBERS` | 32 |
| `COLLECTOR_MAX_COMPRESSION_RATIO` | 200 |

O limite de 100 MiB atende o piloto diagnosticado; competências maiores exigem ajuste explícito. Não existe agendamento automático nesta etapa.

Os originais ficam em `raw/comprasgov/{modulo}/{arquivo}/{ano}/{mes}/{sha256}/{nome.zip}`. Um conteúdo repetido reutiliza o registro e a chave, com nova observação da coleta. Se a fonte mudar, uma nova versão é preservada. Uma falha entre gravação do objeto e commit pode deixar um objeto ainda sem registro; a retomada usa a mesma chave e conclui o registro. Não remova objetos manualmente.

Locks consultivos do PostgreSQL impedem coletas conflitantes por arquivo/mês e são liberados ao terminar ou perder a conexão. Downloads usam blocos de até 1 MiB quando a fonte confirma Range, tamanho e ETag forte. Apenas blocos completos são anexados ao parcial. Mudança de ETag reinicia o download; sem essas garantias, uma retentativa baixa novamente desde o início. Preserve `data/tmp/collector` para retomar após falha.

Arquivo ausente (HTTP 404 ou não anunciado), falha de rede e ZIP inválido têm códigos distintos. Validação rejeita HTML, CRC inválido, travessia de diretórios, links simbólicos, criptografia, membros não CSV e expansão acima dos limites. A gravação local usa temporário e substituição atômica; o banco só confirma o arquivo depois de validar e armazenar.

## S3 / Cloudflare R2 opcional

```bash
uv sync --locked --all-packages --extra s3
```

Configure `STORAGE_BACKEND=s3`, `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ACCESS_KEY_ID` e `OBJECT_STORAGE_SECRET_ACCESS_KEY`. Para R2, configure também `OBJECT_STORAGE_ENDPOINT=https://<conta>.r2.cloudflarestorage.com`. O bucket deve existir e ser privado. Credenciais precisam de leitura, escrita e HEAD dos objetos; o coletor não cria buckets nem altera ACLs. O upload envia checksum MD5 e confirma tamanho e SHA-256 em metadados antes do registro.

O contrato do adaptador é testado com cliente simulado. Provisionamento e teste em uma conta S3/R2 real ainda não foram realizados. O ambiente atual usa disco local. A API ainda não oferece download desses objetos.

## Verificação

```bash
uv run --locked --all-packages pytest -q
uv run --locked --all-packages ruff check .
uv run --locked --all-packages ruff format --check .
```

Integração exige `TEST_DATABASE_URL` em banco terminado em `_test`; os testes criam e removem apenas seus schemas. Cobrem aquisição HTTP controlada, retomada, erro transitório, resposta HTML, arquivo incompleto, CRC, extração, repetição, versões e concorrência usando permissões de coletor no PostgreSQL.

Os scripts em `scripts/` continuam sendo diagnósticos exploratórios, separados da CLI. Consulte [diagnóstico da fonte](../docs/DIAGNOSTICO_COMPRASGOV.md). A competência PNCP se refere à publicação; em pesquisa de preços, à compra. O Portal da Transparência não integra o coletor do MVP.

## Aquisição complementar implementada

A CLI agora atende propostas em ZIP e consultas por compra/controle oficial no Compras.gov.br e PNCP. O comando `complementar` deriva compras de um CATMAT num arquivo material já registrado, pagina e reconcilia respostas, registra execuções por consulta e guarda envelopes JSON versionados. A fonte PNCP é explícita na proveniência.

```bash
uv run --locked --package licita-collector licita-collector coletar --inicio 2026-09 --fim 2026-09 --arquivos propostas
uv run --locked --package licita-collector licita-collector complementar --competencia 2026-09 --material-arquivo UUID_MATERIAL --catalogo 486054
```

Substitua UUID_MATERIAL pelo identificador de um arquivo material real. Propostas usam inclusão do item segundo o LEIAME; consultas JSON usam a competência como janela de referência, sem reescrever as datas da origem. Envelopes JSON podem ser retomados/reprocessados pelos mesmos comandos; não requerem extração. Totais incompatíveis ou paginação ignorada/repetida provocam falha, sem confirmação do objeto.

São adquiridos metadados de documentos e detalhe contratual; PDFs não são baixados. A importação desses arquivos cabe ao pacote ML. [Regras e evidências da etapa 05](../docs/PREPARACAO_E_IMPORTACAO.md). Scripts exploratórios permanecem separados da aquisição de produção.
