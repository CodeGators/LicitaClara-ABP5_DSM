# Backend — FastAPI

## Medida original do Isolation Forest

A aplicação usa **`-score_samples`**, já persistido em `score_bruto`, como
`medida_if`: valores de 0 a 1, com valores maiores indicando maior anomalia.
A apresentação usa quatro casas decimais; rankings e cálculos usam a precisão
persistida. Não é uma probabilidade, nem uma multiplicação por 100.

Painel, itens, fornecedores, licitações, detalhe e relatórios usam essa medida.
O modo automático seleciona somente IF; não substitui sua ausência pelo erro
do Autoencoder. O erro de reconstrução continua separado nos relatórios e na API,
em outra escala, sem entrar no ranking IF.
A média por licitação é apenas descritiva: modelos de grupos diferentes não
possuem calibração comum de gravidade e a média não é uma análise própria da compra.

Não é necessário retreinar, reimportar ou migrar o banco. Os percentis antigos
permanecem no armazenamento histórico para compatibilidade, mas não alimentam
os valores, a ordenação, o histograma ou as exportações da aplicação.
Novas execuções de ML ainda preservam o campo legado para o contrato de armazenamento;
a leitura operacional utiliza o valor bruto tanto para execuções antigas quanto novas.

A API pública passa a usar `medida_if`, `medida_if_media`, `maior_medida_if`,
`itens_com_medida_if` e `itens_sem_medida_if`. O histograma tem intervalos de 0,1
entre 0 e 1. Resultados sem IF ficam sem medida, sem zero imputado.
O parâmetro de URL `ordenacao=indice_desc` é mantido e agora ordena pela medida bruta.
As páginas `/demonstracao/*` continuam como protótipo fictício, separado dos dados reais.


API FastAPI com consultas versionadas de processos, itens e documentos,
análises experimentais e relatórios PDF/CSV. Para uma instalação nova e os
scripts de dados/treinamento, siga o [guia da equipe](../scripts/README.md).
As referências a pilotos e etapas abaixo registram a evolução do backend; a
cobertura atual depende da base e da execução selecionadas.

A etapa 02 do plano de conclusão acrescenta `GET /api/v1/itens` e `GET /api/v1/itens/{item_id}`. Esses endpoints retornam uma linha por item, contexto do processo e resultados por fornecedor, sem modificar as sete rotas originais. Ver contratos de itens/processos e testes manuais (documentação local).

A etapa 03 integra a interface e acrescenta `GET /api/v1/fornecedores/opcoes` para o filtro, com busca/paginação e nome histórico da base. Configuração e testes do frontend integrado (documentação local).

## Instalar e executar

Usar Python 3.12.x, Docker Compose e uv 0.13.2. Executar a partir da raiz do repositório:

```bash
# Instalar uv 0.13.2, se necessário: https://docs.astral.sh/uv/getting-started/installation/
cp .env.example .env  # somente se .env ainda não existir
uv sync --locked --all-packages --extra validation
docker compose --env-file .env -f infra/compose.yaml up -d --wait
uv run --locked --package licita-backend python -m licita_backend.db.permissions bootstrap
uv run --locked --package licita-backend alembic -x role=licita_migrator upgrade head
uv run --locked --package licita-backend python -m licita_backend.db.permissions apply
uv run --locked --package licita-backend python -m licita_backend.db.permissions local-logins
uv run --locked --package licita-backend uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Nesta máquina, uv 0.13.2 foi instalado em `~/.local/bin/uv` e está disponível no PATH. As senhas do exemplo são apenas para desenvolvimento. Nesta máquina, um `.env` ignorado pelo Git foi criado com senha local aleatória. Não substituí-lo pelo exemplo se o volume já estiver inicializado: mudar variáveis não altera a senha persistida no PostgreSQL.

A configuração lê `.env` relativo ao diretório atual. Para outro diretório de execução, fornecer variáveis de ambiente explicitamente. Não há banco alternativo SQLite ou fallback silencioso.

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- `GET /api/v1/health`: processo ativo, sem depender do banco.
- `GET /api/v1/ready`: consulta PostgreSQL; 200 disponível, 503 indisponível.
- OpenAPI: http://127.0.0.1:8000/openapi.json

`--no-access-log` evita duplicar os logs HTTP JSON com o access log padrão do Uvicorn. Logs de inicialização do servidor continuam no formato do Uvicorn. A base local importada pode ser consultada em `/api/v1/base/status` e `/api/v1/processos`.

## Testes

Os testes sem integração não precisam de PostgreSQL:

```bash
uv run --locked --all-packages --extra validation ruff check .
uv run --locked --all-packages --extra validation ruff format --check .
uv run --locked --all-packages --extra validation pytest -m 'not integration'
```

Para integração, criar um banco separado (o comando falha se já existir; nesse caso basta seguir):

```bash
docker compose --env-file .env -f infra/compose.yaml exec -T postgres sh -c 'createdb -U "$POSTGRES_USER" licita_clara_test'
uv run --locked --all-packages --extra validation pytest
```

`TEST_DATABASE_URL` deve apontar para banco descartável com nome terminado em `_test`. Se ausente, os testes de integração são pulados; para validar a etapa completa, eles devem executar. As tabelas temporárias de teste têm nomes exclusivos e são removidas ao terminar. Nunca apontar os testes para o banco da aplicação.

Configuração, propriedade do esquema, sessões e contratos: CONTRATOS_BACKEND_E_DADOS.md (documentação local).

## Migrações e papéis

Revisão atual: `0006_sinteses` (inclui análise por resultado da `0005_resultados`). São 35 tabelas; propostas, contratos e anexos estão descritos no diagnóstico complementar (documentação local).

`MIGRATION_DATABASE_URL` é uma conexão administrativa separada de `DATABASE_URL`. Não é usada pela aplicação HTTP. Os comandos de instalação acima criam os grupos NOLOGIN, aplicam migrações sob o papel proprietário, concedem permissões e geram logins locais de API/coleta/processamento.

Nesta máquina, o `.env` já foi atualizado com as conexões separadas e as quatro revisões estão aplicadas. O comando `local-logins` é idempotente quando os logins e suas credenciais estão no `.env`; não imprime senhas nem cria credenciais remotas. Para nuvem, o operador deverá provisionar logins e grants com as permissões disponibilizadas pelo provedor.

Verificar estado, sem alterar o banco:

```bash
uv run --locked --package licita-backend alembic -x role=licita_migrator current
uv run --locked --package licita-backend alembic -x role=licita_migrator check
uv run --locked --package licita-backend alembic history
```

Após mudar as credenciais, reiniciar a API para que ela leia o `.env`. `upgrade head` aplica apenas revisões pendentes. Não editar revisões já compartilhadas: criar uma nova migração para alterações posteriores. Downgrades removem estruturas e devem ficar restritos a bancos descartáveis ou a recuperação planejada; os testes exercitam downgrade em schemas próprios no banco `_test`, sem tocar no banco da aplicação.

O dicionário implementado, chaves, snapshots e permissões estão em BANCO_DE_DADOS.md (documentação local). Propostas, contratos e documentos já possuem diagnóstico e esquema na revisão `0004_complementos`; cobertura real e vínculos dependem do recorte importado. O piloto atual não tem propostas ou contratos vinculáveis.

## Consultas de dados reais

As consultas de leitura estão disponíveis no Swagger e contrato da API (documentação local). Aceitam seleção de base por UUID; sem seleção explícita, usam a base validada mais recente. A interface real fixa essa base na URL para as requisições relacionadas. Para preservar as dependências do ensaio ML no mesmo ambiente, executar:

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Os scores continuam nulos com análise `nao_publicada`. Valores globais do processo e dos itens do recorte são campos distintos; consultar a documentação antes de usá-los em totais ou filtros.

A inferência/publicação versionada (documentação local) registra treino/modelos, cobertura por resultado e canal experimental explícito; o piloto atual tem zero scores elegíveis.

O painel, ranking e fornecedores reais (documentação local) compartilha base/execução/modelo e filtros; leia as definições de universo, valores, HHI e indisponibilidade antes de interpretar os indicadores.

Sínteses experimentais por processo/modelo ficam em `sinteses_processo_modelo`,
separadas da prioridade de auditoria. As consultas publicadas
`/api/v1/analises/execucoes/{id}/processos` e `/processos/{processo_id}` exigem
`base_id` explícito e aceitam `modelo_id`. Score integral permanece nulo se
o universo oficial ou a cobertura forem insuficientes; a média observada é
um campo distinto. Não há faixas de fraude ou combinação de algoritmos.

## Relatórios públicos por processo

Sem login, filas ou gravação em tabelas de usuários. A prévia e os arquivos usam o
mesmo serviço de dados; bases, resultados cancelados e algoritmos são explícitos.

- `GET /api/v1/relatorios/processos/{processo_id}/previa?base_id=UUID`
- `GET /api/v1/relatorios/processos/{processo_id}/arquivo?base_id=UUID&formato=pdf&snapshot_sha256=HASH`

Ambas aceitam `execucao_id=UUID` de uma análise publicada e `titulo` (até 120
caracteres). Sem execução, geram relatório de dados sem pontuações; não escolhem
outra análise silenciosamente. O hash retornado na prévia deve acompanhar o
arquivo, junto da mesma seleção/título. Divergência retorna 409 para atualizar a
prévia. Publicar outra execução não troca a selecionada, inclusive publicações
históricas. O SHA identifica o conteúdo do snapshot, não os bytes do PDF.

PDF usa [ReportLab/Platypus](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/)
com fontes TrueType distribuídas pelo pacote, texto escapado e paginação A4.
O download é um arquivo PDF, não a impressão do navegador. CSV usa UTF-8 com BOM,
separador ponto e vírgula e campos entre aspas; textos que possam iniciar fórmulas
recebem apóstrofo de proteção. Importar identificadores como texto na planilha.

CSV tem uma linha por resultado/modelo; resultados sem score e itens sem resultado
continuam presentes. Valores repetidos entre modelos não devem ser somados.
Cancelados são identificados; totais de síntese do recorte seguem as consultas
existentes (resultados ativos, sem transformar valores ausentes em zero).
Limites: 200 itens, mil resultados, duas mil pontuações e snapshot de até 2 MiB.
Excesso retorna 413, sem truncar silenciosamente. Não são buscados anexos ou URLs
externos durante a geração. Não há armazenamento de solicitações/identidades;
a tabela antiga `relatorios` não é utilizada por esse fluxo público.

Validação específica:

```bash
uv run --locked --all-packages --extra validation pytest backend/tests/test_reports.py -q
```

### Resumo de licitações

`GET /api/v1/visao/licitacoes` recebe os mesmos parâmetros de base, execução,
modelo, filtros e paginação da visão de itens. Agrupa todos os itens importados
por compra, incluindo compras importadas sem itens. A medida IF média é a média
aritmética das medidas brutas disponíveis por item, com precisão de 12 casas;
o índice do item é o máximo dos resultados não cancelados no modelo escolhido
ou no modelo preferencial de seu grupo. Algoritmos não são somados e itens sem
índice não entram no denominador. Um índice real igual a zero entra na média.

Busca, fornecedor, período e valores selecionam compras inteiras: não reduzem
os itens usados no cálculo. O filtro de valor usa o total global homologado na
origem. `valor_homologado` e `valores_itens_importados` são medidas distintas.
`itens_com_medida_if`, `itens_importados`, cobertura parcial dos resultados e
`maior_medida_if` acompanham a média; `itens_oficiais` fica nulo porque a integridade
da importação não foi confirmada. A média é descritiva, sem prioridade validada.

A seleção múltipla `sinalizacao` aceita as mesmas cinco categorias dos produtos,
com união antes da paginação. As faixas da licitação usam `medida_if_media`.
`requer_validacao` prevalece quando algum resultado da compra ultrapassa seis
vezes a mediana positiva do seu produto/unidade na base atual completa. Os
valores extremos permanecem na média e nos totais. Somente compras com ocorrências
nessa condição recebem a marcação; outras compras do mesmo produto não a herdam.

`GET /api/v1/visao/licitacoes/{process_id}` retorna `licitacao` e `itens`
paginados. Os filtros da listagem são ignorados no detalhe para conservar toda
a compra importada. Paginar os itens não modifica o resumo. Nenhum modelo é
treinado ou executado por essas consultas; elas leem resultados persistidos.

A consulta da análise de um item também informa
`atributos.comparacao.unidade_preco`, obtido da assinatura do modelo. Para modelos
históricos sem esse campo, a unidade de preço é exposta a partir da assinatura
armazenada, sem assumir a unidade do item atual ou modificar seus scores.

### Preços por produto na base operacional

`GET /api/v1/visao/produtos?base_id=...` reúne itens de compras diferentes com o
mesmo catálogo, especificação e unidade/embalagem. A ordem de atributos nomeados
não separa produtos equivalentes. Grupos sem catálogo ou unidade identificados
permanecem separados por item.

Menor preço, maior preço e mediana são calculados com os preços unitários dos
resultados não cancelados da base consultada, antes da paginação. Cada resultado
conta uma vez; as quantidades compradas não ponderam a mediana. Valores ausentes
não viram zero, e extremos continuam nos cálculos. Essa mediana não é a referência
de treino do IF. O limite provisório `maior preço > 6 × mediana da base atual`
marca o produto como `requer_validacao` quando a mediana é positiva, sem confirmar
erro ou remover registros.
A resposta inclui as ocorrências para abrir as análises individuais.

O parâmetro repetido `sinalizacao` permite combinar `menor_anomalia`,
`anomalia_intermediaria`, `maior_anomalia`, `requer_validacao` e `sem_analise`.
Exemplo: `&sinalizacao=menor_anomalia&sinalizacao=maior_anomalia`.
Sem seleção, todos os produtos são incluídos. A seleção usa união das categorias,
após calcular as estatísticas completas de cada produto e antes da paginação.
`Requer validação` tem precedência sobre as faixas IF. As demais usam o maior IF
disponível do produto: abaixo de 0,50, de 0,50 a menos de 0,70, ou de 0,70 a 1.
