# Licita Clara — ABP5 DSM

Projeto acadêmico de detecção de anomalias em licitações públicas. A proposta prevê coleta de dados públicos, modelos de aprendizado não supervisionado e uma interface para priorizar processos para análise.

Anomalia estatística não comprova irregularidade.

## Acompanhamento e estado da entrega

O [plano de conclusão](docs/PLANO_CONCLUSAO.md) é o ponto de entrada para continuar o trabalho: contém etapas, branches, critérios de aceitação e instruções de teste. A [consolidação do repositório](docs/CONSOLIDACAO_REPOSITORIO.md) registra o inventário e a verificação da instalação em uma cópia limpa.

O frontend incorporou a entrega de 01/11/2026 e a [integração de consultas reais](docs/FRONTEND_CONSULTAS_REAIS.md): entrada em `/itens`, detalhe do item/processo e documentos. Painel, ranking experimental e fornecedores estão integrados à API; versões demonstrativas permanecem separadas e identificadas. Autenticação, revisão persistente, relatórios reais e publicação de análises validadas permanecem pendentes. A publicação experimental versionada já é selecionável nas telas reais. O piloto permanece sem índices elegíveis, com motivos explícitos. O Autoencoder está implementado para comparação experimental; a utilidade dos modelos continua inconclusiva. Clonar o repositório não importa automaticamente os dados locais nem instala modelos treinados.

## Estrutura

| Diretório | Conteúdo |
| --- | --- |
| `Frontend-licita-clara/` | React/Vite, consultas reais e demonstrações identificadas |
| `backend/` | FastAPI, consultas versionadas de processos/itens/documentos e endpoints operacionais |
| `collector/` | Coleta versionada do Compras.gov.br e diagnósticos |
| `shared/` | Contrato e adaptadores de armazenamento compartilhados |
| `ml/` | Preparação/importação reproduzível e ensaios de Isolation Forest; sem publicação de scores |
| `docs/` | Proposta em PDF, protótipo HTML e materiais visuais em `prototipo/` |
| `infra/` | PostgreSQL local com Docker Compose e documentação |
| `.github/workflows/` | CI Python com PostgreSQL descartável e build do frontend |

Além do protótipo visual, há uma API FastAPI com [consultas de processos, itens e documentos](docs/API_CONSULTAS.md) e ambiente PostgreSQL local. O esquema PostgreSQL tem 34 tabelas versionadas por Alembic. O coletor em lote já baixa e registra ZIPs reais; a preparação/importação de um recorte CATMAT está implementada. Um [ensaio do núcleo de ML](docs/validacao_nucleo/RESULTADO.md) treinou Isolation Forest com dados reais; sua utilidade para auditoria aguarda revisão independente. Não há modelo ou score publicado em produção. Nenhuma infraestrutura de nuvem foi provisionada. Compras.gov.br é a fonte principal; PNCP complementa a aquisição de metadados de documentos e detalhe contratual; Portal da Transparência permanece como diagnóstico histórico.

## Executar o frontend

Pré-requisitos: Node.js 20.19+ da linha 20 e npm; validação local realizada com Node.js 20.19.0 e npm 10.8.2. Executar na raiz:

```bash
npm ci --prefix Frontend-licita-clara
npm run dev --prefix Frontend-licita-clara
```

Para gerar a versão de produção, execute `npm run build` nessa mesma pasta. Mais detalhes no [README do frontend](Frontend-licita-clara/README.md).

## Dados e configurações

Arquivos brutos, dados processados e modelos gerados não devem ser versionados. Para desenvolvimento local, utilize `data/` e `models/`, ignorados pelo Git; o armazenamento remoto proposto está descrito em [infra/README.md](infra/README.md).

Credenciais devem ficar em variáveis de ambiente ou secrets do provedor. Arquivos `.env.example` podem documentar as variáveis necessárias, sem valores secretos.

## Backend e dados

Python 3.12.x, uv 0.13.2 e dependências em `uv.lock`. Instruções de configuração, PostgreSQL, execução da API e testes no [README do backend](backend/README.md).

Para instalar e verificar o código sem configurar dados da aplicação:

```bash
uv sync --locked --all-packages --extra validation
uv run --locked --all-packages --extra validation ruff check .
uv run --locked --all-packages --extra validation ruff format --check .
uv run --locked --all-packages --extra validation pytest -m 'not integration' -q
npm run build --prefix Frontend-licita-clara
```

A suíte completa usa PostgreSQL e `TEST_DATABASE_URL` em banco descartável terminado em `_test`. Siga a configuração no README do backend; testes sem integração não comprovam o acesso ao banco. Nenhum dataset ou `.env` pessoal é necessário para os testes unitários.

- [Preparação e importação de dados](docs/PREPARACAO_E_IMPORTACAO.md).
- [Índice da documentação](docs/README.md).
- [Contratos de itens/processos e testes no Swagger](docs/CONTRATOS_ITENS_PROCESSOS.md).
- [Frontend integrado: configuração e teste no navegador](docs/FRONTEND_CONSULTAS_REAIS.md).
- [Comandos de coleta e armazenamento](collector/README.md).
- [Checklist de implementação](docs/TODO_IMPLEMENTACAO_BACKEND_E_DADOS.md).
- [Contexto da arquitetura](docs/CONTEXTO_BACKEND_E_DADOS.md).
- [Contratos entre componentes](docs/CONTRATOS_BACKEND_E_DADOS.md).
- [Diagnóstico do Compras.gov.br](docs/DIAGNOSTICO_COMPRASGOV.md).

O [dicionário do banco](docs/BANCO_DE_DADOS.md) registra o esquema aplicado, snapshots e permissões dos serviços.

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

Consulte a [base e atributos analíticos](docs/ATRIBUTOS_ANALITICOS.md) para aquisição histórica registrada, preparo versionado, critérios e testes da etapa 04.

A [avaliação versionada do Isolation Forest](docs/AVALIACAO_ISOLATION_FOREST.md) consome o dataset analítico, compara regras e prepara revisão documental; utilidade ainda inconclusiva.

A [comparação Autoencoder/Isolation Forest](docs/COMPARACAO_AUTOENCODER.md) usa a mesma coorte e regras de referência, sem vencedor validado ou publicação de scores.

A [inferência/publicação versionada](docs/INFERENCIA_PUBLICACAO.md) registra treino/modelos, cobertura por resultado e canal experimental explícito; o piloto atual tem zero scores elegíveis.

O [painel, ranking e fornecedores reais](docs/PAINEL_RANKING_FORNECEDORES.md) compartilha base/execução/modelo e filtros; leia as definições de universo, valores, HHI e indisponibilidade antes de interpretar os indicadores.
