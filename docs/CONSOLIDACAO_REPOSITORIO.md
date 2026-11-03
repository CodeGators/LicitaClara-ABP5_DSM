# Consolidação do repositório — etapa 01 do plano de conclusão

Data: 03/11/2026. Branch: `chore/01-consolidar-repositorio`.

## Escopo e inventário

A base desta entrega é a `main` no commit `e2a5a84`, com o frontend da equipe integrado em 01/11/2026. O plano foi registrado em `docs/00-contexto-conclusao` e incorporado à branch de consolidação, sem alterar a `main`.

Antes da consolidação, havia 192 arquivos não rastreados, aproximadamente 2,8 MB, além de alterações em README/`.gitignore` e exclusões dos caminhos antigos. Esta entrega registra o trabalho existente; não representa implementação nova de todas as funcionalidades descritas nos documentos.

| Origem/área | Destino e tratamento |
| --- | --- |
| `licita-clara/Frontend-licita-clara/` | Movido para `Frontend-licita-clara/`, preservando o código da atualização remota e ajustando instruções do README |
| `Prototipo/` | Movido para `docs/prototipo/`, preservando os arquivos |
| Backend, collector, shared e ML locais | Código, testes e configurações registrados no Git |
| Banco | Quatro migrações e contrato de permissões registrados; nenhuma migração nova ou importação executada nesta entrega |
| Docs | Diagnósticos, evidências agregadas, diagramas, proposta e contexto registrados; exemplos antigos de CLI/paginação corrigidos |
| CI | Workflow Python existente registrado e workflow de build frontend acrescentado |
| Dados, modelos, dependências e credenciais locais | Continuam ignorados e fora dos commits |

O arquivo histórico `UML` permanece preservado na raiz. Ele não substitui o [esquema implementado](BANCO_DE_DADOS.md). O contrato de consulta atual está em [API_CONSULTAS.md](API_CONSULTAS.md).

## Instalação a partir de uma cópia limpa

Pré-requisitos: Git, Python 3.12.x, uv 0.13.2, Node.js 20.19.0/npm e Docker Compose para PostgreSQL. Um checkout do commit desta entrega contém código e lockfiles, não os dados nem `.env` desta máquina.

Na raiz da cópia:

```bash
uv sync --locked --all-packages --extra validation
uv run --locked --all-packages --extra validation ruff check .
uv run --locked --all-packages --extra validation ruff format --check .
uv run --locked --all-packages --extra validation pytest -m 'not integration' -q
npm ci --prefix Frontend-licita-clara --no-audit --no-fund
npm run build --prefix Frontend-licita-clara
```

Para PostgreSQL, seguir o [README do backend](../backend/README.md): criar `.env` a partir do exemplo **somente se ainda não existir**, iniciar banco, provisionar papéis, migrar e aplicar permissões. Não sobrescrever credenciais de volume existente. Para os testes completos, criar banco separado terminado em `_test` e configurar `TEST_DATABASE_URL` com permissão para criar/remover os schemas descartáveis usados pela suíte.

```bash
uv run --locked --all-packages --extra validation pytest -q
uv run --locked --package licita-collector licita-collector --version
uv run --locked --package licita-ml licita-ml --version
```

Verificar o resumo: testes pulados não contam como aprovação de integração. Os ensaios históricos `--offline` exigem snapshots locais ignorados e não são pré-requisito dos testes com fixtures. Para importar dados reais, seguir coleta e preparação documentadas; o clone sozinho terá banco sem esses dados.

## Evidências desta entrega

A cópia limpa foi gerada exclusivamente da árvore selecionada para o Git (`git write-tree` e `git archive`), sem copiar `.env`, datasets, modelos ou dependências da pasta original. Um ambiente virtual novo foi instalado nessa cópia. Para integração, somente `TEST_DATABASE_URL` foi fornecida ao processo; a credencial não entrou nos arquivos ou evidências.

| Verificação | Resultado |
| --- | --- |
| `uv sync --locked --all-packages --extra validation` | Instalação dos quatro pacotes do workspace aprovada |
| Ruff lint e formatação | Aprovados; 94 arquivos na checagem de formatação |
| Suíte Python com PostgreSQL `_test` | 95 testes aprovados, zero falhas/erros/skips |
| CLIs `licita-collector` e `licita-ml` | Ambas retornaram `0.1.0` |
| `npm ci` e `npm run build` | Aprovados na cópia limpa; 1.585 módulos transformados |
| Preservação de arquivos movidos | Fontes frontend e imagens idênticos aos blobs de origem; README frontend atualizado |
| Seleção para commit | Sem `.env`, datasets brutos, modelos, ambientes virtuais, `node_modules` ou `dist` |
| Checagem de credenciais | Valores locais e assinaturas comuns de segredos não encontrados na seleção; não substitui auditoria de segurança |
| Documentação | Links locais e JSONs verificados; `git diff --cached --check` aprovado |

O [resultado agregado](diagnostico/conclusao_etapa01.json) registra comandos e contagens. A árvore identificada na evidência antecede apenas a atualização documental dos resultados; código, lockfiles e workflows testados foram preservados no commit de conclusão. A suíte usa fixtures e schemas descartáveis no banco de testes já disponível; não foi criado um novo servidor PostgreSQL nesta verificação.

**Resultado: OK para a consolidação local.** As funcionalidades futuras e a integração da interface com a API não foram implementadas nesta etapa. Para revisar o conteúdo consolidado, executar `git diff --stat main...chore/01-consolidar-repositorio` e `git status --short`; o segundo deve estar vazio após o commit.

Push, execução do GitHub Actions e implantação remota não foram realizados. A atualização da `main` e a publicação da branch ficam para a integração da entrega.
