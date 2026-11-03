# Consultas de processos e dados de apoio — etapa 06

Implementado em 20/10/2026. API de leitura de dados importados no PostgreSQL, independente dos ensaios de ML. Não calcula ou publica scores. O frontend permanece com seus dados simulados até integração posterior.

Atualização de 03/11/2026: a etapa 02 do plano de conclusão acrescentou `/itens` e `/itens/{item_id}`, com contexto do processo e total do próprio item. As sete rotas originais mantêm seus contratos. Ver [contratos de itens/processos](CONTRATOS_ITENS_PROCESSOS.md) para filtros, navegação e instruções de teste. As evidências da etapa 06 abaixo continuam sendo o registro histórico de 20/10/2026.

A etapa 03 integra essas consultas ao frontend e acrescenta `/fornecedores/opcoes` para o seletor paginado. O nome do fornecedor vem do resultado não cancelado mais recente na base, com desempate pelo ID; a busca é aplicada sobre esse nome selecionado. Essa rota não é ranking nem calcula concentração. Ver [frontend integrado](FRONTEND_CONSULTAS_REAIS.md).

## Executar

Na raiz do repositório, com `.env` configurado e PostgreSQL migrado em execução:

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

O extra `validation` mantém as bibliotecas do ensaio de ML instaladas no mesmo ambiente. As consultas do backend não dependem de scikit-learn e não carregam modelos. Se a API já estiver em execução sem recarga automática, reiniciá-la para carregar as rotas novas.

Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). OpenAPI gerado pela aplicação: `/openapi.json`.

## Rotas

Todas usam prefixo `/api/v1`.

| Método | Rota | Resposta |
|---|---|---|
| GET | `/base/status` | Base selecionada, período, cobertura e horários dos arquivos/importações vinculados |
| GET | `/orgaos` | Órgãos presentes na base, paginados e sem repetir o mesmo ID |
| GET | `/modalidades` | Modalidades presentes na base, paginadas |
| GET | `/processos` | Processos, valores, fornecedores de resultados ativos e paginação |
| GET | `/processos/{processo_id}` | Detalhe do processo no snapshot selecionado |
| GET | `/processos/{processo_id}/itens` | Itens do recorte com seus resultados, incluindo a indicação de cancelamento |
| GET | `/processos/{processo_id}/documentos` | Metadados de anexos da compra e de contratos explicitamente vinculados |
| GET | `/itens` | Itens paginados da base, cada um com contexto do processo, todos os resultados e total dos resultados não cancelados |
| GET | `/itens/{item_id}` | Detalhe do item pelo UUID estável, limitado à base selecionada |
| GET | `/fornecedores/opcoes` | IDs/nomes de fornecedores com resultados não cancelados, busca e paginação na base selecionada |

`/health` e `/ready` continuam disponíveis. Não foram criadas rotas de escrita, coleta ou treinamento.

## Versão da base e identificadores

Todos os endpoints aceitam `base_id` UUID. Quando omitido, selecionam a base com status `validada` mais recentemente criada, com desempate pelo ID. Esse status valida integridade da importação; não aprova comparabilidade dos itens ou treinamento. Bases preparando/rejeitadas não são expostas por essas consultas.

Para várias requisições relacionadas, consultar `/base/status`, copiar `base.id` e enviá-lo nas demais. Isso impede mudar de recorte entre páginas se uma nova base for importada. A seleção fica fixa durante cada requisição; todos os joins/subconsultas usam essa mesma base.

- `id` do processo é UUID da identidade estável; é o identificador usado no caminho.
- `processo_versao_id` identifica o snapshot, que muda entre bases.
- `chave_oficial`, `numero_compra`, `numero_processo` e números de itens são textos da fonte, preservando zeros iniciais. Número de processo ausente permanece `null`; não é substituído pelo identificador fictício do protótipo.
- Itens retornam `id` estável e `item_versao_id` do snapshot.

`/base/status` sem nenhuma base validada retorna 200 com `status: "sem_base"` e cobertura `null`. Uma seleção explícita inexistente/não validada ou uma consulta de processos sem base disponível retorna 404. Uma base validada vazia retorna listas vazias e contagens zero.

## Paginação e busca

Listagens retornam:

```json
{
  "dados": [],
  "meta": {
    "base_id": "a21534e3-e1a9-5d31-9a4e-c3beb608914f",
    "pagina": 1,
    "tamanho_pagina": 20,
    "total": 0,
    "total_paginas": 0
  }
}
```

`pagina` começa em 1 e vai até 1.000.000; `tamanho_pagina` padrão 20, máximo 100. Página além dos resultados retorna lista vazia com o total preservado. A paginação dos itens ocorre antes de anexar seus resultados; vários resultados não criam várias linhas do mesmo item.

`busca`, até 200 caracteres, está disponível em órgãos, modalidades e processos. Nos processos, pesquisa objeto, número do processo/compra, chave oficial, descrição dos itens e nomes de fornecedores dos resultados ativos. Ignora caixa e mantém distinção de acentos. Espaços nas pontas são removidos; busca em branco não restringe resultados. `%` e `_` são caracteres literais, não curingas fornecidos pelo cliente. Consultas são parametrizadas.

## Filtros de processos

| Parâmetro | Semântica |
|---|---|
| `orgao_id` | UUID do órgão |
| `fornecedor_id` | UUID do fornecedor com resultado ativo em um item importado |
| `modalidade_id` | UUID da modalidade |
| `homologacao_inicio`, `homologacao_fim` | Datas ISO `YYYY-MM-DD`, inclusivas, sobre `data_resultado` dos resultados ativos dos itens do recorte |
| `valor_minimo`, `valor_maximo` | Decimal não negativo, até 28 dígitos e oito casas; limites inclusivos |
| `escopo_valor` | `processo` (padrão) ou `itens_recorte`; controla filtro e ordenação por valor |
| `ordenacao` | `publicacao_desc` (padrão), `publicacao_asc`, `valor_desc`, `valor_asc`, `objeto_asc` |

Quando fornecedor e período forem informados juntos, ambos precisam corresponder ao **mesmo resultado ativo**. Resultados cancelados não satisfazem esses filtros. Registro sem data não satisfaz filtro de data; valor desconhecido não satisfaz limites de valor. Intervalos invertidos são rejeitados com 422.

Os campos `data_resultado` do processo e `ultima_data_resultado_itens_recorte` são distintos. O primeiro permanece como veio no snapshot do processo; o segundo é a maior data dos resultados ativos importados, sem afirmar homologação integral da compra. Filtrar um intervalo encontra processos com pelo menos um resultado ativo naquele intervalo; a maior data exibida pode corresponder a outro item do mesmo recorte.

Ordenação usa somente campos permitidos, com desempate pelo UUID estável do processo; valores/datas desconhecidos ficam no final. Órgãos e modalidades ordenam por nome e ID; itens por número textual e ID; documentos por publicação decrescente (nulos no final) e ID. Não há ordenação por score nesta etapa.

## Dinheiro, ausência e agregação

Valores monetários e quantidades são strings decimais, como `"200.00000001"`, mantendo a precisão do PostgreSQL. Datas usam ISO; timestamps preservam offset quando conhecido. Ausência continua `null`, não zero.

- `valor_estimado_processo` e `valor_homologado_processo`: valores globais do snapshot oficial da compra. Não foram recalculados a partir da categoria selecionada.
- `valor_homologado_itens_recorte`: soma dos totais dos resultados ativos dos itens importados. Exclui cancelados. Se não houver resultados ou qualquer resultado ativo tiver total desconhecido, retorna `null`, evitando apresentar soma parcial como completa. `resultados_sem_valor_total_recorte` informa quantos totais estão ausentes.
- Os totais do recorte não mudam para representar apenas um fornecedor quando ele é usado como filtro; o filtro seleciona processos, não redefine o universo de agregação.
- Uma categoria importada pode ser apenas parte de uma compra. Os dois valores não são intercambiáveis e não devem ser somados entre si.
- `fornecedores` lista os fornecedores distintos dos resultados ativos. O nome vem do resultado mais recente na base (desempate pelo ID), preservando nomes observados no snapshot em vez do nome atual do cadastro.
- Órgãos usam nome do snapshot da publicação mais recente na base (desempate pelo ID), com um registro por órgão.
- Participações e documentos não entram nos joins usados para calcular valores. Fornecedores são consultados depois da paginação; a presença de várias relações não multiplica processos ou valores.

## Documentos e análises

Documentos retornam título, tipo, URL oficial, ativo/desconhecido e horário de publicação da origem. Incluem anexos contratuais somente quando há vínculo explícito na mesma base. Contratos não são inferidos por nome/objeto. Sem documentos conhecidos, retorna 200 com `dados: []`; processo inexistente retorna 404.

`binario_registrado` indica apenas se há registro de objeto baixado no banco. Não verifica existência física no disco/bucket nem afirma que o documento foi analisado. Não expõe chave interna de armazenamento e não oferece download por proxy nesta etapa.

Processos e itens retornam:

```json
{"analise": {"status": "nao_publicada", "score": null, "prioridade": null}}
```

Isso não afirma que um processo seja regular. Os artefatos de ML permanecem experimentais e separados; publicar ranking continua dependendo das etapas 07–09 e da validação documentada de utilidade.

## Erros

404, 422, 500 e 503 usam o mesmo envelope:

```json
{
  "erro": {
    "codigo": "processo_nao_encontrado",
    "mensagem": "Processo não encontrado nesta base.",
    "request_id": "identificador-da-requisicao",
    "detalhes": []
  }
}
```

422 inclui campo/tipo da validação, sem repetir o conteúdo recebido. Falhas operacionais de banco retornam 503; falhas internas retornam 500. Logs registram classe da falha e request ID, sem SQL, credenciais ou mensagem do driver. `X-Request-ID` acompanha as respostas. Health/readiness preservam seus contratos operacionais próprios.

## Verificação executada

Foram aprovados 95 testes locais, sem skips, além de lint e formatação. Os novos testes de consultas usam PostgreSQL real, papel `licita_api` e schemas descartáveis em banco `_test`. Cobrem múltiplas bases, precisão decimal, valores desconhecidos, resultados cancelados, fornecedores, participantes, documentos, ausência de dados, filtros, paginação, SQL parametrizado, erros sanitizados e OpenAPI.

A verificação HTTP local com o login restrito da aplicação consultou a base real `a21534e3-e1a9-5d31-9a4e-c3beb608914f`: sete processos, dez itens, oito resultados ativos, seis fornecedores nesses resultados, sete órgãos, duas modalidades, 130 referências de preço e dez metadados de documentos. Os sete processos estão sem data de resultado global e dois sem valor homologado global; esses campos não foram fabricados. Cinco processos têm soma de resultados ativos no recorte. Três possuem resultado ativo entre 01/09 e 20/10/2026.

[Evidência da etapa 06](diagnostico/validacao_etapa06.json). As contagens persistidas foram preservadas, sem migrações ou novas importações. O servidor usado na verificação foi temporário e encerrado; iniciar a API pelo comando acima para navegar. Nenhum serviço preexistente foi encerrado. O CI segue preparado; não houve execução remota nesta entrega.

## Análises experimentais (etapa 07)

Cinco rotas adicionais de leitura em `/api/v1/analises` exigem base/execução explícitas e preservam estados sem score. Consulte [inferência e publicação](INFERENCIA_PUBLICACAO.md). O campo legado `analise.nao_publicada` continua relativo à ausência de publicação de auditoria validada; ele não seleciona automaticamente o canal experimental. Bases de treino (`recorte.tipo=treino_modelo`) são excluídas das consultas operacionais.
