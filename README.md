# Licita Clara — ABP5 DSM

Aplicação acadêmica para explorar anomalias estatísticas em itens de compras
públicas. Inclui frontend React/Vite, API FastAPI, PostgreSQL, preparação de
CSVs, Isolation Forest, Autoencoder e relatórios PDF/CSV. Scores são sinais
experimentais; não representam probabilidade de fraude.

## Instalação passo a passo

Este roteiro prepara uma **instalação local nova**, do clone até a aplicação com
Scores. Execute os comandos na ordem indicada e espere cada etapa terminar.
Depois de entrar na pasta clonada, todos os comandos são executados na **raiz do
projeto**, onde ficam `pyproject.toml`, `alembic.ini` e `.env`.

### 1. Instalar os pré-requisitos

- Linux ou WSL2 com Docker disponível.
- Git, Python 3.12.x e uv 0.13.2.
- Node.js 20.19+ da linha 20 e npm.
- Docker com Docker Compose.
- Aproximadamente 30 GB livres para dados, modelos e arquivos temporários.

### 2. Clonar o repositório

```bash
git clone https://github.com/CodeGators/LicitaClara-ABP5_DSM.git
cd LicitaClara-ABP5_DSM
```

### 3. Criar o `.env` e instalar as dependências

```bash
cp .env.example .env
uv sync --locked --all-packages --extra validation
npm ci --prefix Frontend-licita-clara
```

Cada integrante usa seu próprio `.env`. Em uma instalação local nova, os valores
do exemplo funcionam com o Compose do projeto. Se alterar a senha, o nome ou a
porta do PostgreSQL, ajuste também `DATABASE_URL` e `MIGRATION_DATABASE_URL`.
A configuração inicial usa a porta `55432` para o banco.

Não substitua um `.env` de uma instalação existente: mudar o arquivo não altera
a senha que já foi gravada no volume do PostgreSQL. O `.env` fica fora do Git.

### 4. Subir o PostgreSQL

Com o Docker em execução:

```bash
docker compose --env-file .env -f infra/compose.yaml up -d --wait
```

Esse comando cria e inicia o banco local com armazenamento persistente.

### 5. Criar as tabelas e configurar as permissões

Execute nesta ordem:

```bash
uv run --locked --all-packages --extra validation python -m licita_backend.db.permissions bootstrap
uv run --locked --all-packages --extra validation alembic -x role=licita_migrator upgrade head
uv run --locked --all-packages --extra validation python -m licita_backend.db.permissions apply
uv run --locked --all-packages --extra validation python -m licita_backend.db.permissions local-logins
```

O Alembic cria as tabelas. O último comando gera no `.env` as conexões locais da
API, coleta e processamento, com as permissões correspondentes. São credenciais
de acesso ao banco; a aplicação não exige cadastro ou login de usuário.

### 6. Conferir os arquivos de dados incluídos no clone

Os **14 ZIPs originais com CSVs** estão versionados em
[`datasets/equipe/`](datasets/equipe/), organizados por mês. Eles já são baixados
ao clonar o repositório; não é necessário receber ou extrair um pacote separado.

```bash
uv run --locked --all-packages --extra validation python scripts/popular_banco.py --conferir
```

A conferência precisa confirmar **14 ZIPs**, com os nomes, tamanhos e hashes de
[`config/equipe/dados.json`](config/equipe/dados.json). `--conferir` apenas valida
os arquivos; não popula o banco nem treina modelos. A pasta contém cerca de
312 MB de dados comprimidos. Banco populado e modelos treinados serão gerados
localmente nos próximos passos.

### 7. Popular o banco

```bash
uv run --locked --all-packages --extra validation python scripts/popular_banco.py
```

Esse script organiza os CSVs, cataloga os itens e as unidades, prepara as
partições temporais e importa os dados operacionais. Espere a mensagem de banco
populado antes de seguir. A primeira preparação pode demorar vários minutos;
a saída identifica cada etapa em execução.

Os itens já poderão ser consultados, mas essa instalação ainda não terá seus
Scores publicados. O estado da importação fica em `data/equipe/estado.json`.

### 8. Treinar os modelos e analisar os itens

```bash
uv run --locked --all-packages --extra validation python scripts/treinar_e_analisar.py
```

Esse script treina Isolation Forest e Autoencoder, analisa os itens do banco e
publica a execução experimental para a aplicação local. A barra mostra a
porcentagem de grupos concluídos, atualizada ao final de cada lote, e uma
estimativa do tempo restante. O 100% indica o fim do treinamento; aguarde também
a conclusão da inferência e da publicação.

O padrão usa dois processos. Para reduzir o uso de memória:

```bash
uv run --locked --all-packages --extra validation python scripts/treinar_e_analisar.py --processos 1
```

Se houver interrupção, repita o mesmo comando com os mesmos dados: etapas e
lotes completos são conferidos e reutilizados. Um lote incompleto pode precisar
recomeçar. Itens sem modelo elegível continuam sem Score, com os motivos disponíveis.

A reconstrução usa os mesmos CSVs e regras de treinamento. Enriquecimentos
posteriores por API e bases históricas de outra máquina não são restaurados por
esses scripts, portanto UUIDs, cobertura e totais podem diferir. Para copiar
exatamente um estado operacional existente, também são necessários seu banco e
os objetos referenciados. Consulte o [guia detalhado](scripts/README.md).

### 9. Iniciar backend e frontend

Terminal 1, na raiz do projeto:

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Terminal 2, também na raiz:

```bash
npm run dev --prefix Frontend-licita-clara
```

Abra **http://localhost:5173**. A documentação da API está em
http://127.0.0.1:8000/docs. No ambiente local padrão, o frontend usa o proxy para
a API na porta 8000; não é necessário criar um `.env` adicional no frontend.

### Nas próximas vezes

Basta iniciar o PostgreSQL com o comando da etapa 4 e executar os comandos do
backend e frontend da etapa 9. **Não é necessário popular o banco ou treinar
novamente toda vez que abrir o projeto.**

Preserve `data/` e o volume do PostgreSQL: eles guardam os arquivos, modelos e
resultados. Não use `docker compose down -v` para apenas desligar o ambiente,
pois `-v` remove o volume do banco. Para parar o PostgreSQL preservando os dados:

```bash
docker compose --env-file .env -f infra/compose.yaml stop
```

## Estrutura

| Pasta | Conteúdo |
| --- | --- |
| `Frontend-licita-clara/` | Painel, itens/licitações sinalizadas, fornecedores e relatórios |
| `backend/` | API e migrações Alembic |
| `collector/` | Aquisição versionada de fontes públicas |
| `ml/` | Organização, agrupamento, treino, avaliação e inferência |
| `shared/` | Contratos de armazenamento compartilhados |
| `scripts/` | Instalação e processamento para a equipe |
| `config/equipe/` | Manifesto dos arquivos necessários |
| `datasets/equipe/` | 14 ZIPs originais dos CSVs de treino, avaliação e aplicação |
| `infra/` | PostgreSQL local com Docker Compose |
| `docs/` | Documentação local opcional, ignorada pelo Git |

## Verificação do código

Python 3.12, uv 0.13.2 e Node.js 20.19+ da linha 20. Dependências fixadas nos locks.

```bash
uv sync --locked --all-packages --extra validation
uv run --locked --all-packages --extra validation ruff check .
uv run --locked --all-packages --extra validation ruff format --check .
uv run --locked --all-packages --extra validation pytest -m 'not integration' -q
npm ci --prefix Frontend-licita-clara
npm run build --prefix Frontend-licita-clara
```

Integração exige PostgreSQL e `TEST_DATABASE_URL` em banco descartável terminado
em `_test`; consulte [backend/README.md](backend/README.md). Não execute testes
contra o banco da aplicação. Instruções específicas:
[ML](ml/README.md), [coleta](collector/README.md),
[frontend](Frontend-licita-clara/README.md) e [infraestrutura](infra/README.md).

## 📌 Sobre o projeto

Todo ano, o governo contrata empresas para fornecer produtos e serviços por meio de licitações. Esses dados são públicos, mas são tantos que fica muito difícil para uma pessoa analisar tudo e perceber quando algo foge do normal.

O **Licita Clara** nasceu para ajudar nisso. A ideia é analisar os dados de licitações e destacar casos que merecem atenção, como:

- 💰 Preços muito acima do que normalmente é cobrado;
- 🏢 Um mesmo fornecedor ganhando contratos com frequência fora do comum;
- 📊 Valores que fogem do padrão de um órgão público.

A ferramenta pode ser útil para **cidadãos**, **empresas que vendem para o governo** e **órgãos de controle** que querem acompanhar os gastos públicos com mais clareza.

> ⚠️ **Importante:** encontrar algo fora do padrão **não significa que houve irregularidade**. O sistema apenas indica pontos de atenção para que uma pessoa possa analisar com cuidado.

## 🎯 Objetivos

- Tornar os dados de licitações mais fáceis de entender;
- Apoiar a fiscalização e o controle social dos gastos públicos;
- Ajudar empresas a manterem boas práticas de conformidade (compliance).

## 👥 Equipe CodeGators

Projeto desenvolvido por estudantes como parte da disciplina de Aprendizagem Baseada em Projetos (ABP) do curso de Desenvolvimento de Software Multiplataforma (DSM).
