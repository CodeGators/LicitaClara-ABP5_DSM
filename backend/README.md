# Backend — FastAPI

Ambiente local, endpoints operacionais, consultas versionadas de processos/itens/documentos e esquema PostgreSQL com quatro migrações implementados. O coletor e a preparação/importação estão operacionais. Os ensaios de ML permanecem sem publicação de scores. Veja os [contratos, filtros e comandos da etapa 06](../docs/API_CONSULTAS.md).

A etapa 02 do plano de conclusão acrescenta `GET /api/v1/itens` e `GET /api/v1/itens/{item_id}`. Esses endpoints retornam uma linha por item, contexto do processo e resultados por fornecedor, sem modificar as sete rotas originais. Ver [contratos de itens/processos e testes manuais](../docs/CONTRATOS_ITENS_PROCESSOS.md).

## Instalar e executar

Usar Python 3.12.x, Docker Compose e uv 0.13.2. Executar a partir da raiz do repositório:

```bash
# Instalar uv 0.13.2, se necessário: https://docs.astral.sh/uv/getting-started/installation/
cp .env.example .env  # somente se .env ainda não existir
uv sync --locked --all-packages --extra validation
docker compose --env-file .env -f infra/compose.yaml up -d --wait
uv run --locked --package licita-backend python -m licita_backend.db.permissions bootstrap
uv run --locked --package licita-backend alembic -x role=licita_migrator upgrade head
uv run --locked --package licita-backend python -m licita_backend.db.permissions apply
uv run --locked --package licita-backend python -m licita_backend.db.permissions local-logins
uv run --locked --package licita-backend uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Nesta máquina, uv 0.13.2 foi instalado em `~/.local/bin/uv` e está disponível no PATH. As senhas do exemplo são apenas para desenvolvimento. Nesta máquina, um `.env` ignorado pelo Git foi criado com senha local aleatória. Não substituí-lo pelo exemplo se o volume já estiver inicializado: mudar variáveis não altera a senha persistida no PostgreSQL.

A configuração lê `.env` relativo ao diretório atual. Para outro diretório de execução, fornecer variáveis de ambiente explicitamente. Não há banco alternativo SQLite ou fallback silencioso.

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- `GET /api/v1/health`: processo ativo, sem depender do banco.
- `GET /api/v1/ready`: consulta PostgreSQL; 200 disponível, 503 indisponível.
- OpenAPI: http://127.0.0.1:8000/openapi.json

`--no-access-log` evita duplicar os logs HTTP JSON com o access log padrão do Uvicorn. Logs de inicialização do servidor continuam no formato do Uvicorn. A base local importada pode ser consultada em `/api/v1/base/status` e `/api/v1/processos`.

## Testes

Os testes sem integração não precisam de PostgreSQL:

```bash
uv run --locked --all-packages --extra validation ruff check .
uv run --locked --all-packages --extra validation ruff format --check .
uv run --locked --all-packages --extra validation pytest -m 'not integration'
```

Para integração, criar um banco separado (o comando falha se já existir; nesse caso basta seguir):

```bash
docker compose --env-file .env -f infra/compose.yaml exec -T postgres sh -c 'createdb -U "$POSTGRES_USER" licita_clara_test'
uv run --locked --all-packages --extra validation pytest
```

`TEST_DATABASE_URL` deve apontar para banco descartável com nome terminado em `_test`. Se ausente, os testes de integração são pulados; para validar a etapa completa, eles devem executar. As tabelas temporárias de teste têm nomes exclusivos e são removidas ao terminar. Nunca apontar os testes para o banco da aplicação.

Configuração, propriedade do esquema, sessões e contratos: [CONTRATOS_BACKEND_E_DADOS.md](../docs/CONTRATOS_BACKEND_E_DADOS.md).

## Migrações e papéis

Revisão atual: `0004_complementos` (após `0001_coleta`, `0002_dominio` e `0003_proveniencia`). São 34 tabelas; propostas, contratos e anexos estão descritos no [diagnóstico complementar](../docs/DIAGNOSTICO_PARTICIPACOES_CONTRATOS_DOCUMENTOS.md).

`MIGRATION_DATABASE_URL` é uma conexão administrativa separada de `DATABASE_URL`. Não é usada pela aplicação HTTP. Os comandos de instalação acima criam os grupos NOLOGIN, aplicam migrações sob o papel proprietário, concedem permissões e geram logins locais de API/coleta/processamento.

Nesta máquina, o `.env` já foi atualizado com as conexões separadas e as quatro revisões estão aplicadas. O comando `local-logins` é idempotente quando os logins e suas credenciais estão no `.env`; não imprime senhas nem cria credenciais remotas. Para nuvem, o operador deverá provisionar logins e grants com as permissões disponibilizadas pelo provedor.

Verificar estado, sem alterar o banco:

```bash
uv run --locked --package licita-backend alembic -x role=licita_migrator current
uv run --locked --package licita-backend alembic -x role=licita_migrator check
uv run --locked --package licita-backend alembic history
```

Após mudar as credenciais, reiniciar a API para que ela leia o `.env`. `upgrade head` aplica apenas revisões pendentes. Não editar revisões já compartilhadas: criar uma nova migração para alterações posteriores. Downgrades removem estruturas e devem ficar restritos a bancos descartáveis ou a recuperação planejada; os testes exercitam downgrade em schemas próprios no banco `_test`, sem tocar no banco da aplicação.

O dicionário implementado, chaves, snapshots e permissões estão em [BANCO_DE_DADOS.md](../docs/BANCO_DE_DADOS.md). Propostas, contratos e documentos já possuem diagnóstico e esquema na revisão `0004_complementos`; cobertura real e vínculos dependem do recorte importado. O piloto atual não tem propostas ou contratos vinculáveis.

## Consultas de dados reais

As sete rotas de leitura da [etapa 06](../docs/API_CONSULTAS.md) estão disponíveis no Swagger. Aceitam seleção de base por UUID; sem seleção explícita, usam a base validada mais recente. O frontend ainda não está integrado. Para preservar as dependências do ensaio ML no mesmo ambiente, executar:

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Os scores continuam nulos com análise `nao_publicada`. Valores globais do processo e dos itens do recorte são campos distintos; consultar a documentação antes de usá-los em totais ou filtros.
