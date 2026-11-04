# Preparação e modelagem

O pacote `licita-ml` implementa preparação/importação de dados, avaliação versionada do Isolation Forest e comparação com Autoencoder sobre os atributos analíticos. Os ensaios históricos separados permanecem preservados. A inferência experimental em lote está implementada com registro de treino e publicação versionada; a utilidade do ranking continua inconclusiva por ausência de revisão independente. Veja a avaliação versionada (documentação local) e o histórico dos ensaios (documentação local).

Na raiz do repositório, com PostgreSQL migrado e `PROCESSING_DATABASE_URL` restrita já configurada:

```bash
uv sync --locked --all-packages
uv run --locked --package licita-ml licita-ml preparar --inicio 2026-09-01 --fim 2026-09-30 --catalogo 486054
```

Sem `--arquivos`, seleciona a versão mais recentemente **observada** de cada módulo/competência no período. Uma nova observação de conteúdo antigo pode torná-lo a versão selecionada; hashes e IDs são congelados no manifesto. Para reproduzir uma seleção histórica, informe todos os IDs originais:

```bash
uv run --locked --package licita-ml licita-ml preparar --inicio 2026-09-01 --fim 2026-09-30 --catalogo 486054 --arquivos UUID_1 UUID_2 UUID_3 UUID_4
```

O exemplo representa quatro ou mais IDs reais; se houve aquisição complementar, inclua também esses arquivos. A seleção exige `compra`, `compra_item`, `item_resultado` e `material`. Propostas e envelopes JSON oficiais são opcionais e têm cobertura registrada. Não há acesso a endpoints HTTP neste comando; a aquisição é responsabilidade do coletor.

Repetir período, catálogo, seleção e código reutiliza a base, conferindo os hashes do manifesto, dos Parquets e das rejeições. Uma alteração na origem ou no código gera outra base e mantém o histórico. O status `validada` confirma integridade técnica e reconciliação; não afirma que a base está pronta para treinamento.

Veja regras, comandos e evidências da etapa 05 (documentação local).

## Configuração

- `PROCESSING_DATABASE_URL`: exclusivamente o login de processamento, sem credencial administrativa.
- `STORAGE_BACKEND`, `STORAGE_ROOT` e variáveis de objetos: mesmos adaptadores compartilhados do coletor. Disco local está configurado. Para S3/R2, instalar o extra `s3` do workspace e configurar bucket/credenciais conforme README do coletor; não houve teste com conta remota.
- `PROCESSING_WORK_DIR=data/processing`: relatórios locais de execução, fora do Git.
- `PROCESSING_BATCH_SIZE=500`: tamanho dos lotes SQL, entre 1 e 2.000.
- `PROCESSING_MAX_FILE_BYTES=104857600`: limite compactado/JSON por objeto.
- `PROCESSING_MAX_UNCOMPRESSED_BYTES=2147483648`: limite de expansão de ZIP.

O processamento lê os arquivos em streaming e mantém apenas o recorte selecionado em memória. Há limite de 20 mil itens e 20 mil linhas selecionadas por execução, antes da deduplicação. Para volumes maiores, dividir o recorte e planejar evolução para staging em disco; não ampliar o limite por suposição sobre a memória disponível.

Há um lock PostgreSQL global de preparação para serializar publicação e criação de identidades. Importações operacionais ficam separadas da transação de dados; todos os snapshots, vínculos, proveniências e validação da base são confirmados juntos. Uma falha deixa importações marcadas como `falhou`, sem base parcial publicada; repetir a mesma seleção retoma sem duplicar registros.

## Ensaio do núcleo de ML

```bash
uv sync --locked --all-packages --extra validation
uv run --locked --all-packages --extra validation python -m licita_ml.experiments.core --offline
```

O cache histórico fica em `data/validacao_nucleo/`. Sem `--offline`, consultas ausentes podem ser adquiridas na API oficial; caches existentes são conferidos por URL/hash. Os artefatos e planilhas de revisão ficam fora do Git. O ensaio não escreve no PostgreSQL nem publica scores; a categoria original insuficiente continua separada da coorte alternativa. Consulte o protocolo (documentação local) antes de interpretar as métricas. Usar outro `--saida` preserva execuções anteriores; planilhas com pareceres preenchidos não são sobrescritas.

## Revisão documental e confirmação

A revisão aprofundada (documentação local) encontrou divergências de especificação apesar de valores corroborados. O ranking não está aprovado para publicação como prioridade de auditoria. O ensaio corrigido exige resultado até o corte; a replicação histórica e a consulta de outubro são reportadas separadamente.

Com o extra `validation` instalado, na raiz do repositório:

```bash
uv run --locked --all-packages --extra validation python -m licita_ml.review_validation
uv run --locked --all-packages --extra validation python -m licita_ml.review_validation.documents
uv run --locked --all-packages --extra validation python -m licita_ml.review_validation.confirmation
uv run --locked --all-packages --extra validation python -m licita_ml.review_validation.replication
uv run --locked --all-packages --extra validation python -m licita_ml.review_validation.result_dates
uv run --locked --all-packages --extra validation python -m licita_ml.review_validation.report
```

Esses comandos usam snapshots existentes conferidos por hash; consultas ausentes acessam as fontes oficiais. Não sobrescrever os caches para simular dados novos. O módulo `documents` requer `pdftotext` (Poppler) no sistema. Downloads têm limite de 16 MiB por documento, transferências por partes, prazo global de 45 segundos e quatro tarefas concorrentes. ZIPs são lidos em memória, com até 100 membros, 64 MiB de expansão total e até seis PDFs por documento; nomes internos não viram caminhos locais. Formatos não suportados e falhas permanecem registrados. Nem todos os anexos puderam ser obtidos.

Os quatro modelos originais não são alterados pelos novos ensaios; os novos artefatos têm diretórios próprios. O dossiê independente não contém flags de algoritmo nem achados da conferência automatizada e se recusa a sobrescrever pareceres preenchidos. Nenhum desses comandos publica resultados no PostgreSQL.

Consulte a base e atributos analíticos (documentação local) para aquisição histórica registrada, preparo versionado, critérios e testes da etapa 04.

A avaliação versionada do Isolation Forest (documentação local) consome o dataset analítico, compara regras e prepara revisão documental; utilidade ainda inconclusiva.

A comparação Autoencoder/Isolation Forest (documentação local) usa a mesma coorte e regras de referência, sem vencedor validado ou publicação de scores.

A inferência/publicação versionada (documentação local) registra treino/modelos, cobertura por resultado e canal experimental explícito; o piloto atual tem zero scores elegíveis.

## Recursos e relatórios

Os protocolos e as regras necessários à execução são distribuídos em
`src/licita_ml/resources/`, incluindo `exclusoes_v1.json` para o argumento
`licita-ml atributos --exclusoes ml/src/licita_ml/resources/exclusoes_v1.json`.
A pasta local `docs/` não é necessária à execução e não é versionada.
Os relatórios dos experimentos históricos são escritos em
`data/validacao_nucleo/relatorios/`; executar o experimento original antes
de comandos de revisão que dependam de seus resultados. Artefatos, dados
e modelos continuam fora do Git.
