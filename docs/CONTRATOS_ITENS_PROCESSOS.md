# Contratos de itens, processos, resultados e análises

Decisão da etapa 02 do [plano de conclusão](PLANO_CONCLUSAO.md), 03/11/2026. Branch: `feat/02-contratos-itens-processos`.

## Unidade de consulta e análise

**A fila de auditoria terá uma linha por item, com o processo como contexto.** Um processo pode conter vários itens e um item pode ter vários resultados, inclusive fornecedores distintos. Um contrato é outra entidade e só se relaciona ao processo por vínculo oficial comprovado. Processo, item, resultado, referência de preço e contrato não são contagens intercambiáveis.

A API oferece consultas por item nesta entrega. A interface atual ainda usa dados simulados; adaptar a navegação e os rótulos na etapa 03. As rotas de processos continuam representando processos, sem mudança de significado.

Nos ensaios existentes, a observação é uma referência de preço, identificada por compra/item/fornecedor/forma. Ela não equivale automaticamente ao item relacional ou ao processo inteiro. A etapa 04 deve resolver os vínculos e definir a formação dos atributos; a etapa 07 só publica análises em alvos relacionais comprovados. Referências sem processo/item resolvido não autorizam criar processos fictícios para satisfazer FKs.

Quando um item tiver resultados com preços unitários diferentes, preservar os preços de cada resultado. Não escolher o primeiro fornecedor, calcular uma média de preços ou produzir um único preço implícito na apresentação. A política analítica para múltiplos resultados precisa ser versionada na etapa 04; sem ela, a comparação que dependa de um preço único fica indisponível. O esquema atual suporta scores de item/processo, não scores por resultado de fornecedor; uma necessidade diferente exige revisão explícita do contrato e da modelagem.

## Identidades e snapshots

| Campo | Significado e uso |
| --- | --- |
| `base_id` | UUID de uma base validada; fixar entre lista, detalhe, documentos e páginas |
| `item.id` | UUID estável de `itens_processo`; usado em `/itens/{item_id}` |
| `item.item_versao_id` | UUID do snapshot em `itens_versoes`; pode mudar entre bases |
| `item.chave_oficial` / `numero_item` | Textos da fonte; preservar zeros; número do item não é global |
| `item.processo.id` | UUID estável de `processos`; usado em `/processos/{processo_id}` |
| `item.processo.processo_versao_id` | Snapshot pai da mesma base; não usar como ID estável de navegação |
| `item.processo.chave_oficial` | Identidade textual oficial da compra na fonte |
| `resultado.id` | UUID do resultado naquele snapshot; não prometido como identidade estável entre bases |
| `resultado.fornecedor_id` | UUID do fornecedor; nome observado no resultado preserva o snapshot |
| `execucao_analise_id` | Seleção futura de publicação analítica; ainda não é parâmetro aceito nas consultas |

IDs simulados como `LC-2026-0142` não substituem UUIDs da API. Itens existentes em outra base, mas ausentes na selecionada, retornam 404. Correções geram novos snapshots e não alteram a base consultada anteriormente.

## Endpoints implementados

Todas as rotas abaixo usam `/api/v1`. Contrato comum de paginação, erros e seleção de base: [API_CONSULTAS.md](API_CONSULTAS.md).

| Rota | Granularidade e resposta |
| --- | --- |
| `GET /itens` | Nova: `dados: ItemSummary[]`, uma linha por item; `meta` com base e paginação |
| `GET /itens/{item_id}` | Nova: `{base_id, item: ItemSummary}` |
| `GET /processos` | Mantida: uma linha por processo, com totais globais e do recorte separados |
| `GET /processos/{processo_id}` | Mantida: `{base_id, processo}` |
| `GET /processos/{processo_id}/itens` | Mantida: itens paginados com o contrato anterior `Item`, sem campos novos obrigatórios |
| `GET /processos/{processo_id}/documentos` | Mantida: documentos da compra e de contratos com vínculo explícito; não afirma vínculo documental específico ao item |
| `GET /base/status`, `/orgaos`, `/modalidades` | Mantidas: cobertura e filtros do recorte selecionado |

`ItemSummary` preserva os campos de `Item`: descrição, unidade, quantidade, estimativa unitária, sigilo, catálogo, resultados e análise. Acrescenta `chave_oficial`, `processo`, `valor_homologado_item`, `resultados_ativos`, `resultados_sem_valor_total` e `ultima_data_resultado`.

`processo` contém IDs, fonte/chave oficial, números da compra/processo/controle PNCP, objeto, órgão, modalidade e data de publicação. Não inclui totais globais duplicados em cada linha da fila. Consultar o detalhe do processo para esses valores.

## Filtros e ordenação de `/itens`

| Parâmetro | Semântica |
| --- | --- |
| `base_id`, `pagina`, `tamanho_pagina` | Mesma seleção e limites das consultas de processos; tamanho padrão 20, máximo 100 |
| `processo_id`, `orgao_id`, `modalidade_id` | UUIDs; contexto pai do próprio item na base |
| `catalogo`, `codigo_catalogo` | Igualdade textual exata, de 1 a 100 caracteres; `000123` não equivale a `123`; usar ambos para identificar código dentro de um catálogo |
| `fornecedor_id` | Pelo menos um resultado não cancelado do próprio item para esse fornecedor |
| `homologacao_inicio`, `homologacao_fim` | Datas inclusivas de resultados não cancelados do próprio item; quando combinadas com fornecedor, exigir o mesmo resultado |
| `valor_minimo`, `valor_maximo` | Limites inclusivos de `valor_homologado_item`, decimal não negativo, até 28 dígitos e oito casas |
| `busca` | Até 200 caracteres; descrição/número/chave do item, objeto/números/chave da compra ou nome de fornecedor em resultado não cancelado do item |
| `ordenacao` | `publicacao_desc` (padrão), `publicacao_asc`, `valor_desc`, `valor_asc`, `descricao_asc` |

Publicação é a do processo pai. Ordenações têm desempate pelo UUID estável do item; datas/valores desconhecidos ficam no final. Busca ignora caixa, preserva distinção de acentos e trata `%`/`_` literalmente. Espaços nas pontas são removidos; busca vazia não restringe. A busca é independente dos demais filtros: não promete que o nome pesquisado e o resultado que satisfez a data sejam o mesmo registro.

Filtros selecionam itens, não recortam seus resultados nem recalculam o total para um único fornecedor/período. A resposta mantém todos os resultados, com cancelamento explícito. A última data exibida pode pertencer a outro resultado ativo do item, fora do intervalo filtrado.

`escopo_valor` continua exclusivo de `/processos`; não é aceito em `/itens`. `score`, `prioridade`, `execucao_analise_id` e ordenação por score ainda não são suportados. Parâmetros extras ou inválidos retornam 422, sem correção silenciosa.

## Dinheiro, somas e ausência

- Dinheiro e quantidades são strings decimais; manter casas significativas e não converter valores no processamento para `float`. A formatação monetária visual não deve redefinir a precisão do contrato.
- `valor_homologado_item` soma os totais de todos os resultados não cancelados daquele item na base. Não é valor pago nem valor global da compra.
- Sem resultados ativos, o total é `null`, os contadores são zero e `ultima_data_resultado` é `null`. Um resultado conhecido com total zero pode produzir `"0.00000000"`.
- Se qualquer resultado ativo tiver total ausente, a soma fica `null`; `resultados_sem_valor_total` indica quantos. Não completar com `quantidade × preço` sem uma regra de origem validada.
- Quantidade do item não é automaticamente quantidade homologada. Preços e quantidades homologadas permanecem em cada resultado.
- Ausência de propostas não representa zero participantes; ausência de contrato/documento não comprova inexistência na realidade.
- Participações, documentos e contratos não entram nos joins de agregação. A paginação ocorre antes de anexar os resultados, evitando multiplicação de linhas e valores.

Exemplo artificial de conciliação: processo com total oficial `200.00000001`, item A com resultados ativos `0.10000001` e `0.20000000`, item B com `0.30000000`. O total de A é `0.30000001`; o recorte dos itens é `0.60000001`; o global continua `200.00000001`. Um resultado cancelado de `9999` não altera essas somas. Se surgir outro vencedor ativo de `1` no item A, o total do item passa para `1.30000001`, mesmo filtrando pelo primeiro fornecedor. Não somar o valor global ao recorte ou repetí-lo por item em cards de totais.

## Estados analíticos e compatibilidade futura

O contrato implementado é exatamente:

```json
{"analise": {"status": "nao_publicada", "score": null, "prioridade": null}}
```

Esse campo continua significando ausência de publicação de auditoria validada, sem afirmar regularidade ou baixa prioridade. Desde a etapa 07 há um canal experimental separado, consultado explicitamente pelas [rotas de análise](INFERENCIA_PUBLICACAO.md). Estados operacionais do treinamento não devem aparecer como aprovação pública.

Na etapa 07, definir seleção por execução/base, motivos de indisponibilidade e a distinção entre análise não publicada, alvo não analisado em execução publicada e alvo analisado. Score/política/modelo devem ser rastreáveis; faixas 0–100 do protótipo não são limites já validados. A ampliação dos estados deve atualizar schemas, OpenAPI, testes e consumidores juntos, sem alterar retroativamente a interpretação dos dados atuais.

Não há score de processo derivado implicitamente do score do item. A agregação e a regra que alimentará o ranking dependem de política validada, registrada na execução. Os pesos 43/27/18/12% da interface continuam fictícios e não entram no contrato real.

## Navegação planejada para a etapa 03

| Tela/ação | Contrato a consumir |
| --- | --- |
| Entrada em consultas reais | Buscar `/base/status` e guardar `base.id` |
| Fila de itens | `/itens?base_id=...`, com filtros/paginação; rótulo deve deixar claro que cada linha é item |
| Detalhe do item | Rota de frontend `/itens/{UUID}?base_id=...`, consultando `/api/v1/itens/{UUID}` |
| Contexto da compra | Usar `item.processo.id` em `/api/v1/processos/{UUID}` na mesma base |
| Documentos | Usar `/processos/{item.processo.id}/documentos` e identificar que são documentos da compra/contratos vinculados |
| Link inexistente | Exibir erro/404; nunca substituir silenciosamente pelo primeiro item |
| Relatório/revisão | Preservar IDs/base na navegação; a persistência dependerá das etapas 09/10 e da análise publicada |

A rota visual atual `/processos/:id` ainda contém IDs fictícios. A etapa 03 deverá distinguir detalhe real de processo e item; qualquer compatibilidade com links antigos precisa ser explícita. Não foi alterada interface nesta entrega.

## Como verificar esta etapa

Na raiz, com `.env` e banco de testes configurados conforme [README do backend](../backend/README.md):

```bash
uv run --locked --all-packages --extra validation pytest backend/tests/test_consultas.py -q
uv run --locked --all-packages --extra validation pytest -q
uv run --locked --all-packages --extra validation ruff check .
uv run --locked --all-packages --extra validation ruff format --check .
```

Para conferir os dados reais, iniciar a API (reiniciar um servidor antigo que não use reload):

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

1. Abrir http://127.0.0.1:8000/docs e executar `GET /api/v1/base/status`. Copiar `base.id`.
2. Executar `GET /api/v1/itens` com esse `base_id`, `tamanho_pagina=1` e `ordenacao=descricao_asc`. Esperado no piloto atual: total 10, uma linha e dez páginas.
3. Copiar `dados[0].id` e consultar `/itens/{item_id}` com a mesma base. O objeto `item` deve ser igual ao da lista.
4. Consultar `/processos/{item.processo.id}` e conferir `processo_versao_id`. Abrir seus itens/documentos sem trocar a base.
5. Consultar `processo_id` ou fornecedor na lista e verificar que não aparecem itens de outro processo/fornecedor sem resultado correspondente.
6. Tentar um UUID inexistente (404) e `LC-2026-0142` no caminho (422); tentar `ordenacao=score_desc` (422).

Os exemplos artificiais de múltiplos vencedores, valores desconhecidos, cancelamento, snapshots e precisão são verificados nos testes em schemas descartáveis, sem modificar os dados reais para demonstrá-los. O ranking analítico e a integração visual permanecem nas próximas etapas.

## Resultado da entrega

**OK:** 113 testes locais aprovados, sem skips, lint e formatação aprovados. Comparação do OpenAPI com a `main` preservou exatamente as nove rotas e os 23 schemas anteriores. A validação HTTP TCP com o login restrito da API confirmou dez itens reais, navegação ao processo, respostas consistentes com a consulta antiga e erros 404/422. Contagens persistidas e `.env` foram preservados; servidor temporário encerrado. Evidência em [conclusao_etapa02.json](diagnostico/conclusao_etapa02.json). Não houve migração, importação, alteração visual ou publicação de scores.
