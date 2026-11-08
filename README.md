# Licita Clara — ABP5 DSM

Aplicação acadêmica para explorar anomalias estatísticas em itens de compras
públicas. Inclui frontend React/Vite, API FastAPI, PostgreSQL, preparação de
CSVs, Isolation Forest, Autoencoder e relatórios PDF/CSV. Scores são sinais
experimentais; não representam probabilidade de fraude.

## Instalar na máquina de outro integrante

Siga o **[guia de instalação da equipe](scripts/README.md)**. Ele cobre instalação,
PostgreSQL/migrações, recebimento dos ZIPs e estes dois comandos, na raiz:

```bash
uv run --locked --all-packages --extra validation python scripts/popular_banco.py
uv run --locked --all-packages --extra validation python scripts/treinar_e_analisar.py
```

O primeiro organiza e importa os dados. O segundo treina os modelos, mostra
progresso por grupos concluídos, analisa a base e publica os Scores experimentais
localmente. Consulte os pré-requisitos antes de executá-los. O GitHub não inclui
os ZIPs, modelos, banco populado ou senhas. O manifesto de entradas está em
[`config/equipe/dados.json`](config/equipe/dados.json).

Uma reconstrução por CSV não inclui enriquecimentos de API e bases históricas
existentes em outra máquina; para duplicar exatamente um estado operacional,
é necessário restaurar também seu banco e objetos. Detalhes no guia.

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
| `infra/` | PostgreSQL local com Docker Compose |
| `docs/` | Documentação local opcional, ignorada pelo Git |

## Executar após a configuração

Em dois terminais, na raiz:

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

```bash
npm run dev --prefix Frontend-licita-clara
```

Frontend: http://localhost:5173. Swagger: http://127.0.0.1:8000/docs.

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
