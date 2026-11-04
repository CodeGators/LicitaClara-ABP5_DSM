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

## Diagnóstico offline dos arquivos

Para medir preenchimento, identidades, datas, números, vínculos e categorias dos
quatro ZIPs mensais antes de preparar a base analítica:

```bash
uv run --locked --all-packages --extra validation python -m licita_ml.diagnostics \
  --entrada data/diagnostico/compras/2026-09 \
  --inventario-raiz data \
  --saida data/diagnostico/ml01/conferencia.json
```

A saída deve ser um caminho novo. O comando preserva as fontes, usa SQLite
temporário em disco e não acessa rede, banco operacional ou modelos.
Correspondência de IDs/campos e grupos exploratórios não comprovam
elegibilidade analítica. O relatório é local, em `data/`, fora do Git.

## Base organizada offline

```bash
uv run --locked --all-packages --extra validation python -m licita_ml.organized \
  --entrada data/diagnostico/compras/2026-09 \
  --saida data/organizados
```

A saída indica um diretório `base=FINGERPRINT`, com Parquet e CSV de compras,
itens, resultados, referências, enriquecimento dos itens, vínculos, linhas de
origem e rejeições. `dicionario.json` descreve campos e convenções;
`manifesto.json` registra fontes, hashes, contagens e política. A repetição
confere a integridade e retorna `reutilizada: true`. Uma fonte ou regra nova gera
outra versão. Artefatos existentes divergentes são recusados, sem sobrescrita.

O comando opera nos ZIPs locais e usa SQLite temporário em disco; não importa no
PostgreSQL nem executa ML. `--historico CAMINHO.csv.zip ...` permite acrescentar
arquivos de materiais de outros meses quando disponíveis. Cópias com o mesmo
conteúdo são lidas uma única vez. Os originais e as versões anteriores são
preservados; a pasta final só é publicada depois da conciliação.

As versões usam atualização do registro; referências usam atualização do item e
depois da compra. Empates com atributos divergentes, datas de versão inválidas
ou fusos incompatíveis ficam em rejeições. Linhas que repetem os mesmos atributos
da entidade, mas diferem em colunas de entidades filhas, são classificadas como
`projecao_equivalente`; fornecedores continuam separados nos resultados. Todas
as linhas têm destinação auditável em `linhas`.

IDs são texto, valores são Decimal/decimal128(28,8), datas de evento são date32 e
instantes conservam o offset conhecido em texto ISO. CSV usa UTF-8, `;`, ponto
decimal e vazio para ausência. Ao importar em planilha, configurar IDs como
texto para preservar zeros. `linha` identifica o ordinal do registro CSV,
considerando cabeçalho=1; não é a linha física de um campo com quebras de linha.

Catálogo/descrição vindos da pesquisa aparecem em `enriquecimento_itens`, sem
alterar os campos originais. Vínculo de IDs ou coincidência de preço/quantidade
não comprova comparabilidade nem elegibilidade. Unidade, embalagem, situação,
corte temporal e cobertura precisam de validação na construção dos atributos.
Não há mediana, ajuste de escala, divisão temporal ou score nesta entrega.

```bash
uv run --locked --all-packages --extra validation pytest ml/tests/test_organized.py -q
```

## Partições temporais e atributos

```bash
uv run --locked --all-packages --extra validation python -m licita_ml.temporal \
  --base data/organizados/base=12ee7c68c6d4d7c37a937fd2f6d1c0d02b3a46f27db46ed26908aa7508c38261 \
  --treino-inicio 2025-07-01
uv run --locked --all-packages --extra validation pytest ml/tests/test_temporal.py -q
```

O diretório de entrada é explícito e deve conter uma base organizada íntegra.
Os padrões são treino outubro–dezembro/2025, avaliação julho–agosto/2026 e
aplicação setembro/2026. As seis datas podem ser informadas pelos argumentos
`--treino-inicio`, `--treino-fim`, `--avaliacao-inicio`, `--avaliacao-fim`,
`--aplicacao-inicio` e `--aplicacao-fim`, sempre em ISO. O recorte versionado é
classe 7510 ou os catálogos 486054, 486374 e 637468. Alterar cortes gera outra
versão, não reescreve a anterior.

A saída contém auditoria de referências, grupos e medianas de treino,
matrizes de treino/avaliação/aplicação de referências e auditoria/matriz de
resultados operacionais. CSV e Parquet têm as mesmas contagens. `contrato.json`
define as únicas entradas dos modelos: `log_preco_mediana` e `log_quantidade`.
IDs de observação, grupo e compra são rastreabilidade: não passam ao modelo.
Treinar separadamente por grupo; escalas aprendidas ficam para a etapa de treino,
ajustadas apenas nos dados de treino. Este comando não executa modelos.

As referências são agrupadas por catálogo, descrição detalhada normalizada,
sigla da unidade de fornecimento, capacidade e medida. Não inferir equivalência
entre produtos ou converter caixas em unidades. A mediana usa somente treino
com resultado conhecido até o corte. Compra observada em partição anterior é
excluída das posteriores, inclusive quando o produto anterior está fora do
recorte. Datas inconsistentes, grupos insuficientes e exclusões documentais
continuam na auditoria com motivos; não viram zero.

Os mínimos técnicos são 100 referências/20 compras no treino, 30 referências/dez
compras na avaliação, três órgãos e três fornecedores no treino, até cinco
referências por compra/grupo/partição e até 10% das referências do treino por
compra. Exige-se variação de preço e quantidade para comparar os dois modelos.
Esses limites são operacionais do piloto, não garantias estatísticas universais.

Somente grupos tecnicamente elegíveis produzem matrizes liberadas para treino.
O lote inicial do trimestre terminou como `insuficiente_para_modelagem` e foi
preservado com matrizes vazias e auditoria. Com treino ampliado para julho–dezembro/2025, o grupo 39b446b8528b8da9 (CATMAT 425226, grampo 26/6 em caixa de 5.000 UN)
atingiu 173 referências de treino e 44 de avaliação. Há três referências de
aplicação; os resultados operacionais ainda não têm todos os vínculos necessários.
O estado `apto_avaliacao_tecnica` libera estudo dos modelos nesse grupo, sem
aprovar utilidade de auditoria ou os demais produtos. Grupos insuficientes ficam
na auditoria, com atributos exploratórios quando há referência mínima de
20 registros/dez compras. Não treinar só porque o CSV existe nem reduzir os
critérios para obter um resultado.

Aplicação em referências e em resultados operacionais são observações distintas.
Resultados precisam de cadeia compra/item resolvida, situação confirmada, ausência
de cancelamento/moeda estrangeira, vínculo único por campos e especificação/unidade
compatíveis. Nome e sigla só são aceitos quando fornecidos explicitamente na mesma
referência vinculada. Isso não aprova comparabilidade documental nem utilidade de
auditoria. Snapshots revisados após os cortes são sinalizados; o ensaio não é
um backtest estritamente ponto no tempo. Não há score de processo ou fraude.

## Treino e comparação sobre as matrizes temporais

```bash
uv run --locked --all-packages --extra validation python -m licita_ml.training treinar \
  --base data/atributos_temporais/base=623b9e7c18c853ff1d7b28d0d6b4938f9f4fc95b837c41bda8cb075d1a27fe7a
uv run --locked --all-packages --extra validation pytest ml/tests/test_training.py -q
```

O pacote confere a integridade temporal, reconcilia IDs, compras, datas, medianas
e atributos antes do fit e consome somente treino/avaliação. As referências de
aplicação ficam reservadas. O protocolo executável é
`src/licita_ml/resources/PROTOCOLO_TREINO_TEMPORAL_V1.json`: IF com variantes
preço e preço/quantidade, grade 200/500 árvores × 64/256 amostras × cinco sementes,
âncora predefinida 200 árvores/min(256,n)/semente 42; AE 2→1→2 com cinco sementes
e âncora 42, StandardScaler ajustado apenas no treino. Não escolhe parâmetros
ou vencedor pelo ranking do holdout.

Resultados em `data/treinamento_temporal/execucao=FINGERPRINT`, com sete modelos
(dois IF âncora e cinco AE), scores brutos de treino/avaliação em CSV e Parquet,
comparação com regras unilateral/bilateral, estabilidade, convergência,
sensibilidade sintética, contexto dos casos e hashes. Os CSVs incluem preço,
quantidade, unidade/capacidade da fonte e mediana. Os scores são de anomalia,
não porcentagem de fraude; magnitudes de IF e AE não são comparáveis diretamente.
As parcelas do erro AE não são causas nem contribuições do IF.

A repetição verifica e reutiliza sem retreinar ou desserializar modelos salvos.
Na geração, somente artefatos recém-criados pelo processo são carregados para
verificar replay. Escalas, modelos, IDs e versões ficam associados ao dataset.
Saída divergente não é sobrescrita; o manifesto só é publicado ao final. Nenhum
score de aplicação, registro SQL ou publicação na API é feito por esse comando.

Planilhas cegas originais ficam na execução imutável. Cópias editáveis são
criadas em `data/revisoes_ml04/FINGERPRINT/GRUPO/`, sem sobrescrever respostas
existentes. As planilhas omitem método, ranking e score e começam como pendentes.
Amostra: 20 casos de treino, união dos top-k dos métodos/regras e até três
controles de avaliação. A conferência técnica automatizada não é parecer humano.

```bash
uv run --locked --all-packages --extra validation python -m licita_ml.training revisar \
  --execucao CAMINHO_DA_EXECUCAO --grupo GRUPO \
  --treino COPIA_REVISAO_TREINO.csv --avaliacao COPIA_REVISAO_AVALIACAO.csv \
  --natureza interna
```

A conferência exige IDs/contexto originais e evidência/autor/data para pareceres
preenchidos. `independente_declarada` registra uma declaração, sem comprovar
independência pelo software. Nenhum parecer aprova utilidade/publicação ou escolhe
vencedor automaticamente. O resultado atual é comparação técnica concluída com
utilidade inconclusiva por revisão pendente; os dois algoritmos passaram na
estabilidade deste grupo, sem prova de superioridade ou eficácia de auditoria.

## Inferência dos modelos temporais e integração operacional

Executar na raiz do monorepositório, com `.env`, PostgreSQL migrado e o extra
`validation`. `inferir-temporal` exige um diretório **privado e confiável** gerado
pela ML-04 e o SHA-256 de seu manifesto; não recebe modelos por HTTP.

```bash
uv run --locked --all-packages --extra validation licita-ml inferir-temporal \
  --treino CAMINHO_DA_EXECUCAO_ML04 --sha256-treino SHA256_DO_MANIFESTO \
  --dataset CAMINHO_DA_BASE_TEMPORAL --resultado-ate 2026-10-31
```

Sem `--base-id`, exporta apenas inferência nas referências: manifesto, CSV e
Parquet privados em `data/objects/inferencia/referencias=FINGERPRINT/` quando
usado armazenamento local. O CSV e o Parquet preservam decimais/IDs como texto;
ambos são exportações para inspeção, não matrizes de treino. Manifesto contém
cobertura e exclusões, scores brutos, CDF de treino e parcelas AE. Não são
resultados de licitação e não entram artificialmente nas tabelas operacionais.

Com `--base-id UUID_OPERACIONAL`, reconcilia o snapshot SQL com as referências
e persiste modelos, dataset de treino, execução, scores, cobertura e parcelas
em transação. O comando não publica automaticamente. Repetir a mesma seleção
reconcilia e retorna `reutilizada: true`, sem duplicar resultados.

```bash
uv run --locked --all-packages --extra validation licita-ml inferir-temporal \
  --treino CAMINHO_DA_EXECUCAO_ML04 --sha256-treino SHA256_DO_MANIFESTO \
  --dataset CAMINHO_DA_BASE_TEMPORAL --resultado-ate 2026-10-31 \
  --base-id UUID_OPERACIONAL
uv run --locked --all-packages --extra validation licita-ml publicar-experimental \
  --execucao UUID_DA_EXECUCAO_CONCLUIDA
uv run --locked --all-packages --extra validation pytest ml/tests/test_temporal_inference.py -q
```

`--resultado-ate` é opcional: sem ele, vale o corte original da aplicação ML-03.
Um corte posterior somente libera referências cujo **único** impedimento era
resultado posterior ao corte antigo. O lote registra os motivos originais e
reutiliza a mediana/escala/modelo congelados. Não altera treino, avaliação ou
arquivos ML-03/04; não implica backtest ponto no tempo nem aprovação de utilidade.

Para complementar compras conhecidas, sem varrer todo o catálogo ou baixar
novos lotes mensais, o coletor aceita até 20 IDs oficiais explícitos:

```bash
uv run --locked --all-packages licita-collector coletar-ids \
  --competencia 2026-09 --compras ID_COMPRA_1 ID_COMPRA_2
```

Coleta compra, itens e resultados pela API oficial, com originais e proveniência
registrados. `--arquivos compra_api itens_api resultados_api` restringe módulos.
São arquivos complementares para a preparação operacional já existente, não
substitutos do histórico de treino. Versões diferentes podem mudar a base gerada.

O ensaio local reconciliou **dois resultados reais** de outubro/2026 (mesma
especificação de grampo, caixa de 5.000 UN), gerando quatro scores: IF e AE para
cada resultado. Os três casos pontuados apenas nas referências de setembro
apresentaram datas de resultado divergentes no PNCP e ficaram sem score SQL.
A base complementar contém 20 itens/19 processos/nove resultados; cobertura de
40 pares alvo/modelo: quatro analisados, 22 sem resultado, oito sem modelo do
grupo e seis com data divergente. Esses motivos contam pares, não compras.

A API existente `/api/v1/analises` consulta a publicação experimental e os
resultados por base/execução explícitas. Valores 0–100 são posições na distribuição
de treino, não probabilidade de fraude nem faixas de prioridade. Não há score
por processo nesta entrega. A base antiga e suas publicações permanecem acessíveis.

## Síntese experimental por processo (ML-06)

Após aplicar a migração `0006_sinteses`, a inferência de itens pode originar uma
nova execução com sínteses por processo e por modelo, preservando a anterior:

```bash
uv run --locked --all-packages --extra validation licita-ml sintetizar-processos \
  --execucao-origem UUID_DA_INFERENCIA_DE_ITENS
uv run --locked --all-packages --extra validation licita-ml publicar-experimental \
  --execucao UUID_DA_NOVA_EXECUCAO
```

Não retreina nem carrega modelos. Copia os scores e fatores verificados da origem,
reconcilia seus vínculos, verifica os snapshots de itens/resultados API já
vinculados à base e persiste tudo em transação. Não faz novas requisições HTTP.
Repetir a mesma origem/código/política/fontes reutiliza a execução concluída.

A política `POLITICA_SINTESE_PROCESSO_V1.json` define uma média hierárquica:
primeiro média dos índices dos resultados ativos do mesmo item; depois média
dos itens do processo. Cada item tem peso igual, independentemente da quantidade
de vencedores, preço, quantidade física ou valor global. Não combina algoritmos
nem modelos/grupos diferentes. A média é um índice descritivo, não o percentil
do processo, risco de fraude ou evidência de utilidade validada. Pode diluir um
sinal raro; os sinais e pesos permanecem disponíveis para inspeção.

**Score integral só existe quando o universo oficial no snapshot foi confirmado
e todos os seus itens têm todos os resultados ativos analisados pelo modelo.**
CSV filtrado por catálogo e quantidade de itens importados não comprovam esse
universo. Itens com várias versões na API contam uma vez; versões conflitantes
impedem confirmar o universo. Itens sem resultados continuam sem índice.

Com cobertura parcial, o score integral é nulo. A média dos sinais disponíveis
é outra medida, acompanhada de fontes, contagens, pesos e IDs dos resultados.
Quando o universo é confirmado, limites determinísticos indicam a amplitude da
média sob a hipótese de índices comparáveis entre 0 e 100 para os alvos ausentes.
Não imputam valores, não são intervalo de confiança e não garantem aplicabilidade
do modelo a outras categorias. Sem universo confirmado, limites também são nulos.
Prioridade de auditoria continua separada e indisponível, sem faixas arbitrárias.

A API publicada expõe `/api/v1/analises/execucoes/{id}/processos` e
`/api/v1/analises/execucoes/{id}/processos/{processo_id}`, com `base_id` explícito
e `modelo_id` opcional. Filtros de itens não recalculam a síntese da compra.
Versões antigas retornam `sem_sintese`; a publicação anterior continua acessível.
O detalhe do processo no frontend apresenta cobertura e links para os sinais.

No ensaio real, 19 processos geraram 38 sínteses, sem scores integrais: quatro
sínteses têm sinais (dois processos × dois modelos), com cobertura de um item
entre 78 e de um entre 221 nas fontes oficiais. Os quatro scores de resultados
ML-05 foram preservados. Os demais processos não recebem zeros artificiais.
O caminho de score integral é testado em dados controlados com cobertura completa;
isso não é evidência de cobertura integral nas licitações reais ou validação humana.

```bash
uv run --locked --all-packages --extra validation pytest \
  ml/tests/test_process_scores.py ml/tests/test_process_universe.py \
  ml/tests/test_process_inference.py -q
```

## Catálogo integral e revisão do agrupamento dos itens

```bash
uv run --locked --all-packages python -m licita_ml.catalog \
  --base CAMINHO_DA_BASE_ORGANIZADA --saida data/catalogo_itens
uv run --locked --all-packages --extra validation pytest \
  ml/tests/test_catalog_rules.py ml/tests/test_catalog_pipeline.py -q
```

Percorre todas as referências, itens e resultados consolidados da base, sem o
filtro anterior de materiais de escritório. Usa as fontes já organizadas, com
hashes conferidos, sem baixar dados, importar no SQL ou modificar modelos.
Novos CSVs devem ser incorporados primeiro com `licita_ml.organized`; cópias de
arquivos e versões repetidas não devem virar novos exemplos de treino.

Agrupa por CATMAT, especificações do catálogo **e** detalhada, unidade de
fornecimento, capacidade e medida. Normaliza acentos/caixa, espaçamento entre
número e unidade e ordem dos atributos nomeados. Uma cópia exata dos atributos
do catálogo também pode omitir dois-pontos ou espaços no nome do atributo;
todos os valores devem coincidir, sem sobras ou atributos ausentes. Preserva texto livre, cores,
números, dimensões, qualificadores, atributos repetidos e símbolos significativos
como µ e ≥. Não usa busca por palavra-chave ou similaridade de texto para unir
produtos automaticamente. UN/UNIDADE e CX/CAIXA são aliases explícitos; preços
e quantidades por caixa continuam por caixa. Não converte CX em UN. Unidades
simples KG/G/L/ML/M/M2/M3 também não exigem capacidade de embalagem; KG e G,
por exemplo, permanecem grupos distintos e nenhum preço é convertido.

Saída versionada/imutável em `data/catalogo_itens/catalogo=FINGERPRINT/`, CSV e
Parquet, manifesto de hashes e protocolo:

- `produtos`: inventário dos códigos de catálogo. Não calcula média global que
  misture especificações ou embalagens do mesmo CATMAT.
- `grupos`: especificação canônica, contagens, média, mediana e faixa de preços
  por grupo, com estatísticas de treino separadas e diagnóstico de fragmentação.
- `candidatos_estudo`: grupos com pelo menos 100 referências de treino e 30 de
  avaliação válidas quanto a datas, ordenados por contagens. É triagem; não
  comprova diversidade, estabilidade, comparabilidade comercial ou aptidão de ML.
- `variantes`: descrições originais e contagens para conferir cada reunião.
- `observacoes`: cada referência individual, com preço, quantidade, datas,
  fornecedor, compra/item, grupo novo/anterior e fonte/ordinal. Não substituir
  essas observações por uma única média para treinar o Forest.
- `itens_catalogados` e `resultados_catalogados`: todos os registros nativos,
  incluindo serviços, ausências e vínculos candidatos por chave. Preço estimado
  e homologado são campos distintos; resultados não são somados às referências
  que podem representar a mesma compra. Código ausente não é inventado.

Médias são aritméticas por observação e medianas são descritivas, com Decimal e
sem remoção automática de outliers. Preços não positivos e suspensões documentais
não entram nessas estatísticas. A estatística do período inteiro **não pode ser
usada como baseline do treino**. Médias/medianas da janela de treino são apenas
diagnósticas: a próxima preparação deve validar suficiência/diversidade e manter
a separação temporal. Os snapshots não constituem backtest ponto no tempo.

Os modelos atuais continuam com duas entradas numéricas: log(preço/mediana de
treino) e log(1+quantidade). Catálogo, descrição, cor e embalagem organizam os
grupos e a rastreabilidade; não são novas colunas contínuas no Forest. Corrigir
os grupos melhora comparabilidade/aproveitamento, não reduz automaticamente o
número de atributos nem o número de árvores. O catálogo não treina/publica modelos
ou aprova automaticamente comparabilidade comercial. Repetição confere e reutiliza;
saída corrompida ou incompleta é rejeitada, sem sobrescrever evidências anteriores.


Para refinar um catálogo previamente gerado pela mesma base e protocolo,
`--catalogo-anterior CAMINHO_DO_CATALOGO` reaproveita as observações verificadas
por hash e recalcula os grupos/estatísticas. O manifesto registra o catálogo
anterior; base, janelas temporais ou regras documentais diferentes são rejeitadas.
Essa opção só reconhece a cópia literal dos atributos do catálogo com formatação
diferente. A geração completa e o refinamento produzem as mesmas tabelas; suas
identidades de execução diferem por registrarem o caminho de preparação.

## Treino por grupos do catálogo integral

```bash
uv run --locked --all-packages python -m licita_ml.grouped preparar \
  --base CAMINHO_BASE_ORGANIZADA --catalogo CAMINHO_CATALOGO
uv run --locked --all-packages python -m licita_ml.grouped treinar \
  --preparacao CAMINHO_PREPARACAO --processos 2
uv run --locked --all-packages --extra validation pytest ml/tests/test_grouped_temporal.py -q
```

A preparação verifica a origem e usa os 207 candidatos por contagens do catálogo,
sem limitar a materiais de escritório. Reaplica os mínimos de compras, órgãos,
fornecedores, variação, concentração e cortes da política temporal. Só prosseguem
descrições estruturadas nas duas fontes; livros sem obra/edição/ISBN e acessórios
sem modelo confirmado ficam para revisão. Essa triagem não aprova comparabilidade
documental de todos os registros. Preços extremos não são removidos automaticamente.

Todos os grupos elegíveis são ordenados por assinatura e divididos em lotes de
até 20, sem selecionar os melhores resultados de avaliação. Cada lote mantém o
contrato temporal validado pelo motor de treino existente: duas entradas, mediana
e escala só do treino, 45 ajustes por grupo e modelos/avaliações rastreáveis.
Compras que apareceram em partição anterior continuam excluídas, mesmo em outro
grupo. Os resultados operacionais são reconciliados separadamente na inferência;
as tabelas de alvos SQL da preparação permanecem vazias, sem substituí-los por
referências de preço. A aplicação não participa do ajuste.

O orquestrador admite até três processos independentes, com uma thread numérica
por processo. Execuções completas são verificadas/reutilizadas; lotes já concluídos
podem ser reaproveitados após falha, sem sobrescrever revisões preenchidas. A lista
de grupos, os impedimentos e os modelos estáveis são registrados. Estabilidade
não comprova utilidade, fraude, acurácia ou superioridade entre IF e Autoencoder.
