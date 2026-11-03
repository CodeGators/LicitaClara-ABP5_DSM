# Licita Clara — contexto e checklist de conclusão

Atualizado em: 03/11/2026 (America/Sao_Paulo).

Este é o ponto de entrada para continuar o projeto. Ler este arquivo antes de iniciar uma entrega e atualizar o checklist, a etapa atual e as evidências ao terminá-la. O objetivo do usuário é finalizar o projeto completo, incluindo aplicação integrada e comparação acadêmica dos modelos. Não reduzir o escopo sem acordo.

## Regras de trabalho acordadas

- Uma branch por tarefa/etapa, antes de alterar seus arquivos. A expressão do usuário “para cada tabela” foi interpretada como tarefa/etapa; se ele se referir literalmente a tabelas do banco, ajustar esta regra antes da próxima entrega afetada.
- Não criar uma tabela de banco por branch de forma artificial: uma alteração de domínio pode precisar de várias tabelas e uma migração coerente.
- Ao entregar cada etapa, explicar o que mudou, como o usuário testa, o resultado dos testes e se está OK, parcial ou bloqueada, com o motivo.
- Marcar `[x]` somente depois de cumprir os critérios e registrar evidências. Código escrito não equivale a funcionalidade entregue.
- Preservar alterações locais anteriores, histórico, dados e credenciais. Não usar comandos de limpeza ou restauração que descartem trabalho.
- Antes de trocar de etapa, conferir arquivos modificados e isolar o trabalho da branch. Não usar `git add .` neste estado do repositório.
- Partir da `main` atualizada e consolidada para cada nova branch. Integrar dependências concluídas antes de iniciar etapas que dependam delas; não misturar tarefas independentes na mesma branch.
- Não fazer push, merge na `main` ou implantação como consequência de apenas terminar uma etapa: apresentar a entrega e seguir a autorização vigente do usuário para essas ações.
- Não versionar `.env`, credenciais, dados brutos volumosos ou modelos gerados. Manter `.env.example` sem segredos.
- Preservar `Frontend-licita-clara/` e a organização local. Não substituir o frontend atualizado por uma versão antiga do protótipo.
- Mudanças visuais devem seguir o Figma quando acessível e reutilizar componentes e estilos existentes.
- Não apresentar anomalia como fraude, estabilidade como acurácia, ausência como zero ou indicador descritivo como contribuição calculada do modelo.
- Revisão documental assistida não substitui parecer humano independente.

## Estado confirmado em 03/11/2026

- `main` local está em `e1945f2`, após merges autorizados das etapas 01 e 02. A atualização original do frontend foi integrada pelo PR #3 em 01/11/2026. O envio ao GitHub continua pendente por permissão de escrita; a última referência remota consultada estava em `e2a5a84`.
- A organização local difere do GitHub: frontend em `Frontend-licita-clara/` e protótipos em `docs/prototipo/`.
- No início da revisão, backend, coletor, ML, shared, infraestrutura, docs e CI estavam sem rastreamento no Git. A etapa 01 consolidou esses arquivos e a reorganização em branch própria e já foi integrada à `main` local. As branches de entrega foram preservadas.
- Backup anterior à atualização: `../abp-backup-antes-atualizacao-20261103-092407/`. Contém arquivos locais, diff e estado do Git; não é backup completo do banco/datasets ignorados.
- PostgreSQL local saudável, com duas bases validadas de setembro/2026. Cada versão tem 7 processos, 10 itens e 130 referências; não somar versões como cobertura adicional.
- Banco possui 34 tabelas de aplicação e quatro migrações documentadas. Ter tabela não significa ter serviço implementado.
- Tabelas de modelos, execuções de análise, scores, avaliações, revisões e relatórios estavam vazias. Participações e contratos também sem registros no piloto.
- API possui dez rotas de consulta, além de health/readiness: inclui lista/detalhe global de itens e `/fornecedores/opcoes` para o seletor. Análise permanece `nao_publicada`, score e prioridade nulos.
- Frontend real integrado: entrada `/itens`, detalhe de item/processo, documentos, filtros e paginação HTTP. A base é fixada na URL. Essas telas não consomem os registros de `src/data.js`.
- Demonstrações preservadas em `/demonstracao/painel`, `/demonstracao/itens`, `/fornecedores` e `/relatorios`, com aviso explícito de dados fictícios. IDs reais não são substituídos por exemplos.
- Revisão persistente e exportações reais seguem pendentes; controles antigos continuam somente nas demonstrações. A consulta real mostra indisponibilidade dessas funções e análise não publicada.
- Isolation Forest tem ensaios separados do fluxo operacional, com artefatos reproduzíveis; não há inferência publicada no PostgreSQL. Autoencoder não implementado.
- Ensaio corretivo: 140 referências de treino e 35 de avaliação; replicação histórica: 177/107. Estabilidade aprovada nesses ensaios não comprova utilidade de auditoria.
- Há divergências documentais de especificação e limitações temporais registradas. O dossiê independente tem 18 casos, todos com parecer `pendente` na conferência atual.
- Validação mais recente (etapa 03): **115 testes Python**, **6 testes de cliente**, **13 testes browser com fixtures** e **1 teste browser com API/PostgreSQL reais**, todos aprovados sem skips. Lint/formatação e instalação/build frontend aprovados. Capturas desktop/mobile inspecionadas; isso não comprova fidelidade ao Figma nem o fluxo completo das etapas futuras.
- Ainda não há implantação remota confirmada.

## Figma e referências

- Design fornecido: https://www.figma.com/design/IEjeSPsQpD7SzUy15MWp0C/5DSM---2026?node-id=18-10229
- File key: `IEjeSPsQpD7SzUy15MWp0C`; node: `18:10229`.
- Acesso testado em 03/11/2026 pelo plugin Figma: criação de sessão e screenshot recusados com mensagem de falta de acesso de edição. O conteúdo do arquivo **não foi inspecionado**.
- O perfil pessoal do Chrome não determina a identidade do plugin. Resolver acesso pela conta conectada/permissão do arquivo; não pedir senha ou token no chat.
- Enquanto pendente, usar o frontend existente e os materiais em `docs/prototipo/` como referências locais, sem afirmar fidelidade ao Figma.
- Ao obter acesso, consultar contexto e screenshot do design usando a skill de Figma apropriada e registrar quais telas foram comparadas.

Documentos de apoio:

- [Contexto técnico](CONTEXTO_BACKEND_E_DADOS.md).
- [Checklist técnico anterior](TODO_IMPLEMENTACAO_BACKEND_E_DADOS.md): preserva histórico, mas tem instruções antigas; este plano organiza a conclusão atual.
- [Contrato implementado da API](API_CONSULTAS.md): prevalece sobre exemplos antigos propostos no contexto.
- [Contratos de itens/processos](CONTRATOS_ITENS_PROCESSOS.md): decisão da etapa 02, navegação, valores e testes manuais.
- [Frontend integrado](FRONTEND_CONSULTAS_REAIS.md): execução com proxy Vite, caminhos reais/demonstrativos e testes no navegador.
- [Banco](BANCO_DE_DADOS.md) e [importação](PREPARACAO_E_IMPORTACAO.md).
- [Revisão do núcleo](validacao_nucleo/REVISAO_E_CONFIRMACAO.md), [achados](validacao_nucleo/ACHADOS_DOCUMENTAIS.md) e [guia independente](validacao_nucleo/GUIA_REVISAO_INDEPENDENTE.md).
- [Backend](../backend/README.md), [ML](../ml/README.md), [coletor](../collector/README.md) e [infraestrutura](../infra/README.md).

## Etapa atual e próximo passo

**Etapa atual:** 03 — consultas reais integradas e verificadas, branch `feat/03-frontend-consultas-reais`; pronta para revisão.

**Próxima etapa:** 04 — base operacional e atributos analíticos, após integração autorizada da etapa 03. Não houve merge desta etapa na `main` nem envio ao GitHub; a permissão remota não impede desenvolvimento local.

**Pendências externas:** acesso ao Figma; pareceres humanos independentes; definição/provisionamento da hospedagem. Não impedem iniciar consolidação, contratos e consultas reais.

## Checklist geral

- [x] 00 — Criar contexto, checklist, branches e critérios de teste.
- [x] 01 — Consolidar código local, organização e documentação no Git.
- [x] 02 — Definir contratos de itens, processos, resultados e análises.
- [x] 03 — Integrar consultas reais ao frontend.
- [ ] 04 — Preparar base analítica operacional e atributos reproduzíveis.
- [ ] 05 — Concluir avaliação do Isolation Forest e revisão independente.
- [ ] 06 — Implementar e comparar Autoencoder.
- [ ] 07 — Implementar inferência, explicações e publicação versionada.
- [ ] 08 — Completar painel, ranking e fornecedores integrados.
- [ ] 09 — Implementar autenticação, autorização e revisão persistente.
- [ ] 10 — Implementar relatórios PDF/CSV reais.
- [ ] 11 — Concluir conferência visual, responsividade e acessibilidade.
- [ ] 12 — Hospedar e automatizar operação com recuperação.
- [ ] 13 — Validar fluxo completo e preparar entrega acadêmica reproduzível.

As branches 00–03 foram criadas; as demais são planejadas. Etapas grandes podem ser divididas em tarefas com branches próprias, mantendo o ID e atualizando este plano. Não marcar todas as etapas como prontas só porque a interface compila.

## Entregas, branches e aceitação

### 00 — Contexto de conclusão

Branch: `docs/00-contexto-conclusao`.

- [x] Registrar estado real, restrições, referências e ordem de execução.
- [x] Definir checklist e uma branch planejada por etapa.
- [x] Definir procedimento e evidências de teste por entrega.
- [x] Testar acesso ao Figma e registrar resultado sem presumir acesso.

**Como testar:** abrir este arquivo, conferir links locais, conferir a branch atual e verificar se todas as etapas têm critério e teste. **Conclusão:** plano verificável, sem declarar funcionalidades futuras concluídas.

### 01 — Consolidar repositório

Branch: `chore/01-consolidar-repositorio`. Dependência: 00.

- [x] Inventariar alterações anteriores e registrar a reorganização como tal, sem perder arquivos.
- [x] Versionar código, migrações, documentação, lockfiles e CI pertinentes; excluir segredos e artefatos ignorados.
- [x] Conciliar README, comandos, fonte Compras.gov.br/PNCP e estado real das entregas.
- [x] Preparar integração dessa base para que as próximas branches tenham todos os componentes.

**Como testar:** revisar diff e arquivos rastreados; instalar pelos lockfiles; executar CI Python e build frontend. **Conclusão:** checkout limpo da entrega reproduz o código e a estrutura, sem credenciais/dados privados incluídos. A execução remota do CI deve ser registrada separadamente da local.

### 02 — Contratos e unidade de análise

Branch: `feat/02-contratos-itens-processos`. Dependência: 01.

- [x] Decidir e documentar listagem por item, processo ou resultado; fila por item com contexto do processo e resultados por fornecedor preservados.
- [x] Definir IDs estáveis, snapshots, múltiplos vencedores, seleção de base/execução e navegação; seleção de execução continua explicitamente planejada para 07.
- [x] Definir valores globais versus recorte, dinheiro decimal, nulos, estados de análise e erros.
- [x] Documentar endpoints e compatibilidade com a API existente, sem quebrar silenciosamente consumidores.

**Como testar:** exemplos com vários itens/fornecedores e bases; validar OpenAPI e contratos; conferir que totais não se multiplicam. **Conclusão:** a mesma entidade é identificada e interpretada corretamente na API, interface e modelo.

### 03 — Frontend com consultas reais

Branch: `feat/03-frontend-consultas-reais`. Dependência: 02.

- [x] Criar cliente HTTP configurável e integrar lista, detalhe, itens, documentos e dados de apoio.
- [x] Implementar filtros, busca, ordenação e paginação reais, mantendo a base selecionada.
- [x] Tratar carregamento, erro, vazio, ID inexistente, nulos e análise indisponível.
- [x] Remover mocks das telas migradas; demonstrações preservadas em rotas separadas e identificadas explicitamente.

**Como testar:** navegar com API e PostgreSQL locais; comparar resultados ao Swagger; trocar páginas/filtros; abrir ID inexistente; simular API indisponível. **Conclusão:** consultas funcionam sem `data.js` e sem scores fabricados. Painel analítico e ranking final continuam em 08.

### 04 — Base e atributos analíticos

Branch: `feat/04-base-atributos-analiticos`. Dependência: 02.

- [ ] Incorporar histórico dos ensaios à aquisição/preparação operacional, com manifesto e proveniência.
- [ ] Versionar comparabilidade por especificação, unidade/embalagem e condições disponíveis; tratar divergências documentadas sem alterar ensaios antigos.
- [ ] Incorporar data do resultado aos cortes e registrar limites de revisões posteriores dos snapshots.
- [ ] Definir fórmulas, janelas, mínimos e indisponibilidade para preço/mediana, estimado/homologado, participantes, frequência, HHI e publicação/assinatura.
- [ ] Obter cobertura necessária ou registrar por que um atributo não pode ser calculado; não inventar valores para preencher telas.
- [ ] Medir recursos e suficiência/diversidade antes de ampliar histórico ou limites.

**Como testar:** exemplos de preço, unidade, HHI e datas com resultados conhecidos; impedir dados futuros nas referências; reexecutar sem duplicação; conferir manifesto e rejeições. **Conclusão:** cada atributo disponível é reproduzível e cada ausência é explicada.

### 05 — Isolation Forest e utilidade

Branch: `feat/05-validacao-isolation-forest`. Dependência: 04.

- [ ] Treinar pelo fluxo versionado, preservar artefato e reproduzir inferência após recarga.
- [ ] Revisar documentalmente amostra do treino e concluir pareceres independentes dos casos, com participação humana.
- [ ] Comparar IF com regras unilateral/bilateral sem ajustar repetidamente sobre a mesma avaliação.
- [ ] Registrar estabilidade, utilidade, inconclusivos e confirmação temporal conforme protocolo; insuficiência não vira aprovação.

**Como testar:** executar ensaio sobre snapshots explícitos; conferir hashes, cortes, recarga e métricas; verificar pareceres/evidências. **Conclusão:** avaliação concluída com decisão fundamentada, inclusive se negativa/inconclusiva. Publicar ranking como validado exige evidência de utilidade; demonstração experimental deve preservar seus limites.

### 06 — Autoencoder e comparação acadêmica

Branch: `feat/06-autoencoder-comparacao`. Dependências: 04 e protocolo de 05.

- [ ] Definir framework e arquitetura compatíveis com os recursos e a suficiência dos dados.
- [ ] Ajustar pré-processamento no treino; registrar sementes, parâmetros e dependências.
- [ ] Avaliar ambos os modelos sob o mesmo protocolo e comparar também com regras simples.
- [ ] Documentar decisão do ranking, limites e explicabilidade, sem média arbitrária dos scores.

**Como testar:** recarregar artefatos e reproduzir inferência; comparar cortes, estabilidade, recursos e revisão qualitativa. **Conclusão:** comparação dos dois algoritmos reproduzível e sustentada pela base disponível.

### 07 — Inferência, explicações e publicação

Branch: `feat/07-inferencia-publicacao`. Dependências: 04, 05; decisão final de comparação em 06.

- [ ] Criar comandos de inferência em lote e registrar base, modelo, código, parâmetros e cobertura.
- [ ] Persistir scores brutos, política de normalização/prioridade e comparações rastreáveis.
- [ ] Calcular explicações adequadas ou retornar indisponibilidade; retirar pesos fictícios.
- [ ] Publicar lote completo atomicamente, preservando execuções anteriores e impedindo mistura de bases.
- [ ] Expor análises/execuções e definir eventual agregação item → processo.

**Como testar:** recarga, repetição, falha no meio do lote e troca de versão ativa; reconciliar score exibido com artefato e origem. **Conclusão:** análise consultável e rastreável; publicação respeita a decisão de validação.

### 08 — Painel, ranking e fornecedores

Branch: `feat/08-painel-ranking-fornecedores`. Dependências: 03 e 07.

- [ ] Implementar resumos, distribuição, evolução e contadores reais, incluindo não analisados.
- [ ] Implementar fornecedores, relações e concentração com universo e período explícitos.
- [ ] Integrar filtros por análise/prioridade e manter consistência entre telas.
- [ ] Exibir corretamente itens, processos, contratos e valores conhecidos, sem usar rótulos intercambiáveis.

**Como testar:** reconciliar gráficos/cards/listas sob os mesmos filtros e base; conferir denominadores do HHI; testar ausência de análise e múltiplos fornecedores. **Conclusão:** nenhum indicador funcional depende de constantes simuladas.

### 09 — Identidade e revisão humana

Branch: `feat/09-autenticacao-revisoes`. Dependências: 02, 03 e 07.

- [ ] Escolher identidade, papéis e quais leituras são públicas.
- [ ] Validar usuário no servidor e autorizar operações de escrita.
- [ ] Persistir histórico, observação, conclusão, autor e análise consultada.
- [ ] Tratar concorrência e nova análise sem sobrescrever parecer anterior.

**Como testar:** acesso anônimo, permissão insuficiente, autor correto e concorrência; atualizar navegador e confirmar histórico. **Conclusão:** revisão persistente e auditável, independente do score.

### 10 — Relatórios PDF/CSV

Branch: `feat/10-relatorios-pdf-csv`. Dependências: 08 e 09.

- [ ] Implementar prévia e geração real com o mesmo serviço de dados.
- [ ] Persistir solicitação, autor, seleção, base/análise e snapshot suficiente para reprodução.
- [ ] Implementar worker persistente, estados, retomada, retentativas e download autorizado.
- [ ] Incluir fontes, método, limitações, revisão e formatos corretos; CSV deve tratar escape e fórmulas.

**Como testar:** baixar/abrir PDF e CSV, comparar à prévia, negar acesso indevido, reiniciar worker e trocar análise ativa sem alterar relatório emitido. **Conclusão:** arquivos reais, consistentes e recuperáveis.

### 11 — Conferência da interface

Branch: `fix/11-interface-acessibilidade`. Dependências: 03, 08, 09 e 10; conferir Figma quando acessível.

- [ ] Resolver acesso ao Figma e registrar telas efetivamente inspecionadas.
- [ ] Conferir as cinco telas, ativos visuais, temas e responsividade.
- [ ] Testar teclado, foco, rótulos, contraste e estados vazio/erro/carregando.
- [ ] Remover controles que aparentem funcionar sem ação implementada e textos antigos sobre fontes/mocks.

**Como testar:** comparação visual e navegação real em desktop e celular, nos dois temas, incluindo teclado. **Conclusão:** fidelidade conferida e fluxos utilizáveis; build sozinho não aprova esta etapa.

### 12 — Hospedagem, automação e recuperação

Branch: `chore/12-deploy-operacao`. Dependências: serviços funcionais e cobertura dimensionada.

- [ ] Definir provedores, custos/limites vigentes e execução efetiva do worker antes de provisionar.
- [ ] Criar empacotamento reproduzível, configurações, migrações controladas e armazenamento persistente.
- [ ] Publicar frontend/API/dados com configuração de identidade, CORS e TLS apropriada.
- [ ] Completar CI com build frontend e verificações relevantes; automatizar coleta/processamento com locks e estados observáveis.
- [ ] Testar backup/restauração, reinício, retenção e rollback; não publicar modelos automaticamente sem avaliação.

**Como testar:** fluxo pela URL hospedada, reinício dos serviços, indisponibilidade, restauração e execução manual da automação antes do agendamento. **Conclusão:** aplicação acessível e persistente, sem depender do disco efêmero ou da máquina do desenvolvedor.

### 13 — Aceitação e entrega acadêmica

Branch: `docs/13-entrega-validacao-final`. Dependências: 01–12.

- [ ] Executar coleta → preparação → análise → publicação → consulta → revisão → relatório.
- [ ] Rastrear um resultado até o arquivo oficial e o modelo; reconciliar telas e exportações.
- [ ] Reproduzir instalação em ambiente limpo e executar testes de integração e navegação.
- [ ] Consolidar avaliação IF/Autoencoder/regras, metodologia, fontes, limitações e resultados reais.
- [ ] Atualizar documentação, evidências e roteiro de apresentação; resolver falhas encontradas.

**Como testar:** outra pessoa segue o README e o roteiro sem explicações adicionais; conferir evidências e checklist. **Conclusão:** aplicação completa demonstrável e avaliação acadêmica reproduzível, com limitações explícitas.

## Comandos existentes para verificação

Executar na raiz. Não copiar `.env.example` sobre o `.env` existente. Não recriar bancos/volumes para apenas testar.

```bash
git status --short
git branch --show-current
uv run --locked --all-packages --extra validation ruff check .
uv run --locked --all-packages --extra validation ruff format --check .
uv run --locked --all-packages --extra validation pytest -q
npm ci --prefix Frontend-licita-clara --no-audit --no-fund
npm run build --prefix Frontend-licita-clara
docker compose --env-file .env -f infra/compose.yaml ps
```

Testes PostgreSQL exigem `TEST_DATABASE_URL` apontando para banco descartável terminado em `_test`; sem configuração, podem ser pulados. Registrar skips, nunca declarar integração aprovada quando não executou. Esses comandos são verificações gerais; executar verificações proporcionais à mudança, sem repetir a suíte inteira para uma simples correção de texto.

Para consulta manual, com banco/configuração existentes:

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Em outro terminal:

```bash
npm run dev --prefix Frontend-licita-clara
```

Swagger: http://127.0.0.1:8000/docs. Usar a URL emitida pelo Vite para a interface. Endpoints das etapas futuras só devem entrar nas instruções de teste após implementação.

## Registro obrigatório de cada entrega

Copiar e preencher ao concluir uma tarefa:

```text
Etapa / tarefa:
Branch / commit:
Data:
O que mudou:
Pré-requisitos para testar:
Passos e resultados esperados:
Verificações executadas e resultados (incluindo skips):
O que não foi verificado:
Resultado: OK / PARCIAL / BLOQUEADO, com motivo
Pendências e próxima etapa:
Checklist atualizado:
```

### Entrega 00 — 03/11/2026

- Branch: `docs/00-contexto-conclusao`.
- Mudança: criado este contexto com checklist, critérios, branches e testes planejados.
- Verificação: links Markdown relativos e estrutura das 14 etapas conferidos localmente; Figma recusou acesso nas duas tentativas.
- Resultado: **OK para a documentação do plano**. Acesso ao Figma permanece pendente; nenhuma funcionalidade futura foi marcada como concluída.
- Próximo passo: etapa 01. As alterações anteriores continuam locais e precisam de consolidação própria.

### Entrega 01 — 03/11/2026

- Branch: `chore/01-consolidar-repositorio`; commit de conclusão identificado no histórico pelo título `chore: consolidar monorepositorio e validar instalacao limpa`.
- Mudança: registrado o código local, migrações, testes, docs e lockfiles; reconhecidas as movimentações de frontend/protótipos; corrigidos exemplos antigos de CLI/paginação e acrescentado CI de build frontend.
- Pré-requisitos/passos: seguir [consolidação do repositório](CONSOLIDACAO_REPOSITORIO.md), incluindo ambiente PostgreSQL `_test` para integração.
- Verificações: instalação em cópia limpa com ambiente virtual novo, 95 testes aprovados sem skips, lint e formatação aprovados (94 arquivos), instalação/build frontend aprovados e versões de ambas as CLIs `0.1.0`.
- Preservação: fontes frontend e imagens movidas comparadas byte a byte; dados, modelos, dependências e `.env` fora do índice; valores de credenciais locais e assinaturas comuns de segredos não encontrados na seleção. Essa checagem não é uma auditoria de segurança completa.
- Evidência: [resultado agregado da etapa 01](diagnostico/conclusao_etapa01.json).
- Não verificado: execução remota do CI, implantação e fluxos de negócio das etapas futuras. Testes de integração usaram schemas descartáveis do banco de testes existente; não foi necessário migrar ou importar na base da aplicação.
- Resultado: **OK para a consolidação local**; integração na `main` e publicação remota ainda pendentes.
- Próxima etapa: 02, após integração autorizada da base consolidada.

### Entrega 02 — 03/11/2026

- Branch: `feat/02-contratos-itens-processos`; título do commit: `feat: definir contratos e consultas de itens com contexto do processo`.
- Mudança: contratos de granularidade, IDs, valores e navegação documentados; implementados `GET /api/v1/itens` e `GET /api/v1/itens/{item_id}`, preservando as consultas anteriores. Resultados múltiplos e cancelados permanecem explícitos; total incompleto fica nulo.
- Pré-requisitos/passos: [contratos e teste manual no Swagger](CONTRATOS_ITENS_PROCESSOS.md). Suíte completa usa PostgreSQL `_test` conforme README do backend.
- Verificações: 113 testes aprovados, zero skips, lint e formatação aprovados; OpenAPI comparado à `main` com nove rotas e 23 schemas anteriores idênticos. HTTP TCP local com a identidade restrita conferiu os dez itens reais, contexto do processo, compatibilidade, erros 404/422 e preservação dos dados/configuração.
- Evidência: [resultado da etapa 02](diagnostico/conclusao_etapa02.json).
- Não verificado/fora do escopo: integração de telas, browser, publicação de scores e CI remoto. Nenhuma migração ou importação executada, nenhum score fabricado. Servidor temporário de validação encerrado.
- Resultado: **OK para contratos e consultas de itens**. As telas ainda consomem mocks até a etapa 03.
- Próxima etapa: integrar esta entrega localmente mediante autorização e iniciar 03 em branch própria. O acesso de escrita remoto continua pendente.

### Entrega 03 — 03/11/2026

- Branch: `feat/03-frontend-consultas-reais`; título do commit: `feat: integrar consultas reais de itens processos e documentos no frontend`.
- Mudança: entrada real `/itens`, cliente HTTP configurável, seleção da base na URL, filtros, paginação, detalhe do item e processo, documentos oficiais, nulos e estados de falha/ausência. Acrescentada consulta paginada de opções de fornecedores; demonstrações permanecem identificadas e separadas.
- Pré-requisitos/passos: [execução e testes do frontend](FRONTEND_CONSULTAS_REAIS.md). API local na porta 8000 e Vite normalmente em 5173; configuração por proxy, sem credenciais de banco no navegador.
- Verificações: 115 testes Python, 6 testes do cliente, 13 cenários browser controlados e 1 fluxo browser real aprovados, sem skips. `npm ci`, build Vite, lint e formatação aprovados. Navegação real via proxy Vite/API/PostgreSQL com Chrome headless; screenshots desktop/mobile inspecionadas.
- Cobertura de teste: filtros enviados como strings, base fixa mesmo após mudança da mais recente, cancelamento de respostas antigas, IDs inválidos/inexistentes, vazio/sem base, indisponibilidade/retentativa, documentos, nulos e separação das demonstrações.
- Evidência: [resultado da etapa 03](diagnostico/conclusao_etapa03.json).
- Não verificado/fora do escopo: CI remoto, produção, fidelidade ao Figma, demais navegadores, revisão completa de acessibilidade e funcionalidades analíticas/de escrita futuras. Não houve migração/importação ou publicação de score. Dados/configuração preservados; servidores temporários de validação encerrados.
- Resultado: **OK para consultas reais no frontend**. A validação acadêmica do modelo e os indicadores finais ainda dependem das etapas 04–08.
- Próxima etapa: 04, após integração local autorizada desta entrega.
