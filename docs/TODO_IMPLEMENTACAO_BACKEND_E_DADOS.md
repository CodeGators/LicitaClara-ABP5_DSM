# Licita Clara — checklist de implementação de backend e dados

Referência: [CONTEXTO_BACKEND_E_DADOS.md](CONTEXTO_BACKEND_E_DADOS.md).
Criado em 19/10/2026. Escopo: API, PostgreSQL, coleta, processamento, modelos, relatórios e infraestrutura. Não inclui alterações no frontend.

Para a conclusão integrada, incluindo frontend e branches por entrega, seguir [PLANO_CONCLUSAO.md](PLANO_CONCLUSAO.md). A numeração deste checklist técnico é histórica e difere da numeração do plano atual. Notas de progresso preservam o estado da data indicada.

## Como usar

Executar as etapas na ordem indicada e marcar `[x]` somente após verificar a entrega. Ao concluir cada etapa, registrar evidências, responsável, data e decisões no acompanhamento da equipe. Os itens abaixo representam trabalho futuro; a existência desta lista não significa que os serviços estejam implementados.

Começar com um mês real e ampliar a base gradualmente. Quando um campo não existir na fonte, documentar a ausência e adaptar a solução, sem fabricar resultados. Preservar o nome `Frontend-licita-clara`.

## Validação antecipada do núcleo — 20/10/2026

A pedido da equipe, foi antecipado um ensaio dos itens 07/08 antes de expandir a API. [Protocolo](validacao_nucleo/PROTOCOLO.md), [resultado e próximos critérios](validacao_nucleo/RESULTADO.md) e [evidência agregada](validacao_nucleo/resultado_agregado.json).

- [x] Adquirir histórico real de outubro/2025 a setembro/2026 e registrar snapshots/hashes.
- [x] Verificar suficiência por grupo estrito, sem misturar unidades e especificações.
- [x] Preservar o resultado insuficiente do CATMAT 486054 e escolher alternativa por disponibilidade previamente registrada.
- [x] Treinar IF com preço e quantidade e ablação só de preço; comparar com duas regras simples.
- [x] Avaliar temporalmente, testar estabilidade, registrar parâmetros e reproduzir scores de artefatos carregados.
- [x] Preparar amostra de revisão sem scores: 18 casos principais e dez exploratórios.
- [ ] Concluir revisão documental humana e medir utilidade frente às regras simples.
- [ ] Confirmar generalização em outra janela ainda não usada e fechar a política de publicação.

**Verificação local:** 61 testes aprovados, sem skips, lint e formatação; hashes dos artefatos e planilhas conferidos. CI atualizado, sem execução remota.

**Decisão:** viável tecnicamente, utilidade pendente. O grupo principal de marca-texto (CATMAT 486374) tem 142 referências de treino e 41 de teste. O piloto de borracha permanece exploratório (43/10). Não interpretar estabilidade como acurácia. Os checklists de produção das etapas 07/08 continuam abertos: este ensaio não implementa todos os atributos, integração operacional, score 0–100 ou publicação de análises. As notas datadas abaixo preservam o estado das entregas anteriores.

### Revisão aprofundada — 20/10/2026

[Resultado da revisão e confirmação](validacao_nucleo/REVISAO_E_CONFIRMACAO.md), [achados documentais](validacao_nucleo/ACHADOS_DOCUMENTAIS.md) e [evidência agregada](validacao_nucleo/revisao_e_confirmacao_agregado.json).

- [x] Corroborar identidade, preço, quantidade e unidade dos 18 casos (17 compras): 15 via Compras.gov.br e três resultados diretamente no PNCP.
- [x] Consultar anexos e registrar limites: dez documentos com texto, cobrindo nove casos; 13 falhas de acesso/transferência registradas.
- [x] Documentar duas divergências de especificação e recomendar suspensão da comparação até esclarecimento; corroboração de valores não significa produtos equivalentes.
- [x] Executar ensaio corretivo por data de resultado: 140 referências de treino e 35 de avaliação, com estabilidade aprovada.
- [x] Repetir o ensaio técnico em histórico disjunto 2024/2025: 177 de treino e 107 de avaliação, com estabilidade aprovada.
- [x] Consultar outubro/2026 sem mudar critérios; confirmação futura inconclusiva por insuficiência de referências no grupo estrito.
- [x] Preparar dossiê independente com URLs e páginas, sem scores nem indicação de método; pareceres humanos continuam pendentes.
- [ ] Versionar no fluxo operacional os controles de data de resultado e de especificação documental, incluindo amostra do treino.
- [ ] Concluir revisão independente e comparar utilidade frente à regra simples; não transformar cobertura de dados em acurácia.
- [ ] Obter confirmação operacional posterior com amostra suficiente antes de aprovar publicação do ranking.

**Verificação da revisão:** 71 testes aprovados, sem skips, lint e formatação; hashes das fontes, PDFs citados e oito artefatos conferidos. Planilha original preservada.

**Prioridade atual do núcleo:** corrigir comparabilidade e concluir validação de utilidade; o IF ainda não foi aprovado para publicação de risco de auditoria. A etapa 06 pode ser implementada independentemente, sem publicar scores. Não marcar etapas 07/08 como concluídas por causa da estabilidade dos ensaios.

## 01 — Diagnosticar a fonte de dados

Dependência: nenhuma. Esta etapa determina o esquema definitivo e o recorte viável.

- [x] Consultar a página oficial de downloads e os dicionários de dados.
- [x] Identificar uma competência disponível e registrar a cobertura da fonte.
- [x] Baixar um mês para diretório local ignorado pelo Git.
- [x] Registrar URL, data, tamanho e SHA-256 dos arquivos.
- [x] Identificar formato, codificação, delimitador, cabeçalhos e tipos.
- [x] Levantar chaves de processos, órgãos, fornecedores, itens e participantes.
- [x] Verificar como resultados, contratos e documentos podem ser relacionados; identificar fontes complementares se necessário.
- [x] Conferir datas, quantidades, unidades, preços unitários e valores totais.
- [x] Medir nulos, duplicatas, inconsistências e cobertura dos atributos propostos.
- [x] Medir tamanho do ZIP, arquivos extraídos e uma amostra convertida em Parquet.
- [x] Documentar cada atributo como disponível, derivável ou indisponível.
- [x] Escolher categoria inicial e período histórico pretendido, condicionado ao volume observado.
- [x] Salvar diagnóstico e mapeamento de campos em `docs/`.

**Concluído quando:** a equipe consegue explicar de onde vem cada informação do MVP, quais chaves a relacionam e quais limitações existem.

**Progresso em 19/10/2026:** 13 de 13 tarefas de diagnóstico inicial verificadas por Codex. O [diagnóstico do Portal da Transparência](DIAGNOSTICO_FONTE_LICITACOES.md) mostrou a limitação do pacote histórico. O [diagnóstico complementar do Compras.gov.br](DIAGNOSTICO_COMPRASGOV.md) validou quatro ZIPs mensais de setembro de 2026, campos reais, catálogo CATMAT e vínculos via API. Piloto escolhido: artigos para escritório, começando pelo CATMAT 486054; histórico pretendido de outubro de 2025 a setembro de 2026. Dados brutos em `data/` ignorado pelo Git; perfis agregados em `docs/diagnostico/`. O diagnóstico inicial está concluído; regras de deduplicação, unidades, cobertura de participantes/contratos e expansão do histórico continuam como trabalho de implementação e validação. Não há modelo treinado.

## 02 — Preparar o ambiente e os contratos entre componentes

Dependência: 01 para decisões de esquema; a configuração Python pode começar antes.

- [x] Escolher versão Python compatível com as bibliotecas e documentá-la.
- [x] Criar pacotes e `pyproject.toml` de backend, coletor e modelagem.
- [x] Fixar dependências de forma reproduzível e definir comandos de execução.
- [x] Criar estrutura FastAPI: rotas, schemas, serviços, repositórios, modelos, configuração e sessões.
- [x] Criar configuração por variáveis de ambiente com validação na inicialização.
- [x] Adicionar `.env.example` sem credenciais reais.
- [x] Criar `infra/compose.yaml` com PostgreSQL local, volume persistente e healthcheck.
- [x] Definir acesso local a arquivos e interface de armazenamento substituível por S3/R2.
- [x] Definir responsável único pelas migrações e contrato de importação/publicação usado por coletor e ML.
- [x] Implementar `/api/v1/health` e `/api/v1/ready`, distinguindo processo ativo de banco disponível.
- [x] Definir transações, fechamento das sessões e tratamento de falhas de conexão.
- [x] Criar logs estruturados com IDs de requisição e definir contrato para IDs das futuras execuções.
- [x] Configurar CI inicial para as verificações relevantes dos componentes Python.
- [x] Documentar como iniciar tudo em uma máquina nova.

**Concluído quando:** PostgreSQL e API sobem localmente com configuração documentada, e a prontidão detecta indisponibilidade do banco.

**Progresso em 19/10/2026:** etapa concluída por Codex. Python 3.12.x, workspace uv e lockfile, pacotes instaláveis, PostgreSQL 17 em Compose com volume persistente, FastAPI, configuração validada, pool/sessões, armazenamento local com interface de objetos e CI inicial preparados. Migrações e escritas de domínio pertencem à etapa 03; CLI de coletor e ML possui somente ajuda/versão. Os logs HTTP já têm ID; IDs operacionais serão implementados com as execuções reais. Foram aprovados 19 testes locais, sem skips, lint e formatação. Teste HTTP real confirmou health 200/ready 503 com banco parado e ready 200 após recuperação. Workflow do GitHub preparado, ainda sem execução remota. Instruções no [README do backend](../backend/README.md), [contratos](CONTRATOS_BACKEND_E_DADOS.md) e [evidência de validação](diagnostico/validacao_etapa02.json).

## 03 — Modelar e versionar o PostgreSQL

Dependências: 01 e 02. Adicionar tabelas por migrações conforme cada domínio for implementado; não exigir todas para iniciar a coleta.

- [x] Formalizar tipos, chaves oficiais, granularidades e relações em um diagrama ou dicionário.
- [x] Criar Alembic e migração de `execucoes_coleta`, `arquivos_coletados` e `importacoes`.
- [x] Criar `versoes_base` e associações aos arquivos/importações de origem.
- [x] Criar `orgaos`, `fornecedores`, `modalidades`, `processos` e `itens_processo`.
- [x] Criar `resultados_itens` com a granularidade real da fonte e múltiplos vencedores por item.
- [x] Criar `participacoes` após diagnosticar propostas/participantes do Compras.gov.br, documentando a cobertura de itens homologados.
- [x] Criar `contratos`, `contratos_versoes`, `contratos_processos` e `documentos` com vínculos verificados.
- [x] Criar `versoes_modelo`, `execucoes_analise`, vínculos dos modelos da execução e resultados por alvo.
- [x] Criar `avaliacoes_processo`, `fatores_sinalizacao` e `comparacoes_itens`.
- [x] Criar `usuarios`, `revisoes` e `relatorios` antes de implementar essas funcionalidades.
- [x] Usar `NUMERIC` para dinheiro, texto para identificadores e tipos de data adequados.
- [x] Definir unicidade por fonte/chave e restrições de integridade dos alvos de análise.
- [x] Criar índices para filtros, relacionamentos, ranking por execução e histórico de revisão.
- [x] Definir a estratégia para versões corrigidas dos dados, preservando bases usadas em análises anteriores.
- [x] Criar papéis/permissões de API, coletor, processamento e migração.
- [x] Verificar criação do esquema em banco vazio e atualização a partir da migração anterior.

**Concluído quando:** as migrações necessárias à entrega atual são reproduzíveis e as relações não restringem um processo a um único item ou vencedor.


**Progresso em 19/10/2026:** núcleo aplicável da etapa implementado: 14 de 16 tarefas. Há 29 tabelas em três revisões Alembic (`0001_coleta`, `0002_dominio`, `0003_proveniencia`), aplicadas sob `licita_migrator`. API/coleta/processamento têm grupos e logins locais separados; a API foi reiniciada com o login restrito. Foram aprovados 27 testes, sem skips, lint, formatação e comparação entre metadata e banco. Testes de migração/downgrade usam schemas descartáveis no banco `_test`; não removem o schema da aplicação. Dicionário em [BANCO_DE_DADOS.md](BANCO_DE_DADOS.md) e evidências em [validacao_etapa03.json](diagnostico/validacao_etapa03.json).

**Conclusão em 20/10/2026:** 16 de 16 tarefas concluídas por Codex. O [diagnóstico complementar](DIAGNOSTICO_PARTICIPACOES_CONTRATOS_DOCUMENTOS.md) verificou propostas, contratos e metadados de anexos. A revisão `0004_complementos` foi aplicada com cinco novas tabelas, expansão da proveniência e permissões reaplicadas: 34 tabelas de aplicação. Foram aprovados 43 testes, sem skips, lint, formatação e comparação entre metadata e banco. Os quatro arquivos e as nove execuções já coletados foram preservados. Evidência em [validacao_etapa03_complementos.json](diagnostico/validacao_etapa03_complementos.json).

**Limites da entrega:** propostas da fonte cobrem itens homologados, sem garantia de participantes universais. Compras.gov.br permanece principal; PNCP é complemento explícito de anexos e assinatura contratual. Novos conectores e importadores ainda não foram implementados; a CLI de produção segue coletando os quatro ZIPs originais. A aquisição ampliada e a importação ficam acompanhadas na etapa 05. Não há rotas de negócio nem modelos treinados.

## 04 — Implementar a coleta de um mês

Dependências: 01, 02 e tabelas operacionais de 03.

- [x] Implementar CLI com competência/intervalo e configuração explícitos.
- [x] Implementar descoberta de arquivos usando URLs verificadas da fonte.
- [x] Implementar download em streaming, timeout e retentativas limitadas com espera progressiva.
- [x] Diferenciar arquivo ainda indisponível, resposta inválida e erro de rede.
- [x] Validar conteúdo recebido, integridade e tamanho quando informado.
- [x] Gravar arquivo temporário e só confirmar o objeto depois da validação.
- [x] Calcular SHA-256 e organizar originais por fonte, competência e versão.
- [x] Registrar execução, arquivo, duração, bytes, status e erros no banco.
- [x] Implementar adaptadores de armazenamento local e S3/R2.
- [x] Implementar extração segura, com limites de recursos e prevenção de caminhos fora do destino.
- [x] Proteger contra execuções concorrentes conflitantes.
- [x] Impedir duplicação quando o mesmo conteúdo for coletado novamente.
- [x] Preservar uma nova versão quando a fonte alterar o arquivo.
- [x] Implementar retomada e reprocessamento por identificador.
- [x] Testar download válido, falha transitória, resposta HTML, arquivo incompleto e repetição.

**Concluído quando:** um mês real é coletado e rastreável, e repetir o comando não duplica conteúdo nem metadados equivalentes.

**Progresso em 20/10/2026:** implementado por Codex. Os quatro ZIPs de setembro de 2026 foram adquiridos diretamente do Compras.gov.br com o login restrito do coletor e persistidos em armazenamento local. Há CLI de coleta, retomada e reprocessamento, locks PostgreSQL por arquivo/mês, validação CRC/SHA-256, extração confinada e versionamento por conteúdo. Foram aprovados 38 testes, inclusive integração com permissões de coletor, falhas HTTP, retomada, repetição, versões e concorrência. O adaptador S3/R2 foi testado por contrato com cliente simulado; conta/bucket remoto não foram provisionados. Comandos no [README do coletor](../collector/README.md) e resultados da coleta/repetição em [validação da etapa 04](diagnostico/validacao_etapa04.json). Nenhuma linha de domínio foi importada; próximo passo: etapa 05.

## 05 — Preparar e importar os dados

Dependências: 03 e 04.

- [x] Ampliar a aquisição para ZIPs de propostas, contratos via API Compras.gov.br e detalhe/anexos via PNCP, com paginação, versionamento e proveniência conforme diagnóstico complementar.

- [x] Implementar leitores por tipo de arquivo e versão de esquema.
- [x] Validar colunas obrigatórias e interromper com diagnóstico diante de mudança incompatível.
- [x] Normalizar identificadores sem perder zeros iniciais.
- [x] Tratar valores monetários com `Decimal`, datas e unidades explicitamente.
- [x] Preservar ausências como `NULL`; distinguir desconhecido de zero.
- [x] Definir deduplicação e precedência entre registros corrigidos.
- [x] Separar registros rejeitados com motivo e contagem, sem expor dados desnecessários nos logs.
- [x] Importar entidades e relações em lotes com transações adequadas.
- [x] Preservar proveniência entre registros, importações e arquivos.
- [x] Gerar Parquet particionado e manifesto versionado da base.
- [x] Registrar código/transformação, esquema, checksums, período, filtros e contagens no manifesto.
- [x] Reconciliar totais da origem, registros aceitos e rejeitados.
- [x] Testar repetição da importação, correção de arquivo e recuperação após falha.
- [x] Medir consumo real de memória, disco e PostgreSQL, incluindo índices.

**Concluído quando:** a mesma origem gera uma base reproduzível e uma segunda importação não duplica entidades ou valores.

**Progresso em 20/10/2026:** 15 de 15 tarefas verificadas por Codex. Aquisição complementar de propostas, respostas paginadas do Compras.gov.br e metadados/detalhe PNCP implementada; preparação/importação pelo pacote `licita-ml`, sem importar a aplicação HTTP. CSV/JSON versionados, conversões com Decimal, resolução explícita de conflitos, rejeições rastreáveis, transação atômica, Parquet particionado e manifesto imutável implementados. Foram aprovados 54 testes, sem skips, incluindo correção, reexecução e falha no meio da importação. O recorte CATMAT 486054 de setembro/2026 foi importado e repetido sem duplicação. [Regras e resultados](PREPARACAO_E_IMPORTACAO.md), [comandos ML](../ml/README.md) e [evidência](diagnostico/validacao_etapa05.json).

**Cobertura real:** 7 processos, 10 itens, 8 resultados, 130 referências de preços e 10 metadados de documentos na base validada. Foram separadas 121 linhas por vínculo ausente; não houve propostas/contratos vinculáveis neste recorte. Há fontes vazias e unidades ausentes documentadas. A validação técnica não habilita treinamento automaticamente; binários de anexos não foram baixados, e não há modelo/score nem rotas de negócio. O processamento possui limites explícitos de tamanho e recorte; expansão histórica maior exige nova medição. Próximo passo: 06.

## 06 — Disponibilizar consultas de processos e dados de apoio

Dependência: 05. A autenticação das operações de escrita será tratada em 11.

- [x] Definir contratos Pydantic, convenções de erro e limites de paginação.
- [x] Padronizar prefixo `/api/v1`, IDs, datas e dinheiro como string decimal no JSON.
- [x] Implementar `GET /orgaos` e `GET /modalidades`.
- [x] Implementar `GET /base/status` com cobertura e última carga concluída.
- [x] Implementar `GET /processos` e `GET /processos/{id}`.
- [x] Implementar filtros de órgão, fornecedor, período de homologação, modalidade e valor.
- [x] Implementar busca e ordenação com campos permitidos e desempate por ID.
- [x] Implementar `GET /processos/{id}/itens`.
- [x] Implementar `GET /processos/{id}/documentos`, retornando lista vazia quando não houver documentos conhecidos.
- [x] Mostrar ausência de análise explicitamente até a publicação dos modelos.
- [x] Testar filtros, paginação, valores agregados, IDs inexistentes e entrada inválida.
- [x] Verificar que joins de participantes/documentos não multiplicam valores homologados.

**Concluído quando:** a API permite explorar o recorte real e a documentação OpenAPI corresponde aos contratos implementados.

**Progresso em 20/10/2026:** 12 de 12 tarefas verificadas. Sete rotas de leitura implementadas, com seleção de base validada, snapshots isolados, paginação, busca literal, filtros e ordenação permitida. Valores globais e do recorte separados; totais incompletos permanecem nulos e resultados cancelados são excluídos das somas/filtros. Documentos diretos e contratuais com vínculo comprovado são consultáveis; ausência de análise é explícita, sem score publicado. Foram aprovados 95 testes locais, sem skips, incluindo consultas sob `licita_api` em PostgreSQL isolado, além de lint/formatação e verificação HTTP TCP com dados reais. Não houve migração, importação ou alteração do frontend. [Contratos e comandos da API](API_CONSULTAS.md), [evidência](diagnostico/validacao_etapa06.json). Próximo passo: etapa 07, priorizando comparabilidade e data de resultado, com validação de utilidade ainda pendente.

## 07 — Definir e calcular atributos analíticos

Dependência: 05. Pode evoluir em paralelo ao desenvolvimento das consultas de 06.

- [ ] Definir grupos de itens comparáveis por catálogo, especificação, unidade e condições relevantes.
- [ ] Definir janela temporal e política para preços de períodos distintos.
- [ ] Estabelecer amostra mínima para mediana e faixa de referência.
- [ ] Calcular preço unitário/mediana somente quando os dados forem comparáveis.
- [ ] Calcular diferença entre estimado e homologado na mesma granularidade.
- [ ] Obter participantes com cobertura explícita, sem converter desconhecidos em zero.
- [ ] Definir universo e período da frequência fornecedor–órgão.
- [ ] Calcular participação e HHI usando todos os fornecedores do universo, não apenas os sinalizados.
- [ ] Calcular intervalo publicação–contrato apenas com vínculo comprovado.
- [ ] Definir tratamento de categorias, nulos, escalas e transformações logarítmicas.
- [ ] Versionar as regras de atributos e registrar razões para atributos indisponíveis.
- [ ] Criar testes com exemplos conhecidos para preço/mediana, HHI e frequência.

**Concluído quando:** cada atributo pode ser reproduzido, com fórmula, janela, universo, granularidade e tratamento de ausência documentados.

## 08 — Treinar e avaliar o baseline Isolation Forest

Dependência: 07.

- [ ] Definir unidade de análise: processo, item ou ambos com políticas distintas.
- [ ] Separar treino e avaliação temporalmente quando viável.
- [ ] Impedir vazamento de dados futuros nas referências e transformações.
- [ ] Ajustar pré-processamento apenas no conjunto de treino.
- [ ] Treinar Isolation Forest com parâmetros e sementes registrados.
- [ ] Medir duração, memória e distribuição do score bruto.
- [ ] Avaliar estabilidade entre sementes e sensibilidade aos parâmetros.
- [ ] Revisar manualmente uma amostra dos casos prioritários e registrar critérios e limitações.
- [ ] Usar casos públicos conhecidos apenas quando houver vínculo confiável.
- [ ] Definir transformação de score para 0–100 e registrar sua versão.
- [ ] Definir limiares de prioridade; tratar as faixas do protótipo como proposta, não validação.
- [ ] Salvar pré-processamento e modelo juntos, com dependências, código e manifesto da base.
- [ ] Registrar versão do modelo e relatório de avaliação.
- [ ] Verificar que carregar o artefato reproduz a inferência no conjunto de referência.

**Concluído quando:** há um baseline reproduzível e uma justificativa documentada para publicar seus resultados, sem alegações de acurácia ou probabilidade de fraude não sustentadas.

## 09 — Publicar inferências e explicações

Dependência: 08 e tabelas analíticas de 03.

- [ ] Implementar comando de inferência em lote para base e modelo explícitos.
- [ ] Criar execução de análise com estado e vínculos às versões utilizadas.
- [ ] Gravar scores brutos, normalizados, cobertura e fatores disponíveis.
- [ ] Definir agregação de itens para processo, se necessária, evitando média arbitrária.
- [ ] Definir o score oficial do ranking e preservar scores individuais por algoritmo.
- [ ] Implementar explicabilidade adequada ao modelo; distinguir contribuição calculada de indicador descritivo.
- [ ] Registrar método, referência e versão das explicações.
- [ ] Não preencher pesos ou contribuições fictícias quando a explicação não estiver disponível.
- [ ] Persistir comparações com tamanho da amostra e universo utilizados.
- [ ] Validar o lote e ativar a execução de forma atômica; falha não troca a versão publicada.
- [ ] Manter análises anteriores rastreáveis e definir retenção.
- [ ] Implementar `GET /analises/execucoes` e seleção por `execucao_analise_id`.
- [ ] Implementar `GET /processos/{id}/analises` e `GET /itens/{id}/comparacao`.
- [ ] Devolver base/execução nos metadados das consultas.
- [ ] Testar repetição, falha no lote, troca da execução ativa e ausência de score.

**Concluído quando:** uma análise completa é publicada sem expor lote parcial e qualquer resultado pode ser associado a sua base e modelo.

## 10 — Completar painel, rankings e fornecedores

Dependências: 06 e 09.

- [ ] Adicionar filtros por score, prioridade, status de revisão e indicadores analíticos disponíveis.
- [ ] Implementar `GET /processos/resumo`, com regra explícita para contadores das abas.
- [ ] Implementar `GET /painel/resumo`.
- [ ] Implementar `GET /painel/distribuicao-scores`, incluindo não analisados.
- [ ] Implementar `GET /painel/evolucao-prioridade`, com data de referência definida.
- [ ] Implementar `GET /fornecedores/resumo` e `GET /fornecedores`.
- [ ] Implementar `GET /fornecedores/{id}` e `GET /fornecedores/{id}/concentracao`.
- [ ] Reutilizar a consulta de processos para listar os relacionados ao fornecedor.
- [ ] Distinguir quantidade de processos, contratos e itens nas métricas.
- [ ] Validar consistência entre resumo, lista, detalhe e concentração sob os mesmos filtros.
- [ ] Inspecionar consultas mais usadas e ajustar índices quando houver evidência de necessidade.

**Concluído quando:** os números do painel são reconciliáveis com as listagens e os denominadores da concentração estão documentados.

## 11 — Autenticar usuários e registrar revisão humana

Dependências: 06, 09 e tabelas de usuários/revisões de 03. Não publicar escrita aberta antes desta etapa.

- [ ] Escolher provedor de identidade e definir papéis de acesso.
- [ ] Decidir quais leituras podem ser públicas.
- [ ] Implementar validação de identidade no servidor e associação ao usuário local.
- [ ] Implementar autorização de revisão e emissão de relatórios.
- [ ] Implementar `GET /processos/{id}/revisoes`.
- [ ] Implementar `POST /processos/{id}/revisoes`.
- [ ] Obter autor da sessão/token validado, nunca de um ID livre enviado pelo cliente.
- [ ] Validar transições de status, observação e vínculo à análise consultada.
- [ ] Preservar cada revisão e atualizar o estado consolidado na mesma transação.
- [ ] Definir tratamento para revisões concorrentes e atualização de análise após revisão humana.
- [ ] Testar acesso sem identidade, papel insuficiente, autor correto e preservação do histórico.

**Concluído quando:** revisões são atribuídas a usuários válidos, auditáveis e independentes do score do modelo.

## 12 — Implementar relatórios e exportações

Dependências: 10 e 11.

- [ ] Definir escopos de relatório, limites de seleção, seções e formatos PDF/CSV.
- [ ] Escolher biblioteca PDF e validar seu funcionamento no ambiente de execução.
- [ ] Implementar serviço de dados compartilhado por prévia e exportação.
- [ ] Implementar `POST /relatorios/previa`.
- [ ] Implementar `POST /relatorios`, retornando 202 e ID da tarefa persistida.
- [ ] Persistir seleção, filtros, autor, base, execução e snapshot/referências imutáveis da emissão.
- [ ] Implementar comando worker que reserve tarefas com segurança e sobreviva a reinícios.
- [ ] Implementar retentativas limitadas, estado de falha e prevenção de processamento concorrente duplicado.
- [ ] Gerar CSV com escape correto e tratamento de células interpretáveis como fórmulas.
- [ ] Incluir método, origem, cobertura, limitações e aviso de revisão humana nas exportações.
- [ ] Armazenar arquivos fora do disco efêmero da API.
- [ ] Implementar `GET /relatorios/{id}` e `GET /relatorios/{id}/download` com autorização.
- [ ] Definir retenção/expiração dos arquivos e resposta para download indisponível.
- [ ] Confirmar onde o worker será executado; não presumir worker gratuito no Render.
- [ ] Testar consistência entre prévia/arquivo e reprodução após mudança da análise ativa.

**Concluído quando:** um usuário autorizado gera e baixa um documento rastreável, e uma falha/reinício não perde silenciosamente a solicitação.

## 13 — Ampliar a carga histórica com controle de recursos

Dependências: 05, 07 e baseline funcional de 09. Pode começar antes de relatórios, após validar o fluxo de ponta a ponta.

- [ ] Executar coleta de mais competências em lotes limitados.
- [ ] Medir tempo, memória, rede, armazenamento e crescimento do banco por lote.
- [ ] Comparar distribuições e qualidade entre competências.
- [ ] Ajustar particionamento de arquivos e tamanho de lote quando necessário.
- [ ] Definir o recorte de treinamento e o recorte publicado no banco separadamente.
- [ ] Validar que a concentração usa o universo necessário mesmo quando o painel publica apenas um recorte.
- [ ] Reavaliar referências temporais e modelos com o histórico ampliado.
- [ ] Publicar nova versão de base/análise somente após validação.

**Concluído quando:** o histórico escolhido cabe nos recursos disponíveis e a aplicação informa exatamente a cobertura publicada.

## 14 — Containerizar e preparar a publicação

Dependências: serviços locais validados e estimativas da etapa 13. Provisionar apenas os componentes prontos.

- [ ] Criar Dockerfiles reproduzíveis para backend e coletor, sem segredos na imagem.
- [ ] Documentar comandos de processamento, inferência e worker usados fora da API.
- [ ] Atualizar Compose para o fluxo local que a equipe precisa reproduzir.
- [ ] Revalidar planos, limites, exigências de pagamento e suspensão dos provedores propostos.
- [ ] Confirmar viabilidade de PostgreSQL no Supabase, arquivos no R2 e API no Render.
- [ ] Dimensionar banco incluindo índices, revisões e resultados por versão.
- [ ] Criar banco/bucket privados e credenciais de privilégio mínimo.
- [ ] Configurar TLS, pool de conexões e concorrência compatíveis com os limites do banco.
- [ ] Configurar secrets, identidade, origens CORS e limites de execução.
- [ ] Executar migrações como etapa controlada da implantação.
- [ ] Publicar um recorte validado e uma execução de análise identificada.
- [ ] Publicar API e verificar saúde, prontidão, autenticação e acesso ao armazenamento.
- [ ] Verificar comportamento após suspensão/reinício do provedor.
- [ ] Definir rollback da aplicação e compatibilidade com migrações.
- [ ] Validar exportação no ambiente onde o worker realmente será executado.

**Concluído quando:** a API hospedada consulta dados persistentes, sem depender de arquivos do disco temporário, e o custo esperado está registrado.

## 15 — Automatizar CI/CD e atualização da coleta

Dependências: 04 e CI inicial de 02; ativar agendamento após validar a publicação de 14.

- [ ] Completar CI para importação, API e modelos conforme os componentes evoluírem.
- [ ] Usar PostgreSQL temporário em testes de integração que exigem o banco real.
- [ ] Manter fixtures pequenas, identificadas como artificiais, e excluir datasets/artefatos do Git.
- [ ] Criar workflow manual de coleta com intervalo validado.
- [ ] Configurar secrets e permissões mínimas do workflow.
- [ ] Configurar timeout e controle de concorrência para evitar cargas sobrepostas.
- [ ] Definir janela de revisita de competências corrigidas e frequência de atualização.
- [ ] Ativar agendamento após uma execução manual bem-sucedida.
- [ ] Separar coleta, preparação, inferência e publicação com estados observáveis.
- [ ] Impedir publicação automática de novo modelo sem a avaliação definida.
- [ ] Registrar procedimento de retomada quando um agendamento falhar ou não executar.
- [ ] Automatizar implantação após validações, mantendo secrets fora dos logs.

**Concluído quando:** a execução manual e a agendada são rastreáveis, sem duplicação, e uma falha não substitui a base válida por resultados parciais.

## 16 — Implementar e comparar Autoencoder

Dependências: 08, 09 e base suficiente validada em 13. Evolução posterior ao baseline, mas necessária para completar a comparação prevista na proposta acadêmica.

- [ ] Escolher TensorFlow/Keras ou PyTorch conforme recursos e compatibilidade.
- [ ] Definir arquitetura, normalização, função de perda e estratégia de treinamento.
- [ ] Treinar com separação temporal e pré-processamento ajustado somente no treino.
- [ ] Registrar parâmetros, sementes, dependências e base.
- [ ] Avaliar erro de reconstrução, estabilidade, recursos e casos prioritários.
- [ ] Definir normalização própria do score e limitações da explicação.
- [ ] Comparar com Isolation Forest sob o mesmo protocolo e recorte de avaliação.
- [ ] Documentar concordâncias, divergências e revisão qualitativa.
- [ ] Definir qual modelo/política alimenta o ranking; não combinar scores arbitrariamente.
- [ ] Publicar a versão aprovada e preservar os resultados anteriores.

**Concluído quando:** a comparação é reproduzível e a decisão sobre o modelo de ranking tem evidências e limitações registradas.

## 17 — Validar operação, restauração e entrega acadêmica

Dependências: todas as funcionalidades incluídas na entrega. Segurança, logs e backup devem ser trabalhados desde o início, não apenas nesta revisão final.

- [ ] Executar fluxo completo: coleta → preparação → análise → publicação → consulta → revisão → relatório.
- [ ] Conferir rastreabilidade de um resultado até o arquivo original e modelo utilizado.
- [ ] Simular falha de download, indisponibilidade do banco e reinício do worker.
- [ ] Testar backup e restauração de dados operacionais e relacionamentos.
- [ ] Aplicar política de retenção sem remover artefatos referenciados por relatórios preservados.
- [ ] Confirmar que logs não expõem credenciais e respostas não incluem dados pessoais desnecessários.
- [ ] Conferir limites de armazenamento e alertas/monitoramento disponíveis.
- [ ] Documentar comandos de instalação, operação, atualização e recuperação.
- [ ] Atualizar o contexto com decisões efetivas, limitações e diferenças em relação à proposta inicial.
- [ ] Preparar evidências da avaliação dos modelos, qualidade da base e funcionamento da API.
- [ ] Verificar que nenhum score é apresentado como comprovação ou probabilidade de fraude.

**Concluído quando:** outra pessoa consegue reproduzir a instalação e o fluxo documentado, e a equipe demonstra o projeto com dados e resultados rastreáveis.

## Marcos de acompanhamento

| Marco | Etapas principais | Evidência esperada |
| --- | --- | --- |
| Fonte compreendida | 01 | Diagnóstico de um mês e mapeamento de campos |
| Base operacional | 02–05 | Coleta e importação repetíveis com banco local |
| API com dados reais | 06 | Consultas documentadas e cobertura explícita |
| Baseline publicável | 07–09 | Modelo reproduzível e execução consistente |
| Funcionalidades do protótipo atendidas pela API | 10–12 | Painel, fornecedores, revisões e relatórios |
| Operação hospedada | 13–15 | Histórico dimensionado, implantação e coleta automatizada |
| Comparação acadêmica completa | 16 | Avaliação documentada dos dois modelos |
| Entrega reproduzível | 17 | Fluxo completo, restauração e documentação |

## Próxima ação

As etapas técnicas 01–06 estão documentadas como concluídas; os ensaios anteciparam parte de 07/08, sem aprovação do ranking. A próxima ação de organização é consolidar o trabalho local na etapa 01 do [plano atual](PLANO_CONCLUSAO.md), seguida dos contratos item/processo e da integração. No núcleo analítico, priorizar comparabilidade, data do resultado e revisão independente antes de publicar scores.
