# Frontend com consultas reais — etapa 03

Data: 03/11/2026. Branch: `feat/03-frontend-consultas-reais`.

## Comportamento entregue

A entrada `/` abre `/itens`, com dados da API. A consulta oferece busca, órgão, fornecedor, modalidade, período de resultado, intervalo de valor, ordenação e tamanho de página. Clicar em **Aplicar filtros** consulta o servidor e reinicia na primeira página; **Limpar filtros** remove as restrições, preservando a base. Opções de órgãos, fornecedores e modalidades têm busca e paginação próprias, sem presumir que a primeira página contém todas as opções.

`GET /api/v1/base/status` resolve a base inicial. O UUID fica em `base_id` na URL e é enviado nas consultas relacionadas. Links de item/processo/documentos e paginação preservam essa seleção; uma nova importação não troca silenciosamente o recorte. Um link com base inválida mostra erro e não cai na base mais recente. A base é uma seleção técnica do snapshot, não uma validação dos modelos.

Cada linha representa um item. O detalhe mostra quantidade/unidade/estimativa conhecidas e resultados por fornecedor, com cancelamento explícito. Não escolhe um vencedor arbitrário nem calcula preço médio. Valores decimais são formatados por texto, inclusive acima do limite exato de `Number`; ausência não vira zero.

Os documentos são metadados da compra e de contratos explicitamente vinculados, com link à fonte em outra aba. Não se afirma que cada anexo trata daquele item. URLs precisam ser HTTP(S), sem credenciais; links inválidos não são executados.

Score, prioridade e comparações ficam como **análise não publicada**. Revisão persistente e relatórios reais continuam nas etapas 09/10; o detalhe real não simula essas operações.

| Caminho visual | Conteúdo |
| --- | --- |
| `/itens` | Lista real com filtros e paginação |
| `/itens/{UUID}?base_id=...` | Detalhe real do item e documentos |
| `/processos/{UUID}?base_id=...` | Contexto real da compra, totais globais/recorte distintos e itens do processo |
| `/processos` | Compatibilidade: redireciona para `/itens`; remove a antiga aba demonstrativa |
| `/demonstracao/painel` | Painel com dados fictícios, identificado como demonstração |
| `/demonstracao/itens` e `/demonstracao/itens/{ID}` | Exemplos fictícios preservados para a equipe |
| `/fornecedores`, `/relatorios` | Demonstrações identificadas; ainda não são as funcionalidades reais |

Links fictícios do painel, ajuda e fornecedores apontam para a demonstração. IDs inexistentes não são substituídos pelo primeiro exemplo. Um UUID real passado ao relatório demonstrativo recebe mensagem de indisponibilidade, sem emitir relatório fictício daquele item.

## Consulta de apoio acrescentada

`GET /api/v1/fornecedores/opcoes` retorna `Page[Lookup]` (`dados: [{id, nome}]`, `meta`). Aceita `base_id`, `busca`, `pagina` e `tamanho_pagina`, com os limites existentes. Só inclui fornecedores com resultados não cancelados na base selecionada, sem duplicações; o nome é o do resultado mais recente por data/ID, não um nome global atualizado em outra base. A busca é literal e a ordenação é nome/ID.

Essa rota serve ao seletor. Não é ranking, resumo de fornecedor ou cálculo de concentração da etapa 08. As rotas existentes continuam disponíveis.

## Configuração e execução

Pré-requisitos: instalação e PostgreSQL do [README do backend](../backend/README.md), incluindo uma base importada para ver dados. Não sobrescrever o `.env` existente.

Terminal 1, na raiz:

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Terminal 2, na raiz:

```bash
npm ci --prefix Frontend-licita-clara
npm run dev --prefix Frontend-licita-clara
```

Abrir a URL emitida pelo Vite, normalmente http://localhost:5173/itens. Se a API já estiver rodando sem reload, reiniciá-la para carregar `/fornecedores/opcoes`. Não iniciar uma segunda API na mesma porta.

O padrão `VITE_API_URL=/api/v1` usa o mesmo host da interface. No desenvolvimento, o Vite encaminha `/api` para `http://127.0.0.1:8000`, evitando depender de CORS para esse caminho. Não são necessárias credenciais de banco no navegador.

Configuração opcional em `Frontend-licita-clara/.env`, usando o exemplo dessa pasta apenas como referência:

```dotenv
VITE_API_URL=/api/v1
API_PROXY_TARGET=http://127.0.0.1:8000
```

`API_PROXY_TARGET` configura apenas o servidor Vite. `VITE_API_URL` é público e incorporado ao bundle: nunca colocar senhas, tokens ou URLs de PostgreSQL em variáveis `VITE_*`. Reiniciar o Vite após alterações. Para API em outra origem, configurar sua URL pública completa até `/api/v1` e permitir a origem da interface no CORS do backend. O build estático precisa de encaminhamento `/api` no host ou URL pública explícita; hospedagem é tratada na etapa 12.

## Como testar manualmente

1. Abrir `/itens`. Esperado no piloto atual: dez itens, sete processos e período de setembro/2026 na base selecionada; a URL ganha `base_id`.
2. Selecionar cinco itens por página e aplicar. Navegar à próxima página; o UUID da base permanece igual. Buscar uma palavra presente em uma descrição e aplicar; página reinicia em 1.
3. Filtrar por órgão/fornecedor/modalidade e período. Comparar ao Swagger usando os mesmos parâmetros. O fornecedor e período devem corresponder a um resultado não cancelado do próprio item.
4. Aplicar um intervalo de valor e testar “Limpar filtros”. Total do item pode ser desconhecido e não deve aparecer como zero.
5. Abrir um item e depois “Ver processo da compra”. Conferir resultados por fornecedor, valores globais versus do recorte e documentos. Usar “Voltar à consulta” no item para preservar os filtros de origem.
6. Abrir um item com UUID inexistente e depois `/itens/LC-2026-0142`: esperado erro 404 e 422, sem mostrar o primeiro item da base.
7. Com a API indisponível, usar “Tentar novamente”; depois de restabelecê-la, a consulta deve recuperar. Não interromper serviços de outras pessoas para fazer esse teste.
8. Abrir as telas de demonstração: o aviso de dados fictícios deve permanecer visível. A consulta real não mostra scores simulados.
9. Conferir a consulta em celular e tema escuro. A tabela tem rolagem própria para suas colunas.

## Verificações automatizadas

Cliente HTTP, precisão decimal e URLs:

```bash
npm test --prefix Frontend-licita-clara
```

Browser com respostas artificiais identificadas nos testes (não requer API/PostgreSQL):

```bash
cd Frontend-licita-clara
npx playwright install chromium
npm run test:e2e
```

Se já houver Google Chrome instalado, pode usar `PLAYWRIGHT_CHANNEL=chrome npm run test:e2e`. Na CI, a instalação usa `npx playwright install --with-deps chromium` para incluir dependências do sistema do runner.

Com a API real em execução e dados importados, a partir da raiz:

```bash
npm run test:live --prefix Frontend-licita-clara
```

Pode ajustar `API_PROXY_TARGET` para a API local desejada e `FRONTEND_TEST_PORT` para a porta do servidor temporário de testes (padrão 4197). O runner não reutiliza ou encerra um servidor já existente nessa porta. Resultados e screenshots ficam em `Frontend-licita-clara/test-results/`, ignorados pelo Git. O teste live é somente leitura e não cria dados na aplicação.

Backend e build:

```bash
uv run --locked --all-packages --extra validation pytest -q
uv run --locked --all-packages --extra validation ruff check .
uv run --locked --all-packages --extra validation ruff format --check .
npm run build --prefix Frontend-licita-clara
```

As evidências finais da execução estão em [conclusao_etapa03.json](diagnostico/conclusao_etapa03.json). Fidelidade ao Figma, revisão completa de acessibilidade, autenticação e publicação de análise não são demonstradas por estes testes; seguem nas etapas correspondentes.

## Atualização na etapa 08

`/painel`, `/ranking`, `/fornecedores` e `/fornecedores/{id}` agora consultam dados reais e seleção experimental explícita. A antiga tela fictícia de fornecedores foi preservada em `/demonstracao/fornecedores`. Consulte o [guia atual das telas analíticas](PAINEL_RANKING_FORNECEDORES.md); as instruções e resultados acima registram a entrega histórica 03.
