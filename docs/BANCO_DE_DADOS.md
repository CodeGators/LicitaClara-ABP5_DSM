# Banco de dados — esquema atual

Modelo implementado em SQLAlchemy Core, com metadata compartilhada com Alembic.

[Diagrama UML interativo](diagramas/UML_BANCO.html) · [SVG](diagramas/UML_BANCO.svg) · [PlantUML completo](diagramas/UML_BANCO.puml).
Atualizado em 03/11/2026 (migração 0005); estrutura anterior verificada em 20/10/2026. Fonte principal: Compras.gov.br; complemento PNCP para anexos e assinatura contratual.

## Migrações e escopo

- `0001_coleta`: coleta, observações de arquivos, importações e versões de base.
- `0002_dominio`: identidades, snapshots, resultados, preços de referência, análises e auditoria; inclui atualização dos nomes de constraints compostas da revisão anterior.
- `0003_proveniencia`: unicidade de linha/importação/alvo, inclusive quando alvos opcionais são NULL, para evitar proveniência duplicada em retomadas.
- `0004_complementos`: propostas, identidades/snapshots de contratos, vínculos, documentos e novos alvos de proveniência.
- `0005_resultados`: score por resultado/fornecedor, FK composta resultado/item/base e unicidade preservando múltiplos vencedores.
- Há 34 tabelas da aplicação, além de `alembic_version`.
- Participações representam propostas de itens homologados, conforme cobertura diagnosticada; não garantem todos os participantes de qualquer processo. Ver [diagnóstico complementar e mapeamento](DIAGNOSTICO_PARTICIPACOES_CONTRATOS_DOCUMENTOS.md).
- Há metadados de coleta e snapshots de negócio reais do piloto da etapa 05. Os originais e Parquets permanecem fora do Git. Ver [preparação/importação](PREPARACAO_E_IMPORTACAO.md).

## Identidade, snapshots e correções

`processos`, `itens_processo` e `contratos` mantêm identidades estáveis. Campos de negócio ficam em `processos_versoes`, `itens_versoes` e `contratos_versoes`, únicos por identidade/base. Uma correção produz novo arquivo/importação/base e novos snapshots; análises e revisões continuam ligadas à versão anterior.

Cadastros globais identificam órgãos, fornecedores, modalidades e catálogo. O nome histórico do órgão fica no snapshot do processo; o nome do vencedor, no resultado. Descrições históricas ficam no item/referência e no original rastreável. A aplicação não deve depender de um cadastro global mutável para reproduzir o conteúdo de um relatório: o relatório tem seu próprio snapshot.

O importador trata repetição divergente da chave como conflito de resolução e registra a decisão/rejeição no manifesto, conforme a [etapa 05 implementada](PREPARACAO_E_IMPORTACAO.md). Não usar `ON CONFLICT DO UPDATE` em snapshots publicados nem escolher arbitrariamente uma linha do CSV como vencedora. A unicidade exige uma versão resolvida por base, não afirma que o CSV já é único.

Arquivos têm unicidade por fonte, módulo, competência e SHA-256. Observar novamente um arquivo cria vínculo com nova execução, não nova cópia. Mesmo conteúdo em outra origem/competência pode ser outro registro de aquisição. Importações são únicas por arquivo/versão de importador; recuperação reutiliza essa identidade.

`proveniencias_registros` associa registros a importações integrantes da base, com membro e número de linha (em CSV, ordinal lógico do registro, com cabeçalho = 1; campos multilinha não alteram o ordinal; em JSON, usar página/membro e ordinal positivo definidos pelo importador). Uma mesma entidade pode ter várias origens. Originais completos permanecem em objetos; não duplicar CSV inteiro em JSONB.

## Integridade

- UUIDs internos gerados pelo PostgreSQL; identificadores oficiais continuam texto.
- Dinheiro, quantidades e capacidade: `NUMERIC(28,8)`; scores normalizados: `NUMERIC(6,3)`; scores brutos/contribuições: `NUMERIC(30,12)`.
- Datas de negócio em `DATE`, instantes operacionais em `TIMESTAMP WITH TIME ZONE`.
- JSONB para parâmetros, atributos de origem, métodos e snapshots variáveis; relações centrais usam FKs.
- Campos desconhecidos ficam NULL; zero na fonte não é convertido automaticamente em desconhecido, nem ausência em zero.
- Resultados aceitam múltiplos fornecedores por item. Homologação, contrato e pagamento não são equivalentes.
- FKs compostas vinculam dados à mesma base e itens ao processo correto.
- Resultado de modelo exige modelo habilitado na execução e alvo coerente: processo sem item, ou item pertencente ao processo versionado indicado.
- `UNIQUE NULLS NOT DISTINCT` evita scores duplicados de processo mesmo com item NULL; exige PostgreSQL 15+, validado em PostgreSQL 17.
- Prioridade `nao_analisado` exige score NULL e motivo; demais prioridades exigem score entre 0 e 100. Limiares de prioridade continuam sendo política versionada da aplicação.
- Publicação ativa é única por nome. Serviço de publicação ainda deve validar execução concluída e lote completo, em transação, antes de ativar; o índice sozinho não valida o lote.
- Revisão exige avaliação correspondente ao processo versionado/execução. O estado atual será derivado do histórico, sem sobrescrever eventos.
- FKs não usam cascade de remoção de histórico. Papéis runtime não recebem DELETE/TRUNCATE nem UPDATE em snapshots, scores ou revisões.

## Índices de consulta

Foram criados índices para órgão/data de resultado, base/data de publicação, itens por snapshot de processo, fornecedor/data de resultado, catálogo/data de compra, execução/score, execução/prioridade/score e processo/data de revisão. PKs e constraints únicas também criam índices. Ajustar novos índices com consultas reais e `EXPLAIN`, sem indexar indiscriminadamente todas as colunas.

## Papéis de banco

| Papel NOLOGIN | Permissões principais |
| --- | --- |
| `licita_migrator` | USAGE/CREATE no schema; dono das tabelas criadas pelas migrações locais |
| `licita_api` | SELECT em tabelas da aplicação; INSERT em usuários/revisões/relatórios; UPDATE somente do nome do usuário |
| `licita_collector` | SELECT/INSERT em execuções, arquivos e observações; UPDATE somente de status/horários/erro da execução |
| `licita_processing` | SELECT nos dados; INSERT em importações, bases, identidades, snapshots e análises; UPDATE restrito ao acompanhamento operacional, publicação e geração de relatórios |

Grants são definidos por domínio, tabela e coluna em `licita_backend.db.permissions`. Novas migrações que adicionem tabelas precisam atualizar o contrato de permissões e reaplicar `apply`. Não há grants automáticos de escrita em qualquer tabela futura. O coletor não recebe leitura dos dados de processos nem acesso administrativo.

Os grupos são NOLOGIN. Logins locais separados herdam os grupos de API/coleta/processamento; senhas aleatórias ficam no `.env`, fora do Git. O login da API não é superusuário nem membro do papel de migração. `MIGRATION_DATABASE_URL` é reservada a comandos administrativos e não é carregada nas configurações HTTP. O banco de testes continua separado, com conexão administrativa própria para criar/remover schemas descartáveis.

Autorização dos usuários finais é responsabilidade da futura camada de autenticação; grupos de banco não substituem verificação de token/papel por usuário. Não há acesso direto do navegador ao PostgreSQL nesta arquitetura.

## Dicionário das tabelas

Legenda: campos NULL são explicitamente opcionais. Defaults são executados pelo banco. Uma linha abaixo não implica importação ou treinamento já implementados.


### `arquivos_coletados`

Uma versão de conteúdo por fonte/módulo/competência/SHA-256; conteúdo imutável.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `fonte` | `TEXT` | não | `—` |
| `modulo` | `TEXT` | não | `—` |
| `competencia` | `DATE` | não | `—` |
| `url_origem` | `TEXT` | não | `—` |
| `url_final` | `TEXT` | não | `—` |
| `sha256` | `TEXT` | não | `—` |
| `tamanho_bytes` | `BIGINT` | não | `—` |
| `chave_objeto` | `TEXT` | não | `—` |
| `etag` | `TEXT` | sim | `—` |
| `coletado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Unicidade: (chave_objeto); (fonte, modulo, competencia, sha256).

Validações: `extract(day from competencia) = 1`; `sha256 ~ '^[0-9a-f]{64}$'`; `tamanho_bytes >= 0`.

### `execucoes_coleta`

Um job e seu intervalo mensal; status operacional mutável.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `fonte` | `TEXT` | não | `—` |
| `modulo` | `TEXT` | não | `—` |
| `competencia_inicio` | `DATE` | não | `—` |
| `competencia_fim` | `DATE` | não | `—` |
| `status` | `TEXT` | não | `pendente` |
| `parametros` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |
| `iniciado_em` | `TIMESTAMP WITH TIME ZONE` | sim | `—` |
| `concluido_em` | `TIMESTAMP WITH TIME ZONE` | sim | `—` |
| `erro` | `TEXT` | sim | `—` |

Validações: `competencia_inicio <= competencia_fim`; `concluido_em IS NULL OR (iniciado_em IS NOT NULL AND concluido_em >= iniciado_em)`; `extract(day from competencia_inicio) = 1 AND extract(day from competencia_fim) = 1`; `status IN ('pendente', 'executando', 'concluido', 'parcial', 'falhou')`.

### `fornecedores`

Identificação textual e tipo; preserva CPF/CNPJ/identificador estrangeiro sem presumir CNPJ.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `fonte` | `TEXT` | não | `—` |
| `tipo_identificacao` | `TEXT` | não | `—` |
| `identificacao` | `TEXT` | não | `—` |
| `nome` | `TEXT` | não | `—` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Unicidade: (fonte, tipo_identificacao, identificacao).

### `itens_catalogo`

Identidade de um item em um catálogo, com código de grupo, classe e PDM quando conhecido.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `catalogo` | `TEXT` | não | `—` |
| `codigo` | `TEXT` | não | `—` |
| `descricao` | `TEXT` | não | `—` |
| `codigo_grupo` | `TEXT` | sim | `—` |
| `codigo_classe` | `TEXT` | sim | `—` |
| `codigo_pdm` | `TEXT` | sim | `—` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Unicidade: (catalogo, codigo).

### `modalidades`

Código e descrição por fonte; códigos de plataformas diferentes não são intercambiáveis.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `fonte` | `TEXT` | não | `—` |
| `codigo` | `TEXT` | não | `—` |
| `nome` | `TEXT` | não | `—` |

Unicidade: (fonte, codigo).

### `orgaos`

Identidade oficial do órgão na fonte; UG não é órgão e fica no snapshot do processo.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `fonte` | `TEXT` | não | `—` |
| `chave_oficial` | `TEXT` | não | `—` |
| `nome` | `TEXT` | não | `—` |
| `cnpj` | `TEXT` | sim | `—` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Unicidade: (fonte, chave_oficial).

### `processos`

Identidade estável por fonte e chave oficial; não contém score nem fornecedor único.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `fonte` | `TEXT` | não | `—` |
| `chave_oficial` | `TEXT` | não | `—` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Unicidade: (fonte, chave_oficial).

### `usuarios`

Identidade por issuer/subject e papel; não guarda senha de usuário final.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `issuer` | `TEXT` | não | `—` |
| `subject` | `TEXT` | não | `—` |
| `nome` | `TEXT` | não | `—` |
| `papel` | `TEXT` | não | `leitor` |
| `ativo` | `BOOLEAN` | não | `true` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Unicidade: (issuer, subject).

Validações: `papel IN ('leitor', 'revisor', 'administrador')`.

### `versoes_base`

Manifesto e recorte de uma base reproduzível; versão textual única.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `versao` | `TEXT` | não | `—` |
| `versao_transformador` | `TEXT` | não | `—` |
| `versao_codigo` | `TEXT` | não | `—` |
| `chave_manifesto` | `TEXT` | não | `—` |
| `sha256_manifesto` | `TEXT` | não | `—` |
| `periodo_inicio` | `DATE` | não | `—` |
| `periodo_fim` | `DATE` | não | `—` |
| `status` | `TEXT` | não | `preparando` |
| `recorte` | `JSONB` | não | `'{}'::jsonb` |
| `qualidade` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Unicidade: (versao).

Validações: `periodo_inicio <= periodo_fim`; `sha256_manifesto ~ '^[0-9a-f]{64}$'`; `status IN ('preparando', 'validada', 'rejeitada')`.

### `execucoes_analise`

Execução sobre uma base e política explícita de score; status mutável.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `versao_politica_score` | `TEXT` | não | `—` |
| `configuracao` | `JSONB` | não | `'{}'::jsonb` |
| `status` | `TEXT` | não | `pendente` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |
| `concluido_em` | `TIMESTAMP WITH TIME ZONE` | sim | `—` |
| `erro` | `TEXT` | sim | `—` |

Relações: (base_id) → versoes_base.id.

Unicidade: (id, base_id).

Validações: `status IN ('pendente', 'executando', 'concluida', 'falhou')`.

### `execucoes_arquivos`

Observação de um arquivo por uma execução; permite reutilizar o mesmo download.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `execucao_id` | `UUID` | não | `—` |
| `arquivo_id` | `UUID` | não | `—` |
| `observado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (arquivo_id) → arquivos_coletados.id; (execucao_id) → execucoes_coleta.id.

### `importacoes`

Uma tentativa lógica por arquivo e versão do importador, retomável pelo status.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `arquivo_id` | `UUID` | não | `—` |
| `versao_importador` | `TEXT` | não | `—` |
| `status` | `TEXT` | não | `pendente` |
| `aceitos` | `BIGINT` | não | `0` |
| `rejeitados` | `BIGINT` | não | `0` |
| `diagnostico` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |
| `concluido_em` | `TIMESTAMP WITH TIME ZONE` | sim | `—` |

Relações: (arquivo_id) → arquivos_coletados.id.

Unicidade: (arquivo_id, versao_importador).

Validações: `aceitos >= 0 AND rejeitados >= 0`; `status IN ('pendente', 'executando', 'concluido', 'parcial', 'falhou')`.

### `itens_processo`

Identidade estável do item dentro de um processo.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `processo_id` | `UUID` | não | `—` |
| `chave_oficial` | `TEXT` | não | `—` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (processo_id) → processos.id.

Unicidade: (id, processo_id); (processo_id, chave_oficial).

### `processos_versoes`

Snapshot do processo em uma base, com órgão, UG, valores e datas disponíveis.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `processo_id` | `UUID` | não | `—` |
| `orgao_id` | `UUID` | não | `—` |
| `modalidade_id` | `UUID` | sim | `—` |
| `orgao_nome` | `TEXT` | não | `—` |
| `codigo_unidade` | `TEXT` | não | `—` |
| `nome_unidade` | `TEXT` | sim | `—` |
| `numero_compra` | `TEXT` | não | `—` |
| `numero_controle_pncp` | `TEXT` | sim | `—` |
| `numero_processo` | `TEXT` | sim | `—` |
| `ano` | `INTEGER` | não | `—` |
| `objeto` | `TEXT` | não | `—` |
| `situacao` | `TEXT` | não | `—` |
| `data_publicacao` | `DATE` | sim | `—` |
| `data_abertura` | `DATE` | sim | `—` |
| `data_resultado` | `DATE` | sim | `—` |
| `valor_estimado` | `NUMERIC(28, 8)` | sim | `—` |
| `valor_homologado` | `NUMERIC(28, 8)` | sim | `—` |
| `orcamento_sigiloso` | `BOOLEAN` | sim | `—` |
| `atributos_origem` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (orgao_id) → orgaos.id; (processo_id) → processos.id; (modalidade_id) → modalidades.id; (base_id) → versoes_base.id.

Unicidade: (id, base_id); (id, processo_id, base_id); (processo_id, base_id).

Validações: `valor_estimado IS NULL OR valor_estimado >= 0`; `valor_homologado IS NULL OR valor_homologado >= 0`.

### `referencias_precos`

Referência do módulo de pesquisa de preços, preservando catálogo e embalagem.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `catalogo_id` | `UUID` | não | `—` |
| `fornecedor_id` | `UUID` | sim | `—` |
| `fonte` | `TEXT` | não | `—` |
| `chave_origem` | `TEXT` | não | `—` |
| `id_compra_oficial` | `TEXT` | não | `—` |
| `id_item_oficial` | `TEXT` | não | `—` |
| `descricao` | `TEXT` | não | `—` |
| `unidade_fornecimento` | `TEXT` | sim | `—` |
| `sigla_unidade_fornecimento` | `TEXT` | sim | `—` |
| `capacidade_fornecimento` | `NUMERIC(28, 8)` | sim | `—` |
| `sigla_medida` | `TEXT` | sim | `—` |
| `quantidade` | `NUMERIC(28, 8)` | sim | `—` |
| `preco_unitario` | `NUMERIC(28, 8)` | não | `—` |
| `data_compra` | `DATE` | não | `—` |
| `atributos_origem` | `JSONB` | não | `'{}'::jsonb` |

Relações: (fornecedor_id) → fornecedores.id; (catalogo_id) → itens_catalogo.id; (base_id) → versoes_base.id.

Unicidade: (base_id, fonte, chave_origem); (id, base_id).

Validações: `capacidade_fornecimento IS NULL OR capacidade_fornecimento >= 0`; `preco_unitario > 0`.

### `versoes_modelo`

Artefato imutável, parâmetros, pré-processamento e base de treinamento.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_treino_id` | `UUID` | não | `—` |
| `algoritmo` | `TEXT` | não | `—` |
| `versao` | `TEXT` | não | `—` |
| `versao_codigo` | `TEXT` | não | `—` |
| `chave_artefato` | `TEXT` | não | `—` |
| `sha256_artefato` | `TEXT` | não | `—` |
| `parametros` | `JSONB` | não | `'{}'::jsonb` |
| `metricas` | `JSONB` | não | `'{}'::jsonb` |
| `preprocessamento` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (base_treino_id) → versoes_base.id.

Unicidade: (algoritmo, versao).

Validações: `sha256_artefato ~ '^[0-9a-f]{64}$'`.

### `avaliacoes_processo`

Score oficial e prioridade por processo versionado/execução, distinto de não analisado.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `execucao_id` | `UUID` | não | `—` |
| `processo_versao_id` | `UUID` | não | `—` |
| `score` | `NUMERIC(6, 3)` | sim | `—` |
| `prioridade` | `TEXT` | não | `—` |
| `motivo_indisponibilidade` | `TEXT` | sim | `—` |
| `politica` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (execucao_id, base_id) → execucoes_analise.id, execucoes_analise.base_id; (processo_versao_id, base_id) → processos_versoes.id, processos_versoes.base_id.

Unicidade: (processo_versao_id, execucao_id).

Validações: `(prioridade = 'nao_analisado' AND score IS NULL AND motivo_indisponibilidade IS NOT NULL) OR (prioridade <> 'nao_analisado' AND score IS NOT NULL AND score BETWEEN 0 AND 100)`; `prioridade IN ('nao_analisado', 'baixa', 'media', 'alta')`.

### `base_importacoes`

Relação N:N entre bases e importações que sustentam seus registros.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `base_id` | `UUID` | não | `—` |
| `importacao_id` | `UUID` | não | `—` |

Relações: (importacao_id) → importacoes.id; (base_id) → versoes_base.id.

### `execucoes_modelos`

Modelos habilitados para a execução, com FK composta usada nos resultados.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `execucao_id` | `UUID` | não | `—` |
| `modelo_id` | `UUID` | não | `—` |

Relações: (execucao_id) → execucoes_analise.id; (modelo_id) → versoes_modelo.id.

### `itens_versoes`

Snapshot do item em uma base; FK composta impede item de outro processo/base.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `item_id` | `UUID` | não | `—` |
| `processo_id` | `UUID` | não | `—` |
| `processo_versao_id` | `UUID` | não | `—` |
| `catalogo_id` | `UUID` | sim | `—` |
| `numero_item` | `TEXT` | não | `—` |
| `descricao` | `TEXT` | não | `—` |
| `unidade_medida` | `TEXT` | sim | `—` |
| `quantidade` | `NUMERIC(28, 8)` | sim | `—` |
| `valor_unitario_estimado` | `NUMERIC(28, 8)` | sim | `—` |
| `orcamento_sigiloso` | `BOOLEAN` | sim | `—` |
| `atributos_origem` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (catalogo_id) → itens_catalogo.id; (base_id) → versoes_base.id; (item_id, processo_id) → itens_processo.id, itens_processo.processo_id; (processo_versao_id, processo_id, base_id) → processos_versoes.id, processos_versoes.processo_id, processos_versoes.base_id.

Unicidade: (id, base_id); (id, processo_versao_id, base_id); (item_id, base_id).

Validações: `quantidade IS NULL OR quantidade >= 0`; `valor_unitario_estimado IS NULL OR valor_unitario_estimado >= 0`.

### `publicacoes_analise`

Histórico de publicação; índice parcial permite uma ativa por nome de painel.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `nome` | `TEXT` | não | `—` |
| `base_id` | `UUID` | não | `—` |
| `execucao_id` | `UUID` | não | `—` |
| `ativa` | `BOOLEAN` | não | `true` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (execucao_id, base_id) → execucoes_analise.id, execucoes_analise.base_id.

Unicidade: (nome, execucao_id).

### `relatorios`

Solicitação e snapshot de exportação, sempre associados à mesma base da análise.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `usuario_id` | `UUID` | não | `—` |
| `base_id` | `UUID` | não | `—` |
| `execucao_id` | `UUID` | não | `—` |
| `titulo` | `TEXT` | não | `—` |
| `formato` | `TEXT` | não | `—` |
| `parametros` | `JSONB` | não | `'{}'::jsonb` |
| `snapshot` | `JSONB` | não | `'{}'::jsonb` |
| `status` | `TEXT` | não | `pendente` |
| `chave_objeto` | `TEXT` | sim | `—` |
| `sha256` | `TEXT` | sim | `—` |
| `erro` | `TEXT` | sim | `—` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |
| `concluido_em` | `TIMESTAMP WITH TIME ZONE` | sim | `—` |

Relações: (usuario_id) → usuarios.id; (execucao_id, base_id) → execucoes_analise.id, execucoes_analise.base_id.

Validações: `formato IN ('pdf', 'csv')`; `status IN ('pendente', 'processando', 'concluido', 'falhou')`.

### `comparacoes_itens`

Referência calculada de um item na execução: grupo, período, mediana e amostra.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `execucao_id` | `UUID` | não | `—` |
| `item_versao_id` | `UUID` | não | `—` |
| `versao_criterio` | `TEXT` | não | `—` |
| `grupo_comparavel` | `JSONB` | não | `'{}'::jsonb` |
| `periodo_inicio` | `DATE` | não | `—` |
| `periodo_fim` | `DATE` | não | `—` |
| `tamanho_amostra` | `INTEGER` | não | `—` |
| `mediana` | `NUMERIC(28, 8)` | não | `—` |
| `limite_inferior` | `NUMERIC(28, 8)` | sim | `—` |
| `limite_superior` | `NUMERIC(28, 8)` | sim | `—` |

Relações: (execucao_id, base_id) → execucoes_analise.id, execucoes_analise.base_id; (item_versao_id, base_id) → itens_versoes.id, itens_versoes.base_id.

Unicidade: (execucao_id, item_versao_id); (id, base_id).

Validações: `limite_inferior IS NULL OR limite_superior IS NULL OR limite_inferior <= limite_superior`; `periodo_inicio <= periodo_fim`; `tamanho_amostra >= 1 AND mediana > 0`.

### `resultados_itens`

Resultado por snapshot de item, fornecedor e sequencial; aceita múltiplos vencedores.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `item_versao_id` | `UUID` | não | `—` |
| `fornecedor_id` | `UUID` | não | `—` |
| `fornecedor_nome` | `TEXT` | não | `—` |
| `sequencial_resultado` | `INTEGER` | não | `—` |
| `chave_origem` | `TEXT` | não | `—` |
| `situacao` | `TEXT` | não | `—` |
| `cancelado` | `BOOLEAN` | não | `false` |
| `quantidade_homologada` | `NUMERIC(28, 8)` | sim | `—` |
| `valor_unitario_homologado` | `NUMERIC(28, 8)` | sim | `—` |
| `valor_total_homologado` | `NUMERIC(28, 8)` | sim | `—` |
| `data_resultado` | `DATE` | sim | `—` |
| `atributos_origem` | `JSONB` | não | `'{}'::jsonb` |

Relações: (base_id) → versoes_base.id; (item_versao_id, base_id) → itens_versoes.id, itens_versoes.base_id; (fornecedor_id) → fornecedores.id.

Unicidade: (id, base_id); (id, item_versao_id, base_id); (base_id, item_versao_id, fornecedor_id, sequencial_resultado).

Validações: `quantidade_homologada IS NULL OR quantidade_homologada >= 0`; `valor_total_homologado IS NULL OR valor_total_homologado >= 0`; `valor_unitario_homologado IS NULL OR valor_unitario_homologado >= 0`.

### `resultados_modelo`

Score por modelo/execução/alvo; snapshot de processo obrigatório e item e resultado opcionais conforme tipo de alvo; a inferência experimental usa resultado por fornecedor.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `execucao_id` | `UUID` | não | `—` |
| `modelo_id` | `UUID` | não | `—` |
| `processo_versao_id` | `UUID` | não | `—` |
| `item_versao_id` | `UUID` | sim | `—` |
| `resultado_item_id` | `UUID` | sim | `—` |
| `tipo_alvo` | `TEXT` | não | `—` |
| `score_bruto` | `NUMERIC(30, 12)` | não | `—` |
| `score_normalizado` | `NUMERIC(6, 3)` | não | `—` |
| `versao_normalizacao` | `TEXT` | não | `—` |
| `atributos` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (resultado_item_id, item_versao_id, base_id) → resultados_itens.id, resultados_itens.item_versao_id, resultados_itens.base_id; (item_versao_id, processo_versao_id, base_id) → itens_versoes.id, itens_versoes.processo_versao_id, itens_versoes.base_id; (execucao_id, base_id) → execucoes_analise.id, execucoes_analise.base_id; (processo_versao_id, base_id) → processos_versoes.id, processos_versoes.base_id; (execucao_id, modelo_id) → execucoes_modelos.execucao_id, execucoes_modelos.modelo_id.

Unicidade: (execucao_id, modelo_id, processo_versao_id, item_versao_id, resultado_item_id), com NULLs não distintos.

Validações: `tipo_alvo` em `processo`, `item`, `resultado`; processo não tem item/resultado, item exige item e resultado nulo, resultado exige ambos. `score_normalizado BETWEEN 0 AND 100`. O índice experimental é CDF do treino, não risco validado; ver [política e execução](INFERENCIA_PUBLICACAO.md).

### `revisoes`

Evento de revisão humana sobre snapshot e avaliação existentes; append-only para runtime.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `usuario_id` | `UUID` | não | `—` |
| `processo_versao_id` | `UUID` | não | `—` |
| `execucao_id` | `UUID` | não | `—` |
| `status` | `TEXT` | não | `—` |
| `observacao` | `TEXT` | não | `—` |
| `conclusao` | `TEXT` | sim | `—` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (processo_versao_id) → processos_versoes.id; (processo_versao_id, execucao_id) → avaliacoes_processo.processo_versao_id, avaliacoes_processo.execucao_id; (usuario_id) → usuarios.id.

Validações: `status IN ('a_revisar', 'em_analise', 'revisado')`.

### `comparacoes_referencias`

Referências de preço que compõem a comparação; FKs impedem misturar bases.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `base_id` | `UUID` | não | `—` |
| `comparacao_id` | `UUID` | não | `—` |
| `referencia_id` | `UUID` | não | `—` |

Relações: (referencia_id, base_id) → referencias_precos.id, referencias_precos.base_id; (comparacao_id, base_id) → comparacoes_itens.id, comparacoes_itens.base_id.

### `fatores_sinalizacao`

Explicação identificada por atributo/método/versão; contribuição pode ser negativa ou ausente.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `resultado_modelo_id` | `UUID` | não | `—` |
| `atributo` | `TEXT` | não | `—` |
| `metodo` | `TEXT` | não | `—` |
| `versao_metodo` | `TEXT` | não | `—` |
| `observado` | `JSONB` | não | `'{}'::jsonb` |
| `referencia` | `JSONB` | não | `'{}'::jsonb` |
| `contribuicao` | `NUMERIC(30, 12)` | sim | `—` |
| `descricao` | `TEXT` | não | `—` |

Relações: (resultado_modelo_id) → resultados_modelo.id.

Unicidade: (resultado_modelo_id, atributo, metodo).

### `proveniencias_registros`

Vínculo entre importação integrante da base e exatamente um alvo versionado. Unicidade usa NULLS NOT DISTINCT.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `importacao_id` | `UUID` | não | `—` |
| `membro_arquivo` | `TEXT` | não | `—` |
| `numero_linha` | `BIGINT` | não | `—` |
| `processo_versao_id` | `UUID` | sim | `—` |
| `item_versao_id` | `UUID` | sim | `—` |
| `resultado_item_id` | `UUID` | sim | `—` |
| `referencia_preco_id` | `UUID` | sim | `—` |
| `participacao_id` | `UUID` | sim | `—` |
| `contrato_versao_id` | `UUID` | sim | `—` |
| `contrato_processo_id` | `UUID` | sim | `—` |
| `documento_id` | `UUID` | sim | `—` |

Relações: (base_id, importacao_id) → base_importacoes.base_id, base_importacoes.importacao_id; (contrato_processo_id, base_id) → contratos_processos.id, contratos_processos.base_id; (contrato_versao_id, base_id) → contratos_versoes.id, contratos_versoes.base_id; (documento_id, base_id) → documentos.id, documentos.base_id; (item_versao_id, base_id) → itens_versoes.id, itens_versoes.base_id; (participacao_id, base_id) → participacoes.id, participacoes.base_id; (processo_versao_id, base_id) → processos_versoes.id, processos_versoes.base_id; (referencia_preco_id, base_id) → referencias_precos.id, referencias_precos.base_id; (resultado_item_id, base_id) → resultados_itens.id, resultados_itens.base_id.

Unicidade: (base_id, importacao_id, membro_arquivo, numero_linha, processo_versao_id, item_versao_id, resultado_item_id, referencia_preco_id, participacao_id, contrato_versao_id, contrato_processo_id, documento_id).

Validações: `num_nonnulls(processo_versao_id, item_versao_id, resultado_item_id, referencia_preco_id, participacao_id, contrato_versao_id, contrato_processo_id, documento_id) = 1`; `numero_linha >= 1`.

### `participacoes`

Uma proposta oficial por fonte/base/ID. Podem existir várias propostas do mesmo participante para um item; ausência não representa zero participantes.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `processo_versao_id` | `UUID` | não | `—` |
| `item_versao_id` | `UUID` | não | `—` |
| `fornecedor_id` | `UUID` | sim | `—` |
| `fonte` | `TEXT` | não | `—` |
| `chave_origem` | `TEXT` | não | `—` |
| `identificacao_participante` | `TEXT` | sim | `—` |
| `nome_participante` | `TEXT` | sim | `—` |
| `valor_proposta` | `NUMERIC(28, 8)` | sim | `—` |
| `valor_lance` | `NUMERIC(28, 8)` | sim | `—` |
| `valor_negociado` | `NUMERIC(28, 8)` | sim | `—` |
| `classificacao` | `INTEGER` | sim | `—` |
| `situacao_proposta` | `TEXT` | sim | `—` |
| `situacao_item` | `TEXT` | sim | `—` |
| `homologado` | `BOOLEAN` | sim | `—` |
| `incluido_na_origem_em` | `TIMESTAMP WITHOUT TIME ZONE` | sim | `—` |
| `alterado_na_origem_em` | `TIMESTAMP WITHOUT TIME ZONE` | sim | `—` |
| `atributos_origem` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (base_id) → versoes_base.id; (fornecedor_id) → fornecedores.id; (item_versao_id, processo_versao_id, base_id) → itens_versoes.id, itens_versoes.processo_versao_id, itens_versoes.base_id; (processo_versao_id, base_id) → processos_versoes.id, processos_versoes.base_id.

Unicidade: (base_id, fonte, chave_origem); (id, base_id).

Validações: `classificacao IS NULL OR classificacao >= 1`; `valor_lance IS NULL OR valor_lance >= 0`; `valor_negociado IS NULL OR valor_negociado >= 0`; `valor_proposta IS NULL OR valor_proposta >= 0`.

### `contratos`

Identidade estável por fonte/chave oficial; priorizar controle PNCP e não apenas número local.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `fonte` | `TEXT` | não | `—` |
| `chave_oficial` | `TEXT` | não | `—` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |


Unicidade: (fonte, chave_oficial).

### `contratos_versoes`

Snapshot contratual por base. Assinatura é distinta de vigência e depende do detalhe PNCP; valores ausentes permanecem NULL.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `contrato_id` | `UUID` | não | `—` |
| `orgao_id` | `UUID` | sim | `—` |
| `fornecedor_id` | `UUID` | sim | `—` |
| `numero_contrato` | `TEXT` | não | `—` |
| `numero_controle_pncp` | `TEXT` | sim | `—` |
| `codigo_unidade_gestora` | `TEXT` | sim | `—` |
| `fornecedor_nome` | `TEXT` | sim | `—` |
| `objeto` | `TEXT` | sim | `—` |
| `data_assinatura` | `DATE` | sim | `—` |
| `data_vigencia_inicio` | `DATE` | sim | `—` |
| `data_vigencia_fim` | `DATE` | sim | `—` |
| `valor_global` | `NUMERIC(28, 8)` | sim | `—` |
| `valor_acumulado` | `NUMERIC(28, 8)` | sim | `—` |
| `excluido` | `BOOLEAN` | sim | `—` |
| `atributos_origem` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (base_id) → versoes_base.id; (contrato_id) → contratos.id; (fornecedor_id) → fornecedores.id; (orgao_id) → orgaos.id.

Unicidade: (contrato_id, base_id); (id, base_id).

Validações: `valor_acumulado IS NULL OR valor_acumulado >= 0`; `valor_global IS NULL OR valor_global >= 0`.

### `contratos_processos`

Vínculo verificável entre snapshots de contrato e processo na mesma base, sem limitar a relação a um-para-um.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `contrato_versao_id` | `UUID` | não | `—` |
| `processo_versao_id` | `UUID` | não | `—` |
| `tipo_chave_vinculo` | `TEXT` | não | `—` |
| `chave_vinculo` | `TEXT` | não | `—` |
| `atributos_origem` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (base_id) → versoes_base.id; (contrato_versao_id, base_id) → contratos_versoes.id, contratos_versoes.base_id; (processo_versao_id, base_id) → processos_versoes.id, processos_versoes.base_id.

Unicidade: (base_id, contrato_versao_id, processo_versao_id); (id, base_id).

Validações: `tipo_chave_vinculo IN ('idCompra', 'numeroControlePncpCompra')`.

### `documentos`

Metadados de um documento com exatamente um pai (processo ou contrato) da mesma base. Dados do binário são todos NULL ou preenchidos juntos.

| Coluna | Tipo PostgreSQL | NULL | Default |
| --- | --- | --- | --- |
| `id` | `UUID` | não | `gen_random_uuid()` |
| `base_id` | `UUID` | não | `—` |
| `processo_versao_id` | `UUID` | sim | `—` |
| `contrato_versao_id` | `UUID` | sim | `—` |
| `fonte` | `TEXT` | não | `—` |
| `chave_origem` | `TEXT` | não | `—` |
| `sequencial_documento` | `INTEGER` | não | `—` |
| `tipo_codigo` | `TEXT` | sim | `—` |
| `tipo_nome` | `TEXT` | sim | `—` |
| `titulo` | `TEXT` | sim | `—` |
| `url_origem` | `TEXT` | não | `—` |
| `ativo` | `BOOLEAN` | sim | `—` |
| `publicado_na_origem_em` | `TIMESTAMP WITHOUT TIME ZONE` | sim | `—` |
| `chave_objeto` | `TEXT` | sim | `—` |
| `sha256` | `TEXT` | sim | `—` |
| `tamanho_bytes` | `BIGINT` | sim | `—` |
| `atributos_origem` | `JSONB` | não | `'{}'::jsonb` |
| `criado_em` | `TIMESTAMP WITH TIME ZONE` | não | `now()` |

Relações: (base_id) → versoes_base.id; (contrato_versao_id, base_id) → contratos_versoes.id, contratos_versoes.base_id; (processo_versao_id, base_id) → processos_versoes.id, processos_versoes.base_id.

Unicidade: (base_id, fonte, chave_origem); (id, base_id).

Validações: `num_nonnulls(chave_objeto, sha256, tamanho_bytes) IN (0, 3)`; `num_nonnulls(processo_versao_id, contrato_versao_id) = 1`; `sequencial_documento >= 1`; `sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'`; `tamanho_bytes IS NULL OR tamanho_bytes >= 0`.

Na etapa 07, `versoes_base` também registra datasets de modelagem em objetos (`recorte.tipo=treino_modelo`), excluídos das consultas operacionais. Essa linha é a base real referenciada por `versoes_modelo.base_treino_id`; não representa processos/itens importados nem cobertura adicional de consultas.
