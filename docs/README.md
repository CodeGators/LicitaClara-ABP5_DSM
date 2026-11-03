# Documentação do Licita Clara

Começar pelo [plano de conclusão](PLANO_CONCLUSAO.md): estado, checklist, branches e aceitação. A [consolidação do repositório](CONSOLIDACAO_REPOSITORIO.md) registra a instalação e as verificações da etapa 01 desse plano.

## Contratos e operação atuais

- [API de consultas](API_CONSULTAS.md): rotas implementadas, parâmetros e semântica dos valores.
- [Contratos de itens/processos](CONTRATOS_ITENS_PROCESSOS.md): granularidade, IDs, resultados múltiplos e navegação da integração.
- [Frontend integrado](FRONTEND_CONSULTAS_REAIS.md): configuração, rotas reais/demonstrativas e testes no navegador.
- [Banco de dados](BANCO_DE_DADOS.md) e [diagramas](diagramas/README.md): 34 tabelas e quatro migrações.
- [Preparação e importação](PREPARACAO_E_IMPORTACAO.md) e [contratos entre componentes](CONTRATOS_BACKEND_E_DADOS.md).
- [Backend](../backend/README.md), [coletor](../collector/README.md), [ML](../ml/README.md) e [infraestrutura](../infra/README.md): instalação e comandos.

## Avaliação e histórico

- [Revisão e confirmação do núcleo](validacao_nucleo/REVISAO_E_CONFIRMACAO.md): conclusão mais recente sobre limitações dos ensaios.
- [Resultado inicial](validacao_nucleo/RESULTADO.md), [protocolo](validacao_nucleo/PROTOCOLO.md) e [guia independente](validacao_nucleo/GUIA_REVISAO_INDEPENDENTE.md).
- [Diagnóstico Compras.gov.br](DIAGNOSTICO_COMPRASGOV.md) e [complementos PNCP/propostas/contratos](DIAGNOSTICO_PARTICIPACOES_CONTRATOS_DOCUMENTOS.md).
- [Diagnóstico histórico do Portal da Transparência](DIAGNOSTICO_FONTE_LICITACOES.md): não representa a fonte operacional escolhida.
- [Contexto técnico](CONTEXTO_BACKEND_E_DADOS.md) e [checklist técnico histórico](TODO_IMPLEMENTACAO_BACKEND_E_DADOS.md): contêm propostas e notas datadas; sua numeração difere do plano de conclusão.

O PDF da proposta acadêmica é preservado como documento original; fonte efetiva e evolução do projeto estão nos documentos atuais. O arquivo `UML` da raiz é uma proposta conceitual histórica; o esquema efetivamente implementado está em `diagramas/`. Imagens em `prototipo/` e o HTML AuditaGov são referências demonstrativas, sem comprovar integração ou modelo publicado.

Consulte a [base e atributos analíticos](ATRIBUTOS_ANALITICOS.md) para aquisição histórica registrada, preparo versionado, critérios e testes da etapa 04.

A [avaliação versionada do Isolation Forest](AVALIACAO_ISOLATION_FOREST.md) consome o dataset analítico, compara regras e prepara revisão documental; utilidade ainda inconclusiva.
