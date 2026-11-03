# Contratos iniciais entre backend, coleta e modelagem

Atualizado na etapa 04, 20/10/2026. Compras.gov.br é a fonte principal, com PNCP como complemento explícito para anexos e assinatura contratual. O Portal da Transparência é um diagnóstico histórico preservado, sem integração prevista no MVP inicial.

## Responsabilidade pelo banco

O backend é o responsável pelo esquema PostgreSQL. Migrações Alembic estão em `backend/migrations/`: `0001_coleta`, `0002_dominio`, `0003_proveniencia` e `0004_complementos`, aplicadas e verificadas na etapa 03. Nenhum serviço deve executar `create_all()` em produção ou criar tabelas na inicialização.

O coletor poderá gravar somente no domínio operacional de coleta, por contrato versionado: execuções, arquivos e observações. Importações pertencem à preparação. A preparação poderá gravar bases e dados públicos; a modelagem, versões de modelos e análises. A API consulta dados publicados e futuramente grava revisões e relatórios. Papéis separados de banco são provisionados explicitamente pelo comando `licita_backend.db.permissions`; sua criação é separada do histórico de migrações porque papéis são objetos do cluster. O usuário PostgreSQL do Compose é exclusivamente um administrador local, não a identidade de produção da API.

Antes da primeira escrita por outro serviço, formalizar colunas, unicidade e transações na mesma entrega da migração. Se for necessário compartilhar código de persistência, extraí-lo para um pacote próprio com testes, em vez de copiar modelos ou importar a aplicação HTTP nos outros serviços. O coletor adquire objetos; o pacote ML já possui preparação e importação do recorte. Suas URLs locais são separadas no `.env`; o futuro uso do esquema deve respeitar os grants documentados.

## Aquisição e objetos

O coletor preserva o original e registra fonte/módulo, competência com sua semântica, URL, instante UTC, tamanho, checksum e chave do objeto. Revisões de conteúdo geram novas versões; não sobrescrever um original referenciado por uma base publicada.

A interface compartilhada em `shared/`, `ObjectStorage`, define `put(key, source)` e `open(key)`. A escrita retorna chave, tamanho e SHA-256. Chaves são relativas ao bucket/raiz. O adaptador local publica o arquivo por substituição atômica; não representa por si só uma política de imutabilidade. O coletor usa chaves versionadas por SHA-256 e locks PostgreSQL por arquivo/mês.

O adaptador S3/R2 mantém a mesma interface e confirma tamanho/metadados do upload antes de retornar; seu contrato foi testado com cliente simulado. Não há credenciais de nuvem, bucket provisionado ou teste remoto realizado. Não usar ETag como substituto obrigatório do SHA-256 do conteúdo. O diretório local é privado e controlado pela aplicação; não permitir que usuários externos criem symlinks nele.

## Importação e análise

A preparação produz manifesto com esquema, transformação/código, filtros, contagens, rejeições e arquivos/checksums de origem. Preservar os identificadores oficiais de compra e item; correspondência de catálogo exige vínculo comprovado. A mesma competência pode ter datas de referência diferentes conforme o módulo.

A inferência recebe base e modelos explícitos. Registra execução, resultados brutos/normalizados e limitações; publica uma versão ativa somente após validar o lote completo. A troca da versão publicada é transacional. Não sobrescrever resultados de análises anteriores nem treinar em requisições HTTP.

A preparação/importação de um recorte real está implementada, com manifesto e Parquet versionados. Inferência e publicação de análises permanecem como etapas seguintes.

## Configuração e transações

Python 3.12.x é a versão inicial. `uv.lock` fixa dependências resolvidas dos pacotes; builds usam setuptools fixado. Comandos locais são executados a partir da raiz do repositório. Cada pacote tem dependências próprias e pode ser instalado isoladamente.

`DATABASE_URL` é validada na criação da aplicação, sem abrir conexão imediatamente. A indisponibilidade do banco não impede `/health`; `/ready` testa uma consulta real com timeout e retorna 503. A instância de engine/pool vive durante o ciclo da aplicação e é descartada no shutdown.

Sessões fecham e desfazem alterações não confirmadas. Serviços de escrita devem delimitar `transaction(factory)` e terminar o commit antes de retornar sucesso HTTP; o helper executa rollback em exceções. `get_session` não faz commit implícito depois de uma resposta já enviada. Não reutilizar uma sessão global entre requisições.

## Logs e execução

Logs da aplicação usam JSON, instante UTC e identificador gerado por requisição, devolvido em `X-Request-ID`. Não incluem query string, corpo, senha ou URL do banco. Eventos de conexão indisponível registram a classe da falha, sem o detalhe potencialmente sensível do driver.

O coletor emite JSON por arquivo com IDs de execução/arquivo, hash, bytes e reutilização. Falhas têm código e classe sanitizados; duração é derivada dos horários no banco. Retomada usa o mesmo ID; reprocessamento valida um objeto registrado. ML possui CLI de preparação/importação e um [ensaio independente de treinamento](validacao_nucleo/RESULTADO.md), sem publicação de modelos/scores de produção. Os scripts de diagnóstico permanecem separados. Consulte o [README do coletor](../collector/README.md).

Referências de implementação: [workspaces e lockfile uv](https://docs.astral.sh/uv/concepts/projects/workspaces/), [ciclo de vida FastAPI](https://fastapi.tiangolo.com/advanced/events/). As dependências efetivamente verificadas são as registradas no lockfile do repositório.

## Evolução da etapa 03

Há identidades estáveis de processo/item e snapshots por versão de base. Análises e revisões referenciam snapshots, com FKs compostas para impedir cruzamentos entre bases. O estado atual de revisão será derivado do último evento; não há coluna mutável de revisão no snapshot do processo.

O coletor grava execuções, arquivos e observações; o processamento grava importações e dados. `execucoes_arquivos` registra reutilização de um arquivo já conhecido, sem duplicar seu conteúdo. `proveniencias_registros` exige que a importação faça parte da base do registro. O contrato físico completo está no [dicionário do banco](BANCO_DE_DADOS.md).

A revisão `0004_complementos` inclui propostas (cobertura restrita a itens homologados), contratos com snapshots, vínculos e metadados de documentos. Proveniência aceita esses novos alvos, sempre com exatamente um alvo por registro e na mesma base. Os conectores complementares e a importação foram implementados na etapa 05; binários de anexos não são baixados. Ver [diagnóstico e contratos de campos](DIAGNOSTICO_PARTICIPACOES_CONTRATOS_DOCUMENTOS.md).

## Implementação da etapa 05

Leitores, política de resolução, formato de manifesto/Parquet, reconciliação e limites estão em [PREPARACAO_E_IMPORTACAO.md](PREPARACAO_E_IMPORTACAO.md). A versão da base depende dos arquivos, filtro e código. O coletor não importa dados de domínio; o processamento usa seu login restrito. Artefatos são gravados antes do commit; somente a base validada e confirmada no banco representa publicação técnica. Recuperação repete a mesma seleção sem atualizar snapshots. Não interpretar validação técnica como garantia de cobertura, aptidão para treino ou conclusão de auditoria.

## Consultas implementadas — etapa 06

A [API de consultas](API_CONSULTAS.md) fixa uma base validada por requisição, aceita `base_id` explícito e retorna metadados de paginação com o ID escolhido. Contratos Pydantic e OpenAPI documentam dinheiro decimal como string, ausência como `null` e análise `nao_publicada`. Valores globais do processo e soma de resultados ativos do recorte são distintos; uma soma com algum total desconhecido permanece nula. O filtro de homologação usa datas dos resultados ativos importados, com fornecedor e período correspondendo ao mesmo resultado quando combinados. Não publica os scores experimentais nem carrega modelos em requisições.

As consultas usam `DATABASE_URL` com o papel da API, sem escrita, migração ou aquisição externa. Foram verificadas com PostgreSQL de testes isolado e requisições HTTP sobre a base local real, preservando os dados.
