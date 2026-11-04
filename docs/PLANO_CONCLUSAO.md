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

- `main` local e remota estão sincronizadas em `de16cf2`, após integração e push autorizados das entregas técnicas 00–07. A revisão humana de 05 permanece pendente. A atualização original do frontend foi integrada pelo PR #3 em 01/11/2026. O acesso SSH da conta `rodrigoaslima` está funcionando e a permissão de escrita foi confirmada no envio de `de16cf2`; não alterar credenciais.
- A organização local difere do GitHub: frontend em `Frontend-licita-clara/` e protótipos em `docs/prototipo/`.
- No início da revisão, backend, coletor, ML, shared, infraestrutura, docs e CI estavam sem rastreamento no Git. A etapa 01 consolidou esses arquivos e a reorganização em branch própria e já foi integrada à `main` local. As branches de entrega foram preservadas.
- Backup anterior à atualização: `../abp-backup-antes-atualizacao-20261103-092407/`. Contém arquivos locais, diff e estado do Git; não é backup completo do banco/datasets ignorados.
- PostgreSQL local saudável, com duas bases validadas de setembro/2026. Cada versão tem 7 processos, 10 itens e 130 referências; não somar versões como cobertura adicional.
- Banco possui 34 tabelas de aplicação e cinco migrações documentadas. Ter tabela não significa ter serviço implementado.
- Antes de 07, tabelas de modelos, execuções de análise, scores, avaliações, revisões e relatórios estavam vazias. A etapa 07 registrou duas versões do mesmo treino separado de 140 referências, quatro versões de modelos (dois algoritmos), duas execuções/publicações experimentais e catorze avaliações de processo sem score; scores, revisões e relatórios continuam vazios. Participações e contratos também sem registros no piloto.
- API possui dezenove rotas de leitura, além de health/readiness (cinco de análise experimental e quatro de visão agregada): inclui lista/detalhe global de itens e `/fornecedores/opcoes` para o seletor. Nas consultas antigas, análise de auditoria permanece `nao_publicada`, score e prioridade nulos; o canal experimental exige consulta explícita.
- Frontend real integrado: entrada `/itens`, detalhe de item/processo, documentos, `/painel`, `/ranking`, `/fornecedores` e detalhe de fornecedor, com filtros/paginação e seleção de execução/modelo na URL. A base é fixada na URL. Essas telas não consomem os registros de `src/data.js`.
- Demonstrações preservadas em `/demonstracao/painel`, `/demonstracao/itens`, `/demonstracao/fornecedores` e `/relatorios`, com aviso explícito de dados fictícios. IDs reais não são substituídos por exemplos.
- Revisão persistente e exportações reais seguem pendentes; controles antigos continuam somente nas demonstrações. A consulta real mostra indisponibilidade dessas funções e análise não publicada.
- Isolation Forest e Autoencoder têm avaliação técnica versionada sobre o dataset analítico, com artefatos reproduzíveis e ensaios antigos preservados. Há inferência e publicação experimental de cobertura no PostgreSQL, com zero scores elegíveis no piloto; utilidade e prioridade de auditoria não foram aprovadas e revisão humana permanece pendente.
- Ensaio corretivo: 140 referências de treino e 35 de avaliação; replicação histórica: 177/107. Estabilidade aprovada nesses ensaios não comprova utilidade de auditoria.
- Há divergências documentais de especificação e limitações temporais registradas. O dossiê independente tem 18 casos, todos com parecer `pendente` na conferência atual.
- Etapa 08: 153 testes Python, 7 testes do cliente, 19 cenários browser controlados e 2 fluxos browser reais aprovados, sem skips; lint/formatação e build aprovados. Painel/ranking/fornecedores usam API, com universo explícito e índices ausentes no piloto.
- Etapa 07: 146 testes Python aprovados sem falhas/skips, lint/formatação aprovados (117 arquivos), migração 0005 e Alembic check aprovados; API real restrita e versão anterior consultável verificadas.
- Etapa 06: 143 testes Python aprovados sem skips, lint/formatação aprovados (109 arquivos), cinco treinos AE com recarga exata e comparação real/reutilização verificadas. Utilidade inconclusiva; nenhum vencedor validado.
- Etapa 05: 135 testes Python aprovados sem skips, lint/formatação aprovados (105 arquivos), grade real de 40 ajustes e recarga exata. Revisão humana pendente; utilidade inconclusiva.
- Etapa 04: 131 testes Python aprovados sem skips, lint/formatação aprovados; aquisição e preparo reais reexecutados com preservação das bases. [Política e comandos](ATRIBUTOS_ANALITICOS.md).
- Validação frontend (etapa 03): **115 testes Python**, **6 testes de cliente**, **13 testes browser com fixtures** e **1 teste browser com API/PostgreSQL reais**, todos aprovados sem skips. Lint/formatação e instalação/build frontend aprovados. Capturas desktop/mobile inspecionadas; isso não comprova fidelidade ao Figma nem o fluxo completo das etapas futuras.
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
- [Painel, ranking e fornecedores](PAINEL_RANKING_FORNECEDORES.md): rotas reais, filtros compartilhados, HHI, valores e testes de 08.
- [Inferência e publicação](INFERENCIA_PUBLICACAO.md): registro do treino/modelos, política experimental, API e testes da etapa 07.
- [Comparação com Autoencoder](COMPARACAO_AUTOENCODER.md): arquitetura, resultados, sensibilidade e decisão da etapa 06.
- [Avaliação versionada do IF](AVALIACAO_ISOLATION_FOREST.md): comandos, revisão e alternativa sem revisor independente.
- [Backend](../backend/README.md), [ML](../ml/README.md), [coletor](../collector/README.md) e [infraestrutura](../infra/README.md).

## Etapa atual e próximo passo

**Prioridade atual, definida pelo usuário:** corrigir e validar primeiro o núcleo de ML. Não iniciar 09–13, novas telas ou o botão de análise enquanto a trilha ML abaixo não tiver dados e resultados reais verificáveis. As entregas anteriores continuam preservadas; seus checkboxes representam o escopo técnico entregue, não a conclusão do objetivo analítico completo.

**Etapa 08:** código e testes concluídos na branch `feat/08-painel-ranking-fornecedores`, commit `49ec548`; ainda sem integração à `main` ou envio remoto. A consulta do usuário identificou que o seletor de execuções é pouco intuitivo. A mudança de fluxo está registrada abaixo para implementação posterior.

**Próximo trabalho:** ML-01 — diagnosticar os arquivos locais e propor recorte, vínculos e divisão temporal, antes de solicitar novos downloads ou treinar novamente. Não assumir que todos os anos ou categorias têm dados suficientes.

**Esta atualização documental:** branch `docs/replanejamento-ml`, derivada de 08 para preservar seu contexto. Exceção limitada à documentação: não integra 08 implicitamente. Antes da implementação ML-01, consolidar a base das branches conforme autorização do usuário; não fazer merge/push automático.

**Pendências externas:** acesso ao Figma; pareceres humanos independentes (usuário não tem revisor confirmado; alternativa técnica documentada sem aprovar utilidade); definição/provisionamento da hospedagem. Não impedem iniciar consolidação, contratos e consultas reais.

## Checklist geral

- [x] 00 — Criar contexto, checklist, branches e critérios de teste.
- [x] 01 — Consolidar código local, organização e documentação no Git.
- [x] 02 — Definir contratos de itens, processos, resultados e análises.
- [x] 03 — Integrar consultas reais ao frontend.
- [x] 04 — Preparar base analítica operacional e atributos reproduzíveis.
- [ ] 05 — Concluir avaliação do Isolation Forest e revisão independente.
- [x] 06 — Implementar e comparar Autoencoder (comparação técnica; utilidade inconclusiva).
- [x] 07 — Implementar inferência, explicações e publicação versionada (experimental; piloto sem scores elegíveis).
- [x] 08 — Completar painel, ranking e fornecedores integrados (canal experimental e ausências explícitas).
- [ ] 09 — Implementar autenticação, autorização e revisão persistente.
- [ ] 10 — Implementar relatórios PDF/CSV reais.
- [ ] 11 — Concluir conferência visual, responsividade e acessibilidade.
- [ ] 12 — Hospedar e automatizar operação com recuperação.
- [ ] 13 — Validar fluxo completo e preparar entrega acadêmica reproduzível.

As branches 00–08 foram criadas; as demais são planejadas. Etapas grandes podem ser divididas em tarefas com branches próprias, mantendo o ID e atualizando este plano. Não marcar todas as etapas como prontas só porque a interface compila.

## Replanejamento prioritário — ML antes das próximas funcionalidades

Decisões acordadas em 03/11/2026 após revisão da proposta original e esclarecimentos ao usuário. Esta ordem substitui a indicação anterior de iniciar 09 imediatamente após 08.

### Objetivo e lacunas reais

- A proposta original exige **score explicável por processo/licitação**. Scores por resultado de item ajudam a explicar a compra, mas não substituem esse requisito.
- Hoje IF e Autoencoder usam duas entradas: log(preço/mediana de treino) e log(1+quantidade), em um grupo restrito. Identificadores, descrições e unidades são usados na preparação e rastreabilidade, não como números contínuos no modelo.
- Existem duas execuções publicadas sobre a mesma base piloto de dez itens. Ambas verificaram elegibilidade, mas produziram zero scores: quatro itens anteriores ao corte de treino, quatro sem referência exata compatível e dois sem resultado conhecido. Reexecutar sem resolver os impedimentos não gera scores.
- Os modelos foram tecnicamente treinados e recarregados; isso não comprova utilidade para auditoria. A nova trilha deve demonstrar inferência real em dados posteriores elegíveis e concluir a análise por processo.
- Anomalia não é prova nem probabilidade de fraude. Não definir faixas, pesos ou agregações arbitrárias para preencher a interface.

### Organização dos dados acordada

**Originais preservados → Python reproduzível → base organizada → tabelas analíticas temporais → modelos → inferência e resultados rastreáveis.**

- Preservar os CSVs/ZIPs originais; não corrigir manualmente nem sobrescrever fontes, ensaios ou modelos existentes.
- Gerar cópias organizadas por scripts Python: cruzamento por chaves oficiais, tipos, versões/duplicatas, datas, unidades, situações e rejeições justificadas. Não inventar vínculos ou completar ausências com zero.
- Salvar a base organizada em Parquet e disponibilizar exportação CSV para inspeção humana. Documentar granularidade, colunas, unidades, chaves, contagens e proveniência. Arquivos gerados ficam fora do Git; versionar scripts, regras, dicionário e evidências agregadas.
- Separar organização dos registros de atributos dependentes do treino. Medianas, escalas, codificações aprendidas e outros ajustes usam somente treino; avaliação e aplicação reutilizam as transformações congeladas.
- IDs e textos permanecem associados para explicação e rastreabilidade. Somente atributos numéricos escolhidos entram nos modelos; muitos campos de origem não significam muitas entradas.
- Aproveitar leitores, normalização, experimentos, pipeline analítico e artefatos existentes. Registrar o que é reaproveitado, corrigido ou substituído, sem reconstruir tudo desnecessariamente.

### Checklist da trilha ML e critérios de aceitação

Cada item é uma tarefa com branch própria. Entregar instruções de execução/inspeção, testes proporcionais, evidências e status OK/parcial antes de avançar. Branches abaixo são planejadas.

- [ ] **ML-01 — Diagnóstico e contrato analítico** (`docs/ml-01-diagnostico-recorte`). Inventariar arquivos e cobertura temporal; medir preenchimento, chaves, versões, vínculos entre compras/itens/resultados/preços e diversidade. Definir observação de item/fornecedor e de processo, categoria(s), órgão(s), atributos iniciais e requisitos mínimos. **Aceitação:** relatório com contagens verificáveis, lacunas, recorte justificado e lista exata de downloads faltantes. Não escolher o recorte apenas para obter scores altos.
- [ ] **ML-02 — Base organizada reproduzível** (`feat/ml-02-base-organizada`). Gerar Parquet e exportação CSV inspecionável, dicionário, manifesto/hashes, contagens e rejeições. Preservar resultados de fornecedores distintos e evitar multiplicação de valores em joins. **Aceitação:** mesmas entradas geram conteúdo equivalente; preços, quantidades, unidades e vínculos reconciliados em amostra e checagens agregadas; originais intactos.
- [ ] **ML-03 — Divisão temporal e atributos** (`feat/ml-03-atributos-temporais`). Fixar treino, avaliação e aplicação com base no diagnóstico; separar compras entre conjuntos. Investigar 2023–2025 como histórico e 2026 como aplicação, sem tratar esse exemplo como disponibilidade confirmada. Possível desenho: treino 2023–2024, avaliação 2025 e eventual modelo final até dezembro/2025, preservando a avaliação e identificando o retreino como outra versão. Referências históricas por especificação/unidade; contextos de órgão/fornecedor calculados sem futuro nem a própria compra. **Aceitação:** matrizes numéricas finitas, ausências/inelegibilidade explícitas, referências e transformações restritas ao passado e proveniência até a fonte.
- [ ] **ML-04 — Treino, comparação e avaliação** (`feat/ml-04-treino-avaliacao`). Treinar IF e AE sob o mesmo protocolo; comparar com regra simples de preço relativo à mediana; medir estabilidade, convergência, sensibilidade, recursos e exemplos sinalizados. Manter a avaliação separada do ajuste de parâmetros. **Aceitação:** recarga reproduz resultados, relatório comparativo e revisão qualitativa documentada; sem rótulos não publicar acurácia de fraude. Parecer interno deve ser identificado como interno; revisão independente permanece pendência se indisponível.
- [ ] **ML-05 — Inferência real posterior** (`feat/ml-05-inferencia-real`). Aplicar modelos congelados em compras reais posteriores e compatíveis, com valores observados fora do treino. Reutilizar registro/versionamento e publicação experimental existentes, adaptando contratos se necessário. **Aceitação:** casos reais com scores, explicações/contexto, hashes e cobertura reconciliados; também casos não elegíveis com motivos. Nenhuma fabricação ou seleção apenas de casos convenientes.
- [ ] **ML-06 — Score explicável por processo** (`feat/ml-06-score-processo`). Definir atributos de processo e avaliar estratégia de modelagem/agregação com sinais por item; justificar a escolha em vez de média/máximo/pesos implícitos. Considerar quantidade de itens e cobertura parcial, modalidade, concorrência e histórico de fornecedor somente quando os dados sustentarem. **Aceitação:** resultado por licitação rastreável aos sinais e dados, limitações e cobertura explícitas, comparação de casos e ausência de score quando insuficiente; atualizar contratos, política e testes afetados antes de publicar.
- [ ] **ML-07 — Fechamento do núcleo** (`docs/ml-07-validacao-nucleo`). Registrar comandos, artefatos, recursos, exemplos reais, limitações e protocolo de reprodução; verificar fluxo fonte → base organizada → atributos → modelo salvo → inferência → resultado persistido. **Aceitação:** outra execução reproduz o resultado e o usuário consegue inspecionar os CSVs e conferir exemplos. Declarar separadamente funcionamento técnico e validação de utilidade.

Não declarar a ML concluída apenas porque treinou ou gerou um número. O objetivo inclui avaliação honesta, inferência real e score por processo. A evidência antiga continua histórica; novos testes/métricas são registrados na respectiva entrega.

### Aquisição de novos dados — participação do usuário

O usuário se dispôs a baixar arquivos do Compras.gov quando necessário. Primeiro conferir o material já existente. **Antes de depender de novos dados, avisar quais arquivos baixar, período, módulos, origem oficial e local para colocá-los**, explicando a finalidade. Não baixar grandes históricos nem executar coleta online por iniciativa desta mudança documental.

Fontes candidatas: compras, itens, resultados e pesquisa de preços; propostas para concorrência e contratos/PNCP para assinatura quando o atributo for necessário e a cobertura permitir. Um CSV isolado pode não conter todos os campos. Não exigir todos os módulos para iniciar nem prometer três anos completos sem conferir disponibilidade. Dados ausentes não impedem diagnosticar os arquivos locais.

### Fluxo de uso posterior à ML

- O fluxo esperado pelo usuário é **selecionar licitação → solicitar análise com modelo treinado → persistir → apresentar score e explicações**. Importar primeiro no banco; ML não é pré-requisito para armazenar/consultar a compra.
- O seletor atual apenas consulta execuções já publicadas; não executa ML. Preservar como histórico ou opção avançada, com rótulos claros.
- Após fechar a trilha ML, planejar tarefa própria para ação de análise na API/interface, processamento e estados de progresso/erro/inelegibilidade, autorização e reaproveitamento de resultados. Não implementar endpoint de escrita ou botão neste replanejamento.
- Depois retomar 09–13, atualizando dependências e testes com o contrato analítico final. Esta mudança não apaga entregas anteriores nem autoriza merge/push.

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

- [x] Incorporar histórico dos ensaios à aquisição/preparação operacional, com manifesto e proveniência.
- [x] Versionar comparabilidade por especificação, unidade/embalagem e condições disponíveis; tratar divergências documentadas sem alterar ensaios antigos.
- [x] Incorporar data do resultado aos cortes e registrar limites de revisões posteriores dos snapshots.
- [x] Definir fórmulas, janelas, mínimos e indisponibilidade para preço/mediana, estimado/homologado, participantes, frequência, HHI e publicação/assinatura.
- [x] Obter cobertura necessária ou registrar por que um atributo não pode ser calculado; não inventar valores para preencher telas.
- [x] Medir recursos e suficiência/diversidade antes de ampliar histórico ou limites.

**Como testar:** exemplos de preço, unidade, HHI e datas com resultados conhecidos; impedir dados futuros nas referências; reexecutar sem duplicação; conferir manifesto e rejeições. **Conclusão:** cada atributo disponível é reproduzível e cada ausência é explicada.

### 05 — Isolation Forest e utilidade

Branch: `feat/05-validacao-isolation-forest`. Dependência: 04.

- [x] Treinar pelo fluxo versionado, preservar artefato e reproduzir inferência após recarga. Consome somente grupos/linhas elegíveis; manifesto identifica dataset e IDs reais do treino, distinto do piloto operacional. Registro SQL com FK correta permanece obrigatório antes de 07.
- [ ] Revisar documentalmente amostra do treino e concluir pareceres independentes dos casos, com participação humana.
- [x] Comparar IF com regras unilateral/bilateral sem ajustar repetidamente sobre a mesma avaliação.
- [x] Registrar estabilidade, utilidade, inconclusivos e confirmação temporal conforme protocolo; insuficiência não vira aprovação.

**Como testar:** executar ensaio sobre snapshots explícitos; conferir hashes, cortes, recarga e métricas; verificar pareceres/evidências. **Conclusão:** avaliação concluída com decisão fundamentada, inclusive se negativa/inconclusiva. Publicar ranking como validado exige evidência de utilidade; demonstração experimental deve preservar seus limites.

### 06 — Autoencoder e comparação acadêmica

Branch: `feat/06-autoencoder-comparacao`. Dependências: 04 e protocolo de 05.

- [x] Definir framework e arquitetura compatíveis com os recursos e a suficiência dos dados.
- [x] Ajustar pré-processamento no treino; registrar sementes, parâmetros e dependências.
- [x] Avaliar ambos os modelos sob o mesmo protocolo e comparar também com regras simples.
- [x] Documentar decisão do ranking, limites e explicabilidade, sem média arbitrária dos scores.

**Como testar:** recarregar artefatos e reproduzir inferência; comparar cortes, estabilidade, recursos e revisão qualitativa. **Conclusão:** comparação dos dois algoritmos reproduzível e sustentada pela base disponível.

### 07 — Inferência, explicações e publicação

Branch: `feat/07-inferencia-publicacao`. Dependências: 04, 05; decisão final de comparação em 06.

- [x] Criar comandos de inferência em lote e registrar base, modelo, código, parâmetros e cobertura; registrar a base real de treino antes de associar modelos em SQL.
- [x] Persistir scores brutos, política de normalização/prioridade e comparações rastreáveis.
- [x] Calcular explicações adequadas ou retornar indisponibilidade; retirar pesos fictícios.
- [x] Publicar lote completo atomicamente, preservando execuções anteriores e impedindo mistura de bases. A comparação 06 não aprovou utilidade; distinguir demonstração experimental de prioridade validada, sem publicar automaticamente pela estabilidade.
- [x] Expor análises/execuções e definir eventual agregação item → processo.

**Como testar:** recarga, repetição, falha no meio do lote e troca de versão ativa; reconciliar score exibido com artefato e origem. **Conclusão:** análise consultável e rastreável; publicação respeita a decisão de validação.

### 08 — Painel, ranking e fornecedores

Branch: `feat/08-painel-ranking-fornecedores`. Dependências: 03 e 07.

- [x] Implementar resumos, distribuição, evolução e contadores reais, incluindo não analisados.
- [x] Implementar fornecedores, relações e concentração com universo e período explícitos.
- [x] Integrar seleção de execução/modelo e filtros de cobertura da análise, mantendo consistência entre telas; prioridade de auditoria permanece indisponível porque não há faixas validadas.
- [x] Exibir corretamente itens, processos, contratos e valores conhecidos, sem usar rótulos intercambiáveis.

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

### Entrega 04 — 03/11/2026

- Branch: `feat/04-base-atributos-analiticos`; título do commit: `feat: preparar base e atributos analiticos versionados`.
- Mudança: aquisição histórica registrada online/offline; preparação imutável com fontes explícitas, Parquet decimal, cortes por resultado, grupos estritos, exclusões documentais, fórmulas e motivos de indisponibilidade.
- Como testar: seguir [base e atributos analíticos](ATRIBUTOS_ANALITICOS.md). Repetir `atributos` deve retornar `reutilizada: true` e o mesmo fingerprint.
- Verificação: **131 testes Python aprovados, zero falhas/skips**, lint e formatação aprovados (101 arquivos); resultados em [evidência agregada](diagnostico/conclusao_etapa04.json). Testes cobrem corrupção, precisão, datas, unidades, mínimos, reexecução e cobertura desconhecida.
- Resultado real: 658 entradas, 641 normalizadas e 17 rejeitadas; um grupo tecnicamente elegível com 140 registros de treino e 35 de avaliação; 10 alvos operacionais com ausências explicadas.
- Preservação: 233 arquivos dos ensaios e `.env` inalterados; tabelas de domínio e duas bases de consulta preservadas. Apenas aquisição recebeu registros. Nenhuma migração, treinamento ou publicação de score.
- Limites: snapshots revisados após corte; comparabilidade documental e utilidade ainda não aprovadas. Pareceres humanos pendentes. Frontend inalterado; browser/build e CI remoto não reexecutados.
- Resultado: **OK para preparar e rastrear atributos**. Aprovação do modelo depende da etapa 05.
- Próximo passo: teste do usuário, integração local autorizada e etapa 05 em branch própria.

### Entrega técnica 05 — 03/11/2026

- Branch: `feat/05-validacao-isolation-forest`; título do commit: `feat: versionar avaliacao do isolation forest e revisao documental`.
- A etapa 04 foi integrada à `main` local em `3d7923c`, por autorização do usuário, preservando sua branch; não houve push.
- Mudança: `validar-if` verifica dataset/hash e política, treina duas variantes sob grade/âncora fixas, compara regras unilateral/bilateral e preserva modelos e relatório. `revisao-if` valida planilhas copiadas, preserva denominadores e não aprova utilidade automaticamente.
- Como testar: [guia da avaliação](AVALIACAO_ISOLATION_FOREST.md). Repetição deve reutilizar o fingerprint. Amostras têm 20 casos de treino e 13 de avaliação, sem scores ou procedência do método.
- Verificações: **135 testes Python aprovados sem falhas/skips**, lint e formatação aprovados (105 arquivos). Métricas reais: [evidência da etapa 05](diagnostico/conclusao_etapa05.json). Recarga reproduziu scores; testes cobrem integridade, insuficiência, política e revisão; tabela de consultas, ensaios e credenciais preservados.
- **Resultado: OK técnico / PARCIAL na revisão humana.** Nenhum parecer independente foi preenchido. Utilidade e confirmação temporal continuam inconclusivas; não há prioridade de auditoria validada nem score publicado. O checklist geral de 05 continua aberto até cumprir a revisão ou formalizar com a equipe/professor uma conclusão acadêmica limitada.
- O usuário informou não ter revisor confirmado. Alternativa: concluir comparação técnica com utilidade inconclusiva e identificar qualquer conferência própria como interna. O assistente não substitui pareceres humanos.
- Registro SQL do modelo/base de treino fica para integração da inferência: o manifesto identifica o histórico real; não foi usado o UUID do piloto como base de treino. Não houve migração ou publicação.
- Próximo passo: teste do usuário, integração autorizada da entrega técnica e etapa 06 em branch própria, com limitações preservadas.

### Entrega 06 — 03/11/2026

- Branch: `feat/06-autoencoder-comparacao`; título do commit: `feat: comparar autoencoder e isolation forest em base versionada`.
- Integração anterior: etapa técnica 05 em `0fafea5` na `main` local por autorização; branch preservada, sem push. O merge não encerrou a pendência de revisão humana.
- Mudança: Autoencoder neural 2→1→2 com sete parâmetros, mediana/padronização apenas no treino, cinco sementes, recarga exata e erro de reconstrução decomposto. Comandos `comparar-modelos` e `revisao-comparacao`, com hashes e universos explícitos.
- Como testar: [comparação acadêmica](COMPARACAO_AUTOENCODER.md), na raiz com objetos/configuração existentes. Repetir retorna `reutilizada: true`. As planilhas conjuntas mantêm 20 casos do treino e 14 da avaliação sem método/score.
- Resultado real: 140/35 referências, top-k 4; AE convergente e estável, 75% de sobreposição com IF multivariado. Sensibilidade ao preço 3× foi limitada (score aumentou em 5/12, deslocamento mediano negativo); não esconder esse resultado nem concluir superioridade.
- Verificações: **143 testes Python aprovados sem falhas/skips**, incluindo 8 focados no AE/comparação; lint/formatação aprovados (109 arquivos). Evidência: [resultado agregado da etapa 06](diagnostico/conclusao_etapa06.json). Preservados bases de consulta, modelos/ensaios anteriores, planilhas e configuração. Não houve migração, registro SQL de modelo, inferência operacional ou publicação de score. Frontend inalterado; browser/build e CI remoto não repetidos.
- **Resultado: OK para comparação técnica/experimental.** Sem vencedor validado, sem combinação arbitrária de scores e utilidade inconclusiva. Revisão humana de 05 e confirmação temporal continuam pendentes; esta conclusão não aprova ranking como prioridade de auditoria.
- Próximo passo: teste do usuário, integração autorizada e 07 em branch própria, mantendo as limitações e o vínculo correto de treino/modelo.

### Entrega 07 — 03/11/2026

- Branch: `feat/07-inferencia-publicacao`; título do commit: `feat: registrar inferencia e publicacao experimental por resultado`.
- Integração anterior: 06 em `e9223b0` na `main` local por autorização, branch preservada, sem push.
- Mudança: registro correto do dataset de treino/modelos, inferência por resultado de fornecedor, CDF do treino descritiva, parcelas AE e explicação IF indisponível, cobertura completa, falha/retomada e ativação experimental atômica. Cinco endpoints novos com base/execução explícitas.
- Banco: aplicada `0005_resultados`, mantendo 34 tabelas; FK composta resultado/item/base, unicidade por resultado e bloqueio de downgrade com análises desse tipo. Diagramas/dicionário atualizados. Base de treino é excluída das consultas operacionais.
- Como testar: [guia completo](INFERENCIA_PUBLICACAO.md). Repetir inferência/publicação deve reutilizar a execução `c680b7ea-196d-59db-93c7-03f6c7aaebb4`. Reiniciar API antiga para carregar as novas rotas e seleção de base.
- Resultado real: dez itens, vinte pares alvo/modelo, **zero scores elegíveis**, por data, comparação exata ausente ou resultado desconhecido. A execução final liga duas âncoras a um registro real de treino de 140 referências; sete processos ficam explicitamente sem agregação/score. A versão anterior de execução/modelos/treino permanece no histórico, sem contar os mesmos exemplos duas vezes. Publicação experimental consultável e duas bases operacionais preservadas.
- Verificações: **146 testes Python aprovados sem falhas/skips**, incluindo três cenários focados em inferência/publicação, lint/formatação aprovados (117 arquivos), Alembic check sem divergências. Evidência: [agregado da etapa 07](diagnostico/conclusao_etapa07.json). Testes com scores controlados cobrem múltiplos vencedores, parcelas AE, recarga, FK, falha/retomada e troca ativa atômica. Não houve mudança visual ou teste browser nesta etapa; CI remoto/deploy não executados.
- **Resultado: OK para inferência/publicação experimental; cobertura insuficiente para ranking com scores no piloto.** Não converter ausências em zero, índice em probabilidade ou estabilidade em utilidade. Revisão humana e confirmação temporal continuam pendentes; a etapa 08 deve mostrar esses limites.
- Próximo passo: teste do usuário, integração autorizada e 08 em branch própria.

### Entrega 08 — 03/11/2026

- Branch: `feat/08-painel-ranking-fornecedores`; título do commit: `feat: integrar painel ranking e fornecedores aos dados reais`.
- Estado anterior confirmado: `main` local/remota em `de16cf2`, após push autorizado por SSH. Nenhum merge/push desta etapa foi realizado.
- Mudança: quatro endpoints GET de visão agregada com universo comum; painel, ranking, fornecedores e relações reais; filtros, paginação e seleção de base/execução/modelo fixados na URL; análise selecionada no detalhe do item. Demonstrações anteriores preservadas em rotas explícitas.
- Semântica: totais decimais por resultado, múltiplos vencedores e cancelados, soma conhecida separada do total incompleto, HHI com todos os fornecedores do recorte e frequência por compra distinta. Não há prioridade de auditoria inferida; índices são experimentais e ausências não viram zero.
- Teste manual: [guia da etapa 08](PAINEL_RANKING_FORNECEDORES.md). Iniciar API/Vite e abrir `/painel`, `/ranking`, `/fornecedores`; trocar filtros/modelo/execução, abrir item/fornecedor e conferir contexto preservado.
- Verificações: **153 testes Python**, **7 testes do cliente**, **19 cenários browser controlados** e **2 fluxos browser reais** aprovados, sem skips. Lint/formatação Python (121 arquivos) e build Vite aprovados; screenshots desktop/mobile/tema escuro inspecionadas, sem alegar fidelidade ao Figma ou auditoria integral de acessibilidade.
- Resultado real: dez itens, sete compras, seis fornecedores, oito resultados não cancelados, R$ 26.579,80 homologados e zero contratos vinculados conhecidos. Dez itens não analisados no modelo escolhido; gráfico de índices indisponível. Painel/ranking/fornecedores reconciliados sob os mesmos filtros.
- Evidência: [agregado da etapa 08](diagnostico/conclusao_etapa08.json). Contagens das 34 tabelas iguais às de 07; linhas anteriores, 237 arquivos verificados e `.env` preservados. Não houve migração, coleta/importação, treinamento, inferência ou publicação. Servidor temporário de validação encerrado.
- **Resultado: OK para consultas integradas e ranking experimental com cobertura explícita.** Scores elegíveis, revisão independente/utilidade e confirmação temporal continuam pendentes; nenhuma prioridade validada foi publicada.
- Próximo passo: teste do usuário, integração autorizada e 09 em branch própria. Relatórios reais e conferência final da interface continuam em 10/11.
