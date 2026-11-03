# Licita Clara — contexto de backend, coleta e dados

Documento de referência para implementar os componentes que não pertencem ao frontend.
Atualizado em 20/10/2026. Descreve decisões de arquitetura e propostas; não comprova que os serviços estejam implementados ou provisionados.

Revisão de comandos e contratos em 03/11/2026. Para o acompanhamento atual, usar o [plano de conclusão](PLANO_CONCLUSAO.md); as notas datadas preservam a evolução técnica. O frontend atualizado em 01/11/2026 continua com dados simulados.

## 1. Objetivo e escopo

O Licita Clara é um projeto acadêmico da FATEC Jacareí para priorizar a análise de licitações públicas com comportamentos estatísticos atípicos. Deve coletar dados públicos, preservar sua origem, preparar atributos, comparar modelos não supervisionados e disponibilizar resultados explicáveis em uma API.

Anomalia estatística não é prova de irregularidade. Score indica prioridade de análise, nunca probabilidade de fraude. A revisão humana é independente do resultado do modelo.

Este documento cobre backend, banco, coleta, processamento, treinamento, inferência em lote, exportação, infraestrutura e validação. Não inclui implementação visual. As telas fornecidas orientam os contratos da API, mas seus números e percentuais são simulados e não devem ser importados como resultados reais.

## 2. Estado atual e decisões

- O repositório contém protótipo React, diagnósticos executados e ambiente inicial de backend: FastAPI com saúde/prontidão, configuração, sessões PostgreSQL, armazenamento local e [consultas versionadas de processos, itens e documentos](API_CONSULTAS.md). O coletor possui CLI de aquisição, retomada e reprocessamento; o pacote ML prepara e importa recortes com Parquet/manifesto. Um [ensaio experimental de Isolation Forest](validacao_nucleo/RESULTADO.md) foi executado com histórico real, mas não publicou scores. A [revisão posterior](validacao_nucleo/REVISAO_E_CONFIRMACAO.md) encontrou divergências de especificação e motivou um ensaio corretivo por data do resultado; estabilidade técnica foi reproduzida, mas a publicação de risco não está aprovada e a utilidade aguarda revisão independente. PostgreSQL local está configurado por Compose; o domínio tem 34 tabelas e quatro migrações aplicadas, incluindo propostas, contratos e documentos diagnosticados. Compras.gov.br é a fonte principal; PNCP complementa anexos e assinatura contratual.
- Backend: Python com FastAPI.
- Banco recomendado para implementação: PostgreSQL, com SQLAlchemy e migrações Alembic.
- Não adicionar MongoDB, Redis, Kafka ou Kubernetes ao MVP sem uma necessidade comprovada.
- Coletor independente, executado como comando Python em lote; não precisa de servidor HTTP permanente.
- Treinamento e inferência em lote fora das requisições da API.
- Histórico bruto e datasets de treinamento em arquivos; banco voltado ao controle operacional e às consultas da aplicação.
- Monorepositório, mantendo serviços executáveis e implantáveis separadamente.
- Preservar o nome `Frontend-licita-clara`; o frontend não faz parte deste trabalho.
- A experiência do projeto CNJ foi mencionada como referência, mas seu código e detalhes não foram fornecidos. Não presumir implementações ou dependências herdadas.

### Ambiente inicial implementado — etapa 02

Python 3.12.x; dependências resolvidas em `uv.lock` com uv 0.13.2; PostgreSQL 17 local fixado por digest no Compose; API operacional com `/api/v1/health` e `/api/v1/ready`. A conexão é lazy: a API inicia mesmo se o banco estiver indisponível e prontidão retorna 503. Interface de armazenamento e adaptador local implementados, sem S3/R2 ativo. CI Python preparado, sem implantação remota.

Foram aprovados 19 testes locais com integração PostgreSQL, lint e formatação. A queda e recuperação do banco foram verificadas via HTTP real. Ver [contratos entre componentes](CONTRATOS_BACKEND_E_DADOS.md), [instruções do backend](../backend/README.md) e [evidência](diagnostico/validacao_etapa02.json).

### Esquema inicial implementado — etapa 03

Três revisões Alembic aplicadas (`0001_coleta`, `0002_dominio`, `0003_proveniencia`) e metadata consistente. Identidades de processos/itens são estáveis; dados de negócio são snapshots por base. Análises e revisões referenciam essas versões. Fontes/importações têm proveniência rastreável; reimportar a mesma linha/alvo não pode duplicar o vínculo.

API, coletor e processamento possuem grupos NOLOGIN e logins locais separados. `DATABASE_URL` usa a identidade restrita da API; `MIGRATION_DATABASE_URL` fica reservada aos comandos administrativos. Não foram importados dados reais. Foram aprovados 27 testes, inclusive migração de banco vazio, atualização com preservação de registros, invariantes e permissões em PostgreSQL real. Ver [evidência](diagnostico/validacao_etapa03.json).

### Complemento concluído da etapa 03 — 20/10/2026

A revisão `0004_complementos` acrescenta `participacoes`, `contratos`, `contratos_versoes`, `contratos_processos` e `documentos`, com vínculos da mesma base e proveniência para os novos alvos. As 16 tarefas de modelagem estão concluídas. Na conclusão da modelagem, 43 testes passaram, incluindo atualização com preservação do histórico e permissões. A etapa 05 posteriormente importou o recorte descrito abaixo.

Propostas são obtidas em ZIP próprio do Compras.gov.br, com cobertura de itens homologados, inclusive não vencedores. PNCP é complemento explícito para metadados de documentos de compra/contrato e data de assinatura do contrato; vigência não substitui assinatura. O diagnóstico não amplia automaticamente o coletor de produção. [Mapeamento e limitações](DIAGNOSTICO_PARTICIPACOES_CONTRATOS_DOCUMENTOS.md), [evidências](diagnostico/validacao_etapa03_complementos.json). Os novos conectores e a importação foram implementados na etapa 05.

### Coletor implementado — etapa 04

CLI independente com coleta por arquivo/mês, descoberta no índice oficial, download limitado com retentativas e retomada por ETag/Range, validação CRC/SHA-256 e extração segura. Originais são versionados pelo hash; PostgreSQL registra execuções e observações sem duplicar conteúdo. Locks por arquivo/mês impedem conflito entre intervalos sobrepostos. Um pacote compartilhado define armazenamento local e adaptador S3/R2; a dependência S3 é opcional. O ambiente atual usa disco local, sem infraestrutura remota provisionada.

A coleta e o reprocessamento não importam linhas de negócio. Preparação, deduplicação semântica e importação pertencem à etapa 05. Comandos e limitações no [README do coletor](../collector/README.md); evidências em [validação da etapa 04](diagnostico/validacao_etapa04.json).

### Preparação e importação implementadas — etapa 05

A aquisição complementar agora atende propostas em ZIP e respostas JSON Compras.gov.br/PNCP com paginação controlada, versionamento e texto original das respostas nas novas aquisições. `licita-ml preparar` usa identidade restrita de processamento, leitores versionados, Decimal, validação, resolução de conflitos e rejeições. Exporta Parquet por base/catálogo/entidade, preserva proveniência e confirma a base em uma transação. Repetição reutiliza a base; correções geram outra versão.

O piloto real de setembro/2026, CATMAT 486054, resultou em 7 processos, 10 itens, 8 resultados, 130 referências de preços e 10 metadados de documentos. Foram rejeitadas 121 linhas por vínculo ausente e não houve propostas ou contratos vinculáveis no recorte. Cobertura parcial permanece explícita; `validada` significa integridade técnica, sem aprovação automática para treino. Foram aprovados 54 testes, sem skips. Detalhes em [preparação e importação](PREPARACAO_E_IMPORTACAO.md) e [evidência](diagnostico/validacao_etapa05.json).

## 3. Arquitetura

```text
Compras.gov.br (compras, resultados, preços, propostas e contratos)
+ PNCP (complemento: detalhe contratual e documentos)
        |
        v
Coletor Python (manual/agendado) ----> PostgreSQL: controle da coleta
        |
        v
Armazenamento de objetos: arquivos brutos imutáveis
        |
        v
Validação, limpeza e normalização
        |
        v
Parquet + manifesto da base
        |
        +----> Treinamento e avaliação ----> Artefatos dos modelos
        |                                        |
        +----------------> Inferência em lote <---+
                                  |
                                  v
                    PostgreSQL: recorte publicado,
                    scores, referências e explicações
                                  |
                                  v
                         FastAPI /api/v1
```

Começar com um backend modular e um único PostgreSQL. O coletor grava metadados operacionais; a preparação importa o recorte de consulta; o processo de análise publica resultados. Usar credenciais e permissões específicas para cada componente. Migrações são uma etapa controlada da implantação, não uma operação disparada por cada execução do coletor. O esquema implementado e as permissões estão em [BANCO_DE_DADOS.md](BANCO_DE_DADOS.md).

## 4. Fonte e descoberta dos dados

Fonte principal confirmada após diagnóstico: **Compras.gov.br**, consumindo módulos de contratações/itens/resultados e pesquisa de preços/catálogo. API: `https://dadosabertos.compras.gov.br`; repositório: `https://repositorio.dados.gov.br/seges/comprasgov/`. Ver [diagnóstico complementar](DIAGNOSTICO_COMPRASGOV.md).

Não integrar o Portal da Transparência no MVP inicial. Os arquivos já baixados são evidência do diagnóstico histórico; não são uma segunda fonte obrigatória. A descrição abaixo registra a investigação inicial desse pacote:

- Downloads: https://portaldatransparencia.gov.br/download-de-dados/licitacoes
- Informações da API: https://portaldatransparencia.gov.br/api-de-dados
- Documentação dos endpoints: https://api.portaldatransparencia.gov.br/
- Cadastro de token: https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email

O portal informa arquivos de licitações, itens, participantes e empenhos relacionados. A API pode complementar consultas; para grandes volumes, a orientação oficial é utilizar os arquivos de dados abertos. Confirmar autenticação, parâmetros, limites e disponibilidade antes de implementar; não assumir URLs de download ou endpoints não verificados.

A referência ao dataset “Brazilian Public Tenders / Licitações e Contratos” no PDF não identifica uma base de forma inequívoca. Não tratá-la como fonte validada. O portal também não deve ser apresentado como cobertura automática de todas as compras de estados e municípios: registrar a cobertura efetivamente encontrada.

### Primeira entrega: diagnóstico de um mês

1. Consultar dicionários e baixar uma competência real.
2. Inventariar arquivos, codificação, delimitador, colunas, tipos e chaves oficiais.
3. Medir tamanhos compactado, extraído, Parquet e estimativa de importação no PostgreSQL.
4. Verificar disponibilidade e qualidade de datas, participantes, unidades, preços, quantidades e fornecedores.
5. Documentar vínculos entre processos, itens, resultados e contratos; não presumir que todos estejam no mesmo pacote.
6. Definir um recorte inicial de 12 a 24 meses e uma categoria comparável, condicionado ao diagnóstico.

Se um atributo proposto não existir, registrar a limitação e ajustar a análise. Não fabricar dados para completar a interface.

### Diagnóstico executado em 19/10/2026

Ver [DIAGNOSTICO_FONTE_LICITACOES.md](DIAGNOSTICO_FONTE_LICITACOES.md). Downloads de março e abril de 2024 foram verificados localmente, sem token. A página lista competências até abril de 2024; o arquivo de abril contém datas de resultado apenas até 05/04. Março é a amostra técnica principal. Há duplicatas, códigos de item ausentes e valores totais de licitação iguais a zero. Os dois arquivos de empenhos têm somente cabeçalho.

O ZIP não contém campos próprios de unidade de medida, CATMAT/CATSER, valor estimado ou assinatura de contrato. Comparação confiável de preços e todos os sinais do protótipo dependem de fonte complementar ainda a diagnosticar. O esquema e o recorte analítico permanecem propostas; não iniciar treinamento de sobrepreço apenas com similaridade textual.

### Diagnóstico complementar e recorte piloto em 19/10/2026

O [diagnóstico do Compras.gov.br](DIAGNOSTICO_COMPRASGOV.md) verificou respostas reais da API sem token e quatro ZIPs de setembro de 2026: compras, itens, resultados e pesquisa de preços de materiais. O repositório atual é `https://repositorio.dados.gov.br/seges/comprasgov/`. Compras.gov.br é a única plataforma de dados escolhida para iniciar o piloto; Portal da Transparência permanece diagnóstico histórico, sem integração no MVP inicial.

Há unidade e valor estimado no módulo de itens, mas catálogo vazio em todas as 242.144 linhas do ZIP examinado. O módulo de pesquisa de preços contém catálogo nas 114.029 linhas, com lacunas de unidades de fornecimento. Foram encontrados 49.795 IDs comuns entre os módulos na competência; enriquecimento exige identificador e validação das unidades, sem preencher ausências arbitrariamente. O formato CSV não é igual ao JSON da API: manter mapeamentos de campos próprios por conector.

Recorte inicial escolhido: artigos para escritório, com primeiro exercício no CATMAT 486054; período histórico pretendido de outubro de 2025 a setembro de 2026. Em um grupo com 125 IDs do item por unidade, a consulta direcionada de cinco compras retornou 124 IDs no serviço de itens PNCP; um não foi resolvido. Isso não valida comparabilidade completa nem suficiência para treinamento.

Os ZIPs PNCP são particionados por publicação da compra; pesquisa de preços, por data da compra. Arquivos antigos podem ser corrigidos. Há IDs repetidos sem duplicatas exatas, e referências não resolvidas entre alguns arquivos do mês. Formalizar granularidade e precedência das versões antes de impor unicidade. O diagnóstico complementar validou propostas de itens homologados, contratos e anexos; completude por processo e regras de explicabilidade ainda precisam de validação na preparação/análise.

## 5. Coletor

### Responsabilidades

- Executar carga histórica por intervalo de competências e atualização periódica.
- Descobrir e baixar arquivos oficiais com timeouts, streaming e retentativas limitadas com espera progressiva.
- Respeitar limites da fonte; tratar indisponibilidade e ausência de arquivo separadamente de falha de processamento.
- Registrar URL, fonte, competência, instante da coleta, checksum SHA-256, tamanho e chave no armazenamento.
- Evitar duplicação: repetir uma execução não pode duplicar arquivos nem registros importados.
- Preservar revisões: se o conteúdo de uma competência mudar, guardar nova versão e manter a anterior rastreável.
- Impedir execuções simultâneas conflitantes sobre o mesmo arquivo/competência.
- Validar download e extração; não publicar arquivo incompleto, conteúdo HTML recebido como ZIP ou extração fora do diretório de destino.
- Permitir retomada e reprocessamento sem repetir todos os downloads.

### Estados e comandos implementados

Estados de execução de coleta: `pendente`, `executando`, `concluido`, `parcial`, `falhou`. Arquivos confirmados são registros de conteúdo validado; preparação/importação tem controle próprio, conforme os contratos dos componentes.

CLI disponível, executada na raiz do repositório com configuração e banco migrado:

```bash
uv run --locked --package licita-collector licita-collector coletar --inicio 2025-01 --fim 2025-12
uv run --locked --package licita-collector licita-collector retomar --execucao-id UUID_DA_EXECUCAO
uv run --locked --package licita-collector licita-collector reprocessar --arquivo-id UUID_DO_ARQUIVO
```

Substituir os UUIDs pelos IDs reais. Para revisitar competências, executar `coletar` novamente no intervalo desejado; não existe subcomando `atualizar`. O agendamento ainda será implementado e não garante que a fonte publique novos dados na mesma frequência. Comandos complementares estão no [README do coletor](../collector/README.md).

## 6. Armazenamento e processamento

Separar três classes de informação:

| Classe | Local | Exemplos |
| --- | --- | --- |
| Originais e artefatos volumosos | Armazenamento de objetos | ZIP, CSV, Parquet, modelos, relatórios |
| Controle e rastreabilidade | PostgreSQL | Coletas, arquivos, importações, versões das bases |
| Dados publicados para consulta | PostgreSQL | Processos, itens, fornecedores, análises e revisões |

Organização sugerida das chaves:

```text
raw/portal-transparencia/licitacoes/2025/01/<sha256>/arquivo.zip
processed/<versao-base>/licitacoes/ano=2025/mes=01/parte.parquet
models/<algoritmo>/<versao>/
reports/<relatorio-id>/relatorio.pdf
```

ZIP/CSV é preservado como evidência de origem. Parquet é uma representação derivada, com esquema e transformação versionados. Pode ser consultado com DuckDB no processamento; não é necessário subir um servidor DuckDB.

O manifesto da base deve listar arquivos/checksums de origem, versão do transformador, esquema, filtros, período, contagens e verificações de qualidade. Manter rastreabilidade dos registros publicados às importações, inclusive quando várias fontes participarem.

Usar processamento por lotes e seleção de colunas para não exigir que todo o histórico caiba em memória. Rejeições devem ser contadas e justificadas. Não misturar silenciosamente versões de bases.

## 7. PostgreSQL: modelo conceitual

O mapa abaixo resume o domínio previsto. O esquema físico implementado na etapa 03, incluindo identidades e snapshots separados, está em [BANCO_DE_DADOS.md](BANCO_DE_DADOS.md), referência para nomes, campos e FKs. São 34 tabelas, com UUIDs internos e identificadores oficiais textuais. A revisão `0004_complementos` acrescenta propostas de itens homologados, identidades/snapshots contratuais, vínculos e documentos, conforme diagnóstico próprio.

### Dados públicos

| Tabela | Conteúdo e relações |
| --- | --- |
| `orgaos` | Identificação oficial, nome e localização disponível |
| `fornecedores` | Tipo de identificação, identificador da fonte/CPF/CNPJ quando aplicável, razão social |
| `modalidades` | Código da fonte e descrição |
| `processos` | Fonte, chave oficial, órgão, número, ano, objeto, modalidade, situação e datas |
| `itens_processo` | Processo, número do item, descrição, código de catálogo, unidade, quantidade e preço estimado |
| `participacoes` | Fornecedor, processo/item e situação; granularidade conforme a fonte |
| `resultados_itens` | Item, fornecedor, quantidade adjudicada/homologada, preço unitário, valor total e situação |
| `contratos` / `contratos_versoes` | Identidade oficial e snapshots de órgão, fornecedor, valores e datas |
| `contratos_processos` | Vínculos comprovados entre contratos e processos |
| `documentos` | Processo, tipo, título, URL oficial e eventual chave de armazenamento |

Uma licitação pode ter vários itens e fornecedores vencedores. Não colocar um único `fornecedor_id` como representação obrigatória de todo processo. Não equiparar homologação, contrato, empenho e pagamento.

### Coleta e preparação

| Tabela | Conteúdo |
| --- | --- |
| `execucoes_coleta` | Intervalo solicitado, início, fim, status e erros |
| `arquivos_coletados` | Origem, competência, checksum, tamanho, versão e localização |
| `importacoes` | Arquivo, versão do importador, início/fim e contagens de aceitos/rejeitados |
| `versoes_base` | Identificador, manifesto, período, transformação e estado de publicação |

Prever a relação entre base e arquivos/importações. Para dados derivados de várias importações, usar uma associação de proveniência; não limitar toda a rastreabilidade a um único arquivo por processo.

### Modelagem e resultados

| Tabela | Conteúdo |
| --- | --- |
| `versoes_modelo` | Algoritmo, parâmetros, base de treino, versão do código, métricas e chave do artefato |
| `execucoes_analise` | Base avaliada, versões dos modelos, configuração, política de score e status |
| `resultados_modelo` | Execução, alvo processo ou item, versão do modelo, score bruto e normalizado |
| `avaliacoes_processo` | Score de ranking, prioridade e cobertura da análise para cada processo/execução |
| `fatores_sinalizacao` | Resultado associado, atributo, valor observado, referência, método e contribuição se calculada |
| `comparacoes_itens` | Item, execução, grupo comparável, período, tamanho da amostra, mediana e faixa de referência |

Para resultados por processo/item, assegurar por restrição que exista exatamente um tipo de alvo por registro, ou separar tabelas na implementação. Modelos da execução devem ter vínculos explícitos, não apenas nomes em texto.

### Revisões e exportações

| Tabela | Conteúdo |
| --- | --- |
| `usuarios` | Identificador do provedor de autenticação, nome e papel |
| `revisoes` | Processo, análise consultada, autor, status, observação e data |
| `relatorios` | Solicitante, título, parâmetros, seções, base/análise, estado e localização |

Revisões são histórico: não sobrescrever o registro anterior. Status inicial proposto: `a_revisar`, `em_analise`, `revisado`. A conclusão humana deve ter campo próprio e não ser inferida do score. Se houver estado atual consolidado, atualizá-lo na mesma transação que grava o histórico.

Relatórios devem guardar seleção, configuração e versão dos dados, além de um snapshot ou referência imutável suficiente para reproduzir o documento, inclusive o estado da revisão no momento da emissão.

### Integridade e índices

- Valores financeiros em `NUMERIC` e `Decimal`; preservar precisão de preço unitário, sem usar float para dinheiro.
- Códigos, CNPJ e números oficiais em texto para preservar zeros iniciais.
- Timestamps operacionais com fuso; datas de negócio em `DATE` quando não houver horário.
- Valores ausentes como `NULL`, nunca convertidos automaticamente em zero.
- Chaves estrangeiras e unicidade por fonte + chave oficial/granularidade real.
- Unicidade de resultados por execução, modelo e alvo; importações repetidas não duplicam entidades.
- Índices iniciais em órgão/data de homologação, relações com fornecedores, execução/score e processo/data da revisão. Ajustar usando consultas reais.
- `JSONB` pode guardar parâmetros, metadados e explicações variáveis; relações centrais continuam em tabelas.
- Agregações devem evitar multiplicação de valores por joins com participantes ou documentos.

## 8. Treinamento, avaliação e inferência

### Etapas

1. Análise exploratória e diagnóstico de qualidade.
2. Padronização e engenharia de atributos reproduzíveis.
3. Isolation Forest como baseline.
4. Autoencoder para comparação posterior, quando a base e os recursos permitirem.
5. Validação, explicabilidade e escolha de versão publicável.
6. Inferência em lote e publicação atômica dos resultados.

A publicação só deve trocar a execução ativa quando o lote estiver consistente. Uma nova execução não apaga resultados antigos. Não treinar nem recalcular toda a base a cada chamada HTTP.

### Atributos candidatos

- Razão entre preço unitário homologado e mediana de itens comparáveis.
- Diferença entre valores estimado e homologado, com mesma granularidade.
- Número de participantes quando efetivamente disponível.
- Frequência de contratação do fornecedor com o órgão no período definido.
- Participação do fornecedor no valor do órgão e HHI do órgão.
- Intervalo entre publicação e contrato, quando as datas e o vínculo forem conhecidos.

Participação é uma medida do fornecedor dentro do órgão; HHI é a soma dos quadrados das participações de todos os fornecedores do órgão no mesmo universo e período. Não confundir as duas medidas. Registrar denominadores e cobertura; não calcular concentração usando apenas os processos sinalizados.

Comparações de preço exigem categoria, especificação, unidade, quantidade e condições compatíveis. Registrar tamanho da amostra e não produzir referência enganosa quando faltarem comparáveis.

### Validação e reprodutibilidade

Sem rótulos, não apresentar acurácia ou probabilidade de fraude. Avaliar revisão manual dos casos prioritários, estabilidade entre sementes, concordância entre modelos e sensibilidade aos parâmetros. Casos públicos conhecidos só entram como verificação quando vinculados de forma confiável.

Separar temporalmente treino e avaliação quando possível. Ajustar normalizadores/codificadores no treino e evitar uso de dados futuros nas referências históricas. Registrar sementes, dependências, parâmetros, versão do código e manifesto. Serializar o pré-processamento junto ao modelo e carregar apenas artefatos produzidos por ambiente confiável.

### Scores e explicações

- Preservar score bruto e orientação de cada algoritmo.
- Apresentar score normalizado em 0–100, com regra de transformação versionada.
- Scores de algoritmos distintos não são automaticamente comparáveis; não tirar média sem validação.
- Escolher explicitamente o modelo ou política que alimenta o ranking.
- Faixas iniciais do protótipo: baixa `< 50`, média `50 a < 80`, alta `>= 80`; são propostas de apresentação, não limiares validados.
- Distinguir `nao_analisado` de baixa prioridade.
- Contribuições SHAP ou de outro método devem identificar método e versão. Indicadores descritivos não devem ser apresentados como explicação causal do modelo.
- Sem explicação calculada, retornar ausência e motivo. Não reproduzir pesos fictícios do protótipo.

## 9. API FastAPI

Prefixo `/api/v1`. Organizar módulos por domínio. OpenAPI gerado a partir dos contratos Pydantic. A API consulta resultados publicados e registra revisões/exportações.

### Painel

| Método | Rota | Resposta |
| --- | --- | --- |
| GET | `/painel/resumo` | Processos, valor homologado, alta prioridade e revisão humana |
| GET | `/painel/distribuicao-scores` | Contagem por faixa, incluindo não analisados |
| GET | `/painel/evolucao-prioridade` | Contagem mensal segundo data e política documentadas |
| GET | `/processos` | Também atende ao ranking resumido do painel |

### Processos e itens

| Método | Rota | Responsabilidade |
| --- | --- | --- |
| GET | `/processos` | Busca, filtros, ordenação e paginação |
| GET | `/processos/resumo` | Contadores das abas antes da seleção da faixa de prioridade |
| GET | `/processos/{id}` | Dados gerais, valores, vínculos e situação da revisão |
| GET | `/processos/{id}/analises` | Resultados por modelo, score oficial e explicações |
| GET | `/processos/{id}/itens` | Itens paginados |
| GET | `/itens/{id}/comparacao` | Referência e exemplos de itens similares |
| GET | `/processos/{id}/documentos` | Fontes/documentos disponíveis |
| GET | `/processos/{id}/revisoes` | Histórico paginado |
| POST | `/processos/{id}/revisoes` | Nova revisão atribuída ao usuário autenticado |

Registrar rotas estáticas como `/processos/resumo` antes de `/{id}` ou garantir roteamento sem ambiguidade.

### Fornecedores

| Método | Rota | Responsabilidade |
| --- | --- | --- |
| GET | `/fornecedores/resumo` | Totais do recorte |
| GET | `/fornecedores` | Ranking paginado e busca |
| GET | `/fornecedores/{id}` | Identificação e indicadores |
| GET | `/fornecedores/{id}/concentracao` | Participação por órgão e HHI do universo correspondente |
| GET | `/processos?fornecedor_id={id}` | Processos relacionados |

### Relatórios

| Método | Rota | Responsabilidade |
| --- | --- | --- |
| POST | `/relatorios/previa` | Prévia estruturada, sem exigir persistir rascunho |
| POST | `/relatorios` | Solicitação persistida de PDF/CSV; retornar 202 e identificador |
| GET | `/relatorios/{id}` | Estado e metadados |
| GET | `/relatorios/{id}/download` | Arquivo autorizado ou URL temporária |

Seleção temporária de processos pode permanecer no cliente. Geração deve usar o mesmo serviço de dados da prévia. Se assíncrona, usar tarefas persistidas no PostgreSQL e um comando worker separado; não depender exclusivamente de tarefas em memória do servidor para trabalhos que precisam sobreviver a reinício. Uma fila externa não é necessária no início.

### Apoio e operação

| Método | Rota | Responsabilidade |
| --- | --- | --- |
| GET | `/orgaos` | Busca paginada para filtros |
| GET | `/modalidades` | Opções disponíveis |
| GET | `/analises/execucoes` | Execuções publicadas consultáveis |
| GET | `/base/status` | Cobertura, origem e última atualização bem-sucedida |
| GET | `/health` | Processo da API em execução |
| GET | `/ready` | Prontidão e conexão com o banco |

Não expor rotas públicas de treinamento ou coleta no MVP. Acionar por CLI/workflow com credenciais operacionais.

### Convenções

- Filtros: datas, órgão, fornecedor, modalidade, faixa de valor, score, prioridade, revisão e indicadores disponíveis.
- Declarar a data filtrada; padrão proposto nas telas: homologação. Data desconhecida não deve virar data de coleta.
- As consultas implementadas selecionam `base_id` e o devolvem nos metadados. `execucao_analise_id` e resolução da análise ativa são evolução planejada; não são parâmetros aceitos na etapa 06.
- Listagens implementadas: `pagina`, `tamanho_pagina` (máximo 100) e `ordenacao` validada, com ID como desempate estável.
- Resposta paginada implementada: `dados` e `meta`, contendo `base_id`, `total`, `pagina`, `tamanho_pagina` e `total_paginas`. Ver [contrato da API](API_CONSULTAS.md).
- Resumo das abas aplica os filtros comuns, mas não a própria aba; explicitar a regra.
- Retornar valores monetários como strings decimais no JSON; percentuais e scores com escala documentada.
- Ausência de score/comparação deve ter motivo e cobertura; não retornar zero como substituto.
- Erros consistentes: código, mensagem e identificador da requisição. Usar 404, 422 e demais status conforme o caso.
- Revisões e relatórios persistidos exigem autenticação e autorização. Resolver autor no servidor a partir da identidade validada.
- Consultas podem ser públicas se essa for a decisão do produto; não disponibilizar campos pessoais desnecessários.

Exemplo de listagem implementada, sem filtro ou ordenação por score:

```http
GET /api/v1/processos?homologacao_inicio=2026-01-01&homologacao_fim=2026-06-30&ordenacao=publicacao_desc&pagina=1&tamanho_pagina=20
```

## 10. Organização do código

```text
backend/
  app/
    main.py
    api/v1/          # Rotas por domínio
    schemas/         # Contratos Pydantic
    models/          # Mapeamento SQLAlchemy
    services/        # Regras de negócio e agregações
    repositories/    # Consultas e persistência
    core/            # Configuração, identidade e logs
    db/              # Sessões e conexão
  migrations/        # Alembic
  tests/
  pyproject.toml
  Dockerfile
collector/
  collector/         # CLI, downloads, manifestos e controle
  tests/
  pyproject.toml
  Dockerfile
ml/
  src/               # Preparação, treino, avaliação e inferência
  tests/
  pyproject.toml
infra/
  compose.yaml       # Desenvolvimento local
.github/workflows/   # Validação, coleta e publicação
```

Essa árvore é um destino proposto, não uma descrição dos arquivos já existentes. Escolher uma versão Python suportada pelos pacotes no início da implementação e fixar dependências de forma reproduzível. Evitar duplicar regras de banco entre serviços: manter um responsável pelo esquema e um contrato explícito de importação/publicação.

## 11. Infraestrutura e custo

Proposta acadêmica, sujeita à confirmação dos planos no provisionamento:

| Componente | Desenvolvimento | Hospedagem proposta |
| --- | --- | --- |
| PostgreSQL | Docker Compose | Supabase |
| API | Uvicorn/local ou Docker | Render |
| Coletor | CLI/local | GitHub Actions manual/agendado |
| Arquivos | Diretório local ignorado | Cloudflare R2, API compatível com S3 |
| Treinamento | Máquina local | Manter local inicialmente |
| Exportador | Comando worker local | Execução independente a definir |

Referências consultadas na discussão: Supabase Free com 500 MB de banco; R2 Standard com franquia de 10 GB-mês, além de limites de operações; Render Free com suspensão por inatividade; runners padrão do Actions gratuitos em repositórios públicos. Essas franquias não garantem custo zero para toda a base e podem mudar. Revalidar limites, meios de pagamento, suspensão e disponibilidade antes de contratar ou publicar.

- https://supabase.com/docs/guides/platform/billing-on-supabase
- https://developers.cloudflare.com/r2/pricing/
- https://render.com/docs/free
- https://github.com/features/actions

Não usar o disco efêmero do backend como persistência. PostgreSQL gratuito hospeda o recorte consultável, não necessariamente todo o histórico. Medir consumo incluindo índices, metadados e resultados por versão. Preservar versões completas em arquivos e definir retenção das versões publicadas no banco.

Se o limite gratuito for insuficiente, reduzir o recorte da demonstração ou manter processamento local, sem alegar cobertura maior que a efetivamente publicada. A execução de um worker de relatórios na nuvem precisa ser resolvida antes de prometer exportação assíncrona hospedada; o plano gratuito do backend não implica worker gratuito.

## 12. Configuração, segurança e observabilidade

Variáveis previstas, com nomes ajustáveis na implementação:

```text
DATABASE_URL
OBJECT_STORAGE_ENDPOINT
OBJECT_STORAGE_BUCKET
OBJECT_STORAGE_ACCESS_KEY_ID
OBJECT_STORAGE_SECRET_ACCESS_KEY
PORTAL_TRANSPARENCIA_TOKEN
AUTH_ISSUER
AUTH_AUDIENCE
LOG_LEVEL
CORS_ALLOWED_ORIGINS
```

O token do portal é necessário se os endpoints utilizados exigirem autenticação; não presumir que downloads de arquivos dependam dele. Segredos ficam em `.env` local ou secrets do provedor; `.env.example` contém apenas exemplos sem credenciais.

- Banco e bucket privados; acesso com privilégios mínimos e TLS nos serviços remotos.
- Autenticação validada no servidor e autorização para revisão, exportação e operações administrativas.
- CORS com origens configuradas; não registrar tokens ou credenciais nos logs.
- Logs estruturados com IDs de requisição, execução, arquivo e análise.
- Acompanhar duração, bytes, falhas, rejeições e contagens por etapa.
- Mostrar cobertura e data da última carga concluída, não apenas a última tentativa.
- Testar backup/restauração dos dados operacionais e manter política de retenção dos arquivos.

## 13. Validação necessária

Testes devem verificar comportamento relevante:

- Importar duas vezes o mesmo arquivo sem duplicar dados.
- Detectar versão corrigida e manter rastreabilidade.
- Retomar download/processamento falho sem publicar dados incompletos.
- Conferir dinheiro, unidades, datas, chaves e tratamento de ausências.
- Evitar duplicação de valores em agregações com múltiplos itens/participantes.
- Conferir paginação, filtros e consistência entre resumo, ranking e detalhe.
- Verificar HHI/participação com denominadores conhecidos.
- Reproduzir transformação e inferência de uma versão salva.
- Não confundir sem análise com baixa prioridade.
- Impedir revisão sem autorização e preservar histórico.
- Garantir que o relatório corresponda à base, execução e seleção registradas.

CI deve executar as verificações pertinentes aos componentes alterados. Fixtures pequenas e artificiais podem ser usadas nos testes, identificadas como tal; datasets reais grandes e artefatos não entram no Git.

## 14. Ordem de implementação

1. Diagnóstico real de uma competência e dicionário de dados.
2. Ambiente local PostgreSQL, configuração, saúde da API e migrações iniciais.
3. Coletor com persistência de originais, checksums, metadados e retomada.
4. Importação idempotente e preparação em Parquet.
5. Rotas de processos/itens com dados reais e cobertura explícita.
6. Baseline Isolation Forest, avaliação e inferência versionada.
7. Painel, fornecedores e explicações disponíveis.
8. Autenticação e revisão humana.
9. Prévia e exportação reprodutível de relatórios.
10. Publicação, automação de coleta e avaliação do Autoencoder.

Cada etapa deve funcionar com um recorte pequeno antes de ampliar o histórico. Não é necessário esperar o Autoencoder para disponibilizar resultados do baseline, desde que a versão e as limitações estejam identificadas.

## 15. Decisões pendentes

- Esquema real dos arquivos, chaves, cobertura temporal e disponibilidade de resultados/contratos/documentos.
- Expansão e validação do piloto de escritório (CATMAT 486054, histórico pretendido 10/2025–09/2026); tamanho do recorte hospedado.
- Critério de comparabilidade de itens e tratamento temporal dos preços.
- Método de normalização de score, limiares e composição do ranking.
- Política de referência para concentração e frequência de contratação.
- Provedor de autenticação, papéis e acesso público de leitura.
- Frequência e janela de atualização, retenção e backup.
- Bibliotecas de Autoencoder/explicabilidade e geração de PDF após validação técnica.
- Provisionamento dos provedores, orçamento, worker de relatórios e limites de execução.

Não transformar propostas deste documento em alegações de serviços já funcionando. Atualizar o contexto conforme decisões e diagnósticos forem confirmados.
