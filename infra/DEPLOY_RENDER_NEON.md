# Publicação gratuita: Render e Neon

A API atende consultas e gera relatórios a partir do PostgreSQL. O primeiro deploy
copia o banco já analisado; não executa os scripts de preparação ou treinamento.
Os CSVs e artefatos da ML permanecem guardados fora do servidor web.

## Ordem da primeira publicação

1. Preparar e testar esta branch; integrar na `main` antes de criar os serviços.
2. Criar no Neon um projeto gratuito com PostgreSQL 17 e um banco vazio.
3. Restaurar uma cópia do PostgreSQL local, conferindo versões, contagens e análises.
4. Criar a API gratuita no Render a partir do `render.yaml` da raiz.
5. Criar o frontend estático no Render e configurar as duas URLs públicas.
6. Testar o acesso por uma janela anônima, inclusive após a API ficar inativa.

São duas contas: [Neon](https://console.neon.tech/signup) e
[Render](https://dashboard.render.com/register). Usar os endereços gratuitos dos
provedores; não é necessário comprar domínio. Os planos têm franquias de uso.
API e banco devem ficar em regiões próximas, preferencialmente no leste dos EUA.

## 1. Copiar o banco local

Com o PostgreSQL local em execução, na raiz:

```bash
uv run --locked --package licita-backend python scripts/exportar_banco.py
```

O comando cria um `.dump` e um manifesto SHA-256 em `data/deploy/`, ignorado pelo
Git, com permissões locais restritas. Não modifica o banco nem exporta as senhas
dos papéis PostgreSQL. O dump contém dados e metadados internos da aplicação;
não publicar o arquivo em um repositório ou endereço aberto.

A exportação usa `pg_dump` 17 dentro do Compose e omite proprietários e grants.
No destino, reconfigurar a propriedade das tabelas e um login restrito de leitura
para a API. Não usar a conexão administrativa da migração no serviço web.

## 2. Preparar o Neon

Criar um projeto Free, PostgreSQL 17, com banco vazio. Em Connect, selecionar a
conexão **Direct**, sem `-pooler`, para a restauração. Conferir o SHA-256 da cópia
antes de importar. A restauração usa `pg_restore` 17, sem `--clean`, em banco novo;
nunca executar contra a origem local. Restaurar o esquema e os dados completos,
incluindo `alembic_version`, tabelas de análise e publicações.

Copiar `infra/neon.env.example` para `.env.neon` na raiz e preencher as conexões
somente nesse arquivo local, com permissão `600`. Ele é ignorado pelo Git.
A URI que o Neon fornece começa com `postgresql://`; a configuração SQLAlchemy da
API exige `postgresql+psycopg://`, preservando `sslmode=require` e os demais
parâmetros. Não enviar senhas ou URIs completas em mensagens ou screenshots.

Antes de publicar a API, comparar origem/destino: quantidade de itens, compras,
resultados e modelos; bases e execuções publicadas; assinatura dos valores IF.
Uma cópia restaurada não precisa rodar Alembic novamente: já inclui a versão do
esquema. Futuras migrações ficam em etapa administrativa controlada.

## 3. Criar a API no Render

Em New > Blueprint, conectar o repositório e selecionar o `render.yaml` da raiz.
Esse arquivo cria **somente a API Free**, sem banco Render, disco pago ou worker.
Confirmar os valores antes de criar:

| Campo | Valor |
| --- | --- |
| Branch | `main` |
| Runtime | Python; a `.python-version` fixa a linha 3.12 |
| Região | Virginia |
| Plano | Free |
| Build | `uv sync --locked --package licita-backend --no-dev` |
| Start | Comando Uvicorn do `render.yaml`, sem `--reload`, um worker |
| Health check | `/api/v1/ready` |
| `DATABASE_URL` | Conexão Neon do login restrito da API, com TLS |
| `CORS_ALLOWED_ORIGINS` | Inicialmente `[]`; atualizar após criar o frontend |

O build instala backend e shared. Não instala a ML, scikit-learn, joblib ou
PyArrow. Nenhum comando de treinamento, carga ou migração roda na inicialização.
Deploy automático fica desligado na primeira publicação para não trocar a
versão em validação. O comando usa a porta `$PORT` fornecida pelo Render.

Ao concluir, guardar a URL pública real da API e verificar:

- `/api/v1/health`: processo disponível.
- `/api/v1/ready`: conexão ao banco disponível.
- `/api/v1/base/status`: base restaurada encontrada.

## 4. Criar o frontend no Render

Em New > Static Site, conectar o mesmo repositório:

| Campo | Valor |
| --- | --- |
| Branch | `main` |
| Auto-Deploy | Off durante a primeira validação |
| Root Directory | `Frontend-licita-clara` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |
| `NODE_VERSION` | `20.19.0` |
| `VITE_API_URL` | `https://URL-REAL-DA-API.onrender.com/api/v1` |
| `VITE_API_STARTUP_WAIT` | `true` |

Adicionar uma regra **Rewrite**, não Redirect: origem `/*`, destino `/index.html`.
Assim, abrir ou atualizar `/ranking/:id`, `/fornecedores` e outras rotas funciona.
O proxy de `vite.config.js` atende somente o desenvolvimento local.

Na API, configurar `CORS_ALLOWED_ORIGINS` como um array JSON com a URL real do
frontend, por exemplo `["https://URL-REAL-DO-FRONTEND.onrender.com"]`, sem barra
final. As variáveis `VITE_*` são públicas e entram no build; nunca colocar a
conexão do banco nelas. Mudanças em `VITE_*` exigem novo build do frontend.

## 5. Primeiro acesso e teste

A API gratuita pode ficar suspensa por inatividade. Com
`VITE_API_STARTUP_WAIT=true`, a consulta inicial da base aguarda por até 90 segundos,
retentando apenas falhas de rede e respostas transitórias. Um erro permanente,
como base inexistente, continua aparecendo imediatamente. As demais consultas
mantêm seu limite normal. Não há requisições periódicas para impedir a suspensão.

Na pasta do frontend, os testes específicos são:

```bash
npm test
npm run test:e2e
npm run test:startup
npm run build
```

Validar na URL hospedada: painel, pesquisa, múltiplas sinalizações, expansão de
compras, detalhe de item, fornecedores e exportação PDF/CSV. Conferir recarregamento
direto das rotas e o retorno após a API despertar. Desligar a aplicação local e
confirmar que o site continua consultando o banco remoto.

## Atualização posterior

Atualizar o código não deve recriar o banco. Dados novos e eventuais novos treinos
são trabalhos separados, inicialmente locais. Preservar cópias, versões dos
modelos e publicações; publicar uma nova análise somente depois de validá-la.
Manter uma cópia recente do banco fora do serviço web. O disco efêmero do Render
não guarda a única cópia de dados, modelos ou arquivos de treinamento.

Referências: [Render Free](https://render.com/docs/free),
[Blueprints](https://render.com/docs/blueprint-spec),
[Neon Free](https://neon.com/pricing),
[migração PostgreSQL para Neon](https://neon.com/docs/import/migrate-from-postgres).
