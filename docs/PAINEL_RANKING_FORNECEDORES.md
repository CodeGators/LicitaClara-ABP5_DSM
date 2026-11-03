# Painel, ranking e fornecedores reais — etapa 08

Branch `feat/08-painel-ranking-fornecedores`. A `main` local/remota estava sincronizada em `de16cf2` no início desta etapa, após envio autorizado das entregas 00–07. Esta entrega permanece em branch própria, sem merge/push.

## Telas implementadas

- `/painel`: contadores do recorte, totais homologados, cobertura, distribuição dos índices disponíveis, evolução por último resultado e motivos de indisponibilidade.
- `/ranking`: itens ordenados por índice experimental, valor ou descrição; cobertura parcial/indisponível, paginação e acesso ao detalhe real.
- `/fornecedores`: fornecedores dos itens selecionados, compras com resultado, contratos vinculados, totais próprios e máximo de índice dos seus resultados.
- `/fornecedores/{id}`: relações por órgão, participação e HHI do recorte, compras distintas e itens/resultados desse fornecedor.
- `/itens/{id}`: mostra a análise experimental indicada na URL, preservando scores por fornecedor/modelo, parcelas AE e explicação IF indisponível. Um modelo fora da execução não recebe resultados de outro modelo como fallback.

Os estilos/componentes existentes foram reutilizados. Painel e fornecedores antigos foram preservados em `/demonstracao/painel` e `/demonstracao/fornecedores`; continuam usando dados fictícios, com aviso. `/demonstracao/itens` e `/relatorios` também permanecem demonstrativos. Nenhum número das novas telas usa `data.js` ou fallback fictício. O acesso ao Figma continua pendente; não foi afirmada fidelidade ao design nem concluída a auditoria visual/acessível de 11.

A entrada `/` continua em `/itens`. A navegação lateral oferece Painel, Ranking experimental e Fornecedores reais. Ao trocar de tela a rolagem volta ao topo; em telas pequenas, tabelas podem rolar dentro do seu contêiner, sem alargar a página. Tema claro/escuro preservado.

## Seleção e filtros compartilhados

`base_id`, `execucao_id` e `modelo_id` ficam na URL. Na primeira visita às novas telas, o cliente consulta a publicação ativa da base e fixa sua execução; seleciona o IF disponível por padrão e também fixa esse modelo. Depois disso, publicar outra execução não muda a seleção aberta. O usuário pode escolher versões publicadas anteriores, outro modelo ou consultar sem análise (`execucao_id=nenhuma` na URL do frontend, omitido na chamada API).

A API nunca escolhe silenciosamente uma execução/modelo mais recente. Modelo sem execução é inválido; modelo de outra execução e IDs/base incompatíveis geram erros explícitos. Uma execução inexistente não vira a ativa automaticamente; a interface permite escolher outra versão. Respostas antigas são canceladas/descartadas ao mudar seleção ou filtros.

Os filtros são comuns: texto em item/compra/fornecedor, órgão, modalidade, fornecedor, datas de homologação, mínimo/máximo do total do item no recorte e estado da análise. A busca/valores preservam strings e decimais; a seleção reaparece ao navegar entre telas. Paginação é reiniciada ao aplicar filtros ou trocar modelo/execução.

Não há filtro de prioridade alta/média/baixa: não existem faixas de auditoria validadas. O filtro disponível é de **cobertura**: integral, parcial e não analisado. Isso implementa a consulta de análise sem inventar prioridades a partir do protótipo.

## Universo, totais e ausências

O recorte parte dos itens da base operacional, considera somente resultados não cancelados e aplica o intervalo de homologação aos resultados. Com filtro de data, resultados sem data ficam fora, pois não há como confirmar que pertencem ao intervalo. Sem filtro de data, são incluídos nos valores conhecidos e o item aparece em `Sem data conhecida` na evolução se não houver resultado datado.

O fornecedor filtra **itens que têm resultado dele no período**, mas valores/concentração desses itens preservam os demais vencedores no período. A lista de fornecedores pode exibir somente o fornecedor escolhido; o contador `fornecedores_no_denominador` e a explicação mantêm visível que o HHI usa todos os fornecedores desse universo. Isso evita HHI artificialmente igual a um por descartar covencedores. Esse universo é um recorte de itens, não todas as compras do órgão.

- Contador de compras: processos/snapshots distintos com os itens selecionados; duas linhas do mesmo processo não viram duas compras.
- Contratos: IDs distintos de snapshots de contratos efetivamente vinculados aos processos selecionados, independentemente de quantidade de itens/anexos. No fornecedor, somente contratos com identificação dele; vínculo desconhecido não é inferido da vitória em item.
- Valores: soma direta de `valor_total_homologado` dos resultados selecionados, sem produto entre itens/resultados/documentos/contratos. Não é estimativa global, valor contratado ou pago.
- Se qualquer resultado selecionado não tem total, o total agregado é nulo. A soma dos valores conhecidos aparece separadamente, sem ser apresentada como total completo. Zero conhecido permanece zero; ausência não vira zero. Sem resultados conhecidos, soma/total são indisponíveis.
- No detalhe do fornecedor, valores/índices dos itens relacionados consideram somente seus resultados. O detalhe completo do item conserva todos os vencedores, com essa diferença de escopo explicada na tela.

Dinheiro é somado em Decimal e serializado como texto, inclusive acima do limite exato de Number no JavaScript. Não há conversão monetária para float na interface. Participação/HHI são arredondados somente para exibição; os valores decimais completos permanecem na API.

## Índices e gráficos

Para cada item, usa-se o máximo dos índices dos seus resultados no **mesmo modelo selecionado**, sem combinar IF/AE. A cobertura é integral somente quando todos os resultados selecionados têm score; um ou mais sem score produzem estado parcial. Um item sem resultados ou sem nenhum score é não analisado. O máximo dos resultados de um fornecedor considera apenas os resultados dele, nunca o score de um covencedor.

A ordenação mantém índices disponíveis primeiro e ausências ao final; empates usam ID estável. Não existe score de processo ou probabilidade de fraude. O índice é a CDF do treino definida em 07. A utilidade continua inconclusiva por revisão humana e confirmação temporal pendentes.

Distribuição: um índice máximo por item, dez intervalos `[0,10)`, …, `[80,90)`, `[90,100]`, em cor neutra, sem rótulos de risco. Sem índices, mostra indisponibilidade, não uma distribuição de scores zero. Itens parciais são identificados nos contadores e no ranking.

Evolução: cada item conta uma vez, no mês de seu último resultado selecionado, com colunas de cobertura e grupo de data ausente. Não representa série de pagamentos, contratos ou alta prioridade. Somas dos meses/estados reconciliam com o contador de itens. Motivos contam ocorrências registradas, não percentuais de fraude.

## Relações e concentração

Para cada órgão identificado por ID (mesmo se nomes de snapshots diferirem), agrupar valores por todos os fornecedores no universo descrito. Participação = valor do fornecedor / total desse universo. HHI = soma dos quadrados das participações de **todos** os fornecedores. Valores ausentes ou denominador zero deixam HHI/participação indisponíveis, com motivo; não calcular sobre um subconjunto conveniente de valores conhecidos.

Exemplo controlado: 75/25 → HHI 0,625, participação 75%. Duas linhas da mesma compra contam uma compra observada. Cancelados não entram em numeradores/denominadores. Concentração, isoladamente, não comprova irregularidade. As relações são de resultados homologados e contratos conhecidos vinculados, sem inferir participação completa em certames ou entrega/pagamento.

## Contrato API

Quatro endpoints GET, somente leitura, com `base_id` obrigatório e filtros comuns:

| Endpoint | Retorno |
| --- | --- |
| `/api/v1/visao/painel` | contexto, resumo, distribuição, evolução e motivos |
| `/api/v1/visao/ranking` | contexto/resumo e página de itens/resultados/índices |
| `/api/v1/visao/fornecedores` | contexto/resumo e página de fornecedores |
| `/api/v1/visao/fornecedores/{supplier_id}` | contexto/resumo, fornecedor, relações por órgão e página de itens próprios |

Parâmetros de seleção: `execucao_id`, `modelo_id`; filtro `analise` = `todos`, `analisados`, `parcial`, `nao_analisados`; `ordenacao` = `indice_desc`, `descricao_asc`, `valor_desc`. Paginação 1–100 registros. Datas/valores invertidos, modelo fora da execução e filtros de prioridade não implementados retornam 422. Base/execução/fornecedor incompatíveis retornam 404, nunca o primeiro registro como fallback.

Esta versão lê no máximo 20 mil registros por tabela da base antes das agregações. Exceder o limite produz 503 `recorte_excede_limite`, sem truncamento silencioso. O filtro de tela não substitui preparar uma base menor nesse caso. Desempenho de volumes maiores precisa ser medido antes de ampliar limites.

## Como testar

Na raiz `LicitaClara-ABP5_DSM`, sem sobrescrever `.env` ou recriar volumes:

```bash
uv run --locked --all-packages --extra validation pytest backend/tests/test_visao.py -q
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Em outro terminal:

```bash
npm run dev --prefix Frontend-licita-clara
```

Abrir a URL do Vite com `/painel` (normalmente http://localhost:5173/painel). A API antiga deve ser reiniciada para carregar as quatro rotas novas. Swagger: http://127.0.0.1:8000/docs. Não há migração, coleta, treinamento ou publicação necessários para testar esta etapa nesta instalação.

1. Conferir base/execução/modelo fixados na URL e a marcação experimental. Alternar IF/AE e versão; a seleção muda somente por ação explícita.
2. No painel, conferir dez itens, sete compras, seis fornecedores, oito resultados não cancelados e R$ 26.579,80 homologados. Há zero contratos vinculados conhecidos, sem concluir que contratos não existam fora do recorte.
3. Conferir dez não analisados e distribuição indisponível. Na base atual não há scores elegíveis; não esperar índices positivos. Evolução real: quatro itens em abril/2025, um em fevereiro/2026, três em setembro/2026 e dois sem data conhecida.
4. Navegar ao ranking, filtrar analisados (vazio no piloto) e voltar a todos. Aplicar busca/órgão/fornecedor/datas/valores e conferir os mesmos totais ao mudar de tela. Paginar, abrir item e voltar, mantendo seleção/filtros.
5. Abrir fornecedor. Conferir compras com resultado versus contratos vinculados, valor próprio versus denominador do órgão e HHI do recorte. Sem totals suficientes, participação/HHI devem ficar indisponíveis.
6. Simular indisponibilidade da API e repetir; fornecer ID/intervalo inválido e corrigir. Nunca devem aparecer dados demonstrativos. Conferir celular/tema e rolagem interna das tabelas.

Suítes frontend (Chrome/Chromium instalado):

```bash
npm test --prefix Frontend-licita-clara
PLAYWRIGHT_CHANNEL=chrome npm run test:e2e --prefix Frontend-licita-clara
API_PROXY_TARGET=http://127.0.0.1:8000 PLAYWRIGHT_CHANNEL=chrome npm run test:live --prefix Frontend-licita-clara
npm run build --prefix Frontend-licita-clara
```

Usar `PLAYWRIGHT_CHANNEL` conforme o navegador disponível; a execução local usou Chrome headless. Testes `live` exigem API/base/publicação existentes; os controlados exercitam cenários com índices e erros sem alterar os dados da aplicação.

## Verificação e resultado

**153 testes Python**, **7 testes do cliente**, **19 cenários browser controlados** e **2 fluxos browser com API/PostgreSQL reais** aprovados, sem skips. Lint/formatação Python e build Vite aprovados. Capturas desktop/mobile e tema escuro inspecionadas; isso não comprova fidelidade ao Figma ou auditoria completa de acessibilidade.

As 34 tabelas mantiveram as contagens da entrega 07, com linhas anteriores, 237 arquivos verificados e `.env` preservados. Não houve migração/importação/treinamento/inferência/publicação nesta etapa. Servidor temporário de validação foi encerrado. Evidência: [conclusao_etapa08.json](diagnostico/conclusao_etapa08.json).

**OK para painel, ranking experimental e fornecedores integrados.** Cobertura de scores do piloto continua insuficiente; revisão independente e validação de utilidade permanecem pendentes. Autenticação/revisões persistentes são 09; relatórios reais são 10; conferência completa da interface é 11. Nenhuma dessas funcionalidades foi declarada concluída por esta entrega.
