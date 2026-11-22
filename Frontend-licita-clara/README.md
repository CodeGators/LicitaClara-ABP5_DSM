# Licita Clara — Frontend

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


Vite + React 18 + React Router + lucide-react. Consulta real de itens, detalhe, processo e documentos integrada à API. Painel, fornecedores, revisão e relatório demonstrativos permanecem separados e identificados; as demonstrações usam `src/data.js`.

Usar Node.js 20.19+ da linha 20 e npm. A partir desta pasta:

```bash
npm ci
npm run dev     # http://localhost:5173
npm run build
```

Entrada `/` → `/ranking` (Itens Sinalizados). Detalhes reais em `/ranking/:id` e `/processos/:id`. Os endereços antigos `/itens` e `/itens/:id` apenas redirecionam para as telas correspondentes em `/ranking`, preservando os parâmetros. Demonstrações em `/demonstracao/painel`, `/demonstracao/itens`, `/demonstracao/fornecedores` e `/demonstracao/relatorios`.
Tokens de cor/tipografia em `src/styles.css` (`:root`), seguindo a proposta de identidade (Inter, #102D46, #087F83...).

O frontend incorporou a entrega de 01/11/2026 da equipe e a integração da etapa 03. Subir a API na porta 8000 pelo README do backend; o Vite encaminha `/api` para ela. Configuração opcional em `.env` desta pasta, conforme `.env.example` (sem credenciais). Para outra API, configurar `API_PROXY_TARGET` no desenvolvimento ou `VITE_API_URL` pública até `/api/v1` e CORS apropriado.

Testes: `npm test` (cliente HTTP/decimais), `npm run test:e2e` (browser com fixtures) e `npm run test:live` (API real com dados importados). Instalar o browser com `npx playwright install chromium` ou usar `PLAYWRIGHT_CHANNEL=chrome` se Chrome já estiver instalado. Relatórios e screenshots de teste são ignorados pelo Git.

Instruções completas e resultados em FRONTEND_CONSULTAS_REAIS.md (documentação local). Revisão persistente, ranking e exportação real continuam no plano de conclusão (documentação local). O botão de exportação da demonstração abre a impressão do navegador; a opção CSV demonstrativa ainda não gera CSV.

O painel, ranking e fornecedores reais (documentação local) compartilha base/execução/modelo e filtros; leia as definições de universo, valores, HHI e indisponibilidade antes de interpretar os indicadores.

O detalhe do processo apresenta a síntese experimental quando a URL fixa
`base_id` e `execucao_id`. Exibe separadamente score integral, média dos sinais
disponíveis, cobertura oficial e links para os itens. Cobertura parcial mantém
o score integral indisponível. Os modelos continuam separados, sem botão de
execução ou faixas de fraude. API e banco devem estar na migração `0006_sinteses`.

## Relatórios reais

`/relatorios` consulta a API e permite selecionar um processo, conferir a prévia,
alterar título e baixar PDF/CSV sem login. Os links “Preparar relatório” no detalhe
do item/processo levam à compra selecionada e preservam base/execução; os modelos
são incluídos separadamente. A página não exporta apenas a página atual de itens.
A antiga tela ilustrativa fica em `/demonstracao/relatorios`.

Uma alteração de título precisa ser aplicada em “Atualizar prévia” antes do
exportar. Conflito 409 solicita atualizar os dados. Arquivos de até 200 itens por
processo podem ter várias páginas; ausências e limites são explícitos.

O projeto Playwright `reports-live` usa API/banco reais, sem escrever dados. Criar
JSON local ignorado com `base`, `execucao`, `processo` (UUIDs publicados) e executar:

```bash
PLAYWRIGHT_CHANNEL=chrome API_PROXY_TARGET=http://127.0.0.1:8000 LICITA_REPORT_TEST_CONFIG=../data/diagnostico/10/browser_config.json npx playwright test --project=reports-live
```

O fluxo verifica o snapshot, arquivos baixados, exceções JavaScript e largura em
celular. Os testes controlados de relatório fazem parte de `npm run test:e2e`.

## Interface e navegação acessível

As telas reais incluem atalho “Pular para o conteúdo”, identificação de conteúdo
principal, foco após troca de página e regiões de tabela roláveis com teclado.
No celular, o menu fechado fica fora da navegação por teclado. Menu aberto e
ajuda mantêm o foco, permitem fechar com Escape e devolvem o foco ao controle que
os abriu. As abas da ajuda aceitam setas, Home e End. A preferência por movimento
reduzido do sistema é respeitada. Contraste, foco e largura dos cartões foram
ajustados para os dois temas.

A lista de itens preserva base, execução e modelo ao aplicar/limpar filtros.
“Sem análise selecionada” descreve a consulta atual; não afirma que não existam
análises publicadas. Ajuda e glossário descrevem as funcionalidades reais.

`npm run test:e2e` inclui teclado, menu, ajuda, estados de carregamento/erro/vazio,
rolagem em 320 px e persistência de tema. A auditoria de dados reais usa o projeto
`interface-live` e [axe com Playwright](https://playwright.dev/docs/accessibility-testing):

```bash
PLAYWRIGHT_CHANNEL=chrome API_PROXY_TARGET=http://127.0.0.1:8000 LICITA_INTERFACE_CONFIG=../data/diagnostico/11/config.json npx playwright test --project=interface-live
```

O JSON local contém `routes`, lista de pares `[nome, caminho_com_base_e_execucao]`.
São verificadas oito telas em 1280/390 px e temas claro/escuro, com registro de
violações, exceções JavaScript, overflow da página/cartões e screenshots locais.
`LICITA_INTERFACE_OUTPUT` pode selecionar outra pasta de evidências.
As regras automatizadas WCAG 2/2.1 A/AA e best practices não substituem uma
avaliação completa com tecnologias assistivas.
O comportamento dos diálogos segue a [referência WAI-ARIA](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).

## Painel Geral

O painel tem quatro indicadores, distribuição em barras, evolução temporal e uma
seleção de itens para comparar resultados dos modelos. O período é apenas
informativo; o painel não exibe controles de filtros ou de versão da análise.
Ordenação, paginação e filtros permanecem nas telas de consulta.

Os cards mostram processos, homologado, itens com índice e itens sem análise.
Valores grandes são abreviados no card; o valor exato fica no título do valor.
As cores do histograma indicam intervalos numéricos, sem criar classes de risco.
A evolução usa o mês real do último resultado; itens sem data são informados
separadamente, e as tabelas dos gráficos podem ser abertas abaixo deles.

Selecionar uma linha em “Por onde começar” consulta os resultados já persistidos.
IF/AE são comparados para o mesmo resultado/fornecedor; quando há vários
resultados, o seletor permite escolher o fornecedor. Não executa treino/inferência.
Nomes longos têm visual compacto e texto completo no título/detalhe do item.

O teste real do painel (`painel-live`) usa o mesmo `LICITA_INTERFACE_CONFIG` da
auditoria de interface. Confere dados e composição em 1280, 1062 e 390 px, temas
claro/escuro e regras automatizadas de acessibilidade:

```bash
PLAYWRIGHT_CHANNEL=chrome API_PROXY_TARGET=http://127.0.0.1:8000 LICITA_INTERFACE_CONFIG=../data/diagnostico/11/config.json npx playwright test --project=painel-live
```

## Detalhe do item sinalizado

A lupa do painel e os links de itens do ranking abrem `/ranking/:id`, mantendo
base, execução e modelo. A tela consulta o item, a compra e os scores existentes;
não executa inferência. Os valores globais da compra são identificados separadamente
do total do resultado do item. Fornecedores e modelos não têm seus scores combinados.

A comparação mostra a mediana e o tamanho do treino registrados com o modelo,
preço unitário estimado e homologado. O Autoencoder mostra as parcelas disponíveis
do erro de reconstrução; contribuição por atributo do Isolation Forest permanece
indisponível. Documentos usam links oficiais e o relatório mantém processo/base/execução.
A revisão humana é indicada como não registrada; persistência de pareceres e lista
individual de exemplos históricos ainda não estão disponíveis nessa tela.

Verificação com API real, a partir desta pasta e com o servidor acessível:

```bash
LICITA_INTERFACE_CONFIG=../data/diagnostico/11/config.json PLAYWRIGHT_CHANNEL=chrome npx playwright test --project=detalhe-live
```

O arquivo local de configuração segue o formato `{ "base": "UUID", "execucao": "UUID", "routes": [["painel", "/painel?base_id=UUID&execucao_id=UUID"]] }`.

## Licitações Sinalizadas

O menu abre `/licitacoes`, com uma linha por compra, órgão, valor total homologado
e quantidade de itens importados/com análise. A execução publicada ativa e o
roteamento dos modelos são selecionados automaticamente. Busca, ordenação e
sinalização múltipla ficam visíveis; opções avançadas e indicadores numéricos de
IF não aparecem na listagem.

As linhas usam a média das medidas IF dos itens analisados: verde abaixo de 0,50,
amarelo de 0,50 a menos de 0,70 e vermelho de 0,70 a 1. Cada item tem o mesmo peso;
sem análise não recebe zero. Licitações sem IF ou com `Requer validação` ficam
neutras. A validação é marcada quando uma ocorrência da compra tem preço unitário
mais de 500% acima da mediana do mesmo produto/unidade na base atual. Ela não é
propagada às compras com preços regulares do mesmo produto.

A lupa abre `/licitacoes/:id`, com resumo e itens paginados. Clicar no item abre
a análise salva e permite voltar à licitação. Os filtros selecionam compras
inteiras; a média do detalhe usa todos os itens importados, independentemente
da pesquisa ou página atual. Valores globais e dos itens importados são
identificados separadamente. O back-end precisa carregar as novas rotas
`/api/v1/visao/licitacoes` e `/api/v1/visao/licitacoes/:id`.

A comparação no detalhe identifica separadamente a unidade da mediana histórica
e a unidade registrada no item. Unidades ausentes permanecem “Não informada”.
A unidade do grupo não é inferida da descrição do item atual.

As listagens de produtos, licitações e fornecedores usam busca, ordenação e
seleção múltipla das cinco sinalizações. A análise publicada ativa é automática;
seletores de versão e opções avançadas ficam fora dessas listagens.

### Fornecedores

`/fornecedores` mostra uma linha por fornecedor, com compras, total homologado e
itens analisados no formato “3 de 14 analisados”. As cores usam o maior IF dos
resultados do próprio fornecedor. A marcação de preço extremo também pertence ao
resultado vencedor, sem ser propagada aos covencedores com preço regular.
O clique no nome expande a linha com animação e lista as compras por órgão, com
o total homologado exclusivamente para esse fornecedor em cada compra, sem IF.
A lista expandida inclui todas as compras, independentemente da paginação dos itens.
A lupa abre `/fornecedores/:id`, com resumo, participação por órgão e itens
paginados. A busca seleciona fornecedores inteiros, sem reduzir seus totais.

Números exibidos usam até duas casas decimais; valores monetários usam pelo
menos duas. O arredondamento é apenas de apresentação e preserva inteiros acima
do limite seguro de JavaScript. Valores não nulos que arredondariam para zero
mantêm as casas necessárias; HHI usa até quatro casas. Preços unitários e
medianas têm o valor original no tooltip. Banco, cálculos, respostas da API,
filtros numéricos e exportação CSV conservam a precisão original. O PDF usa o
mesmo arredondamento visual e informa também preços unitários e medianas originais.

## Interface e responsividade (revisão de UX)

- **Escala automática:** todo o CSS usa `rem`. Acima de 1500 px de largura o tamanho-base da página cresce (1500, 1800, 2200 e 2800 px), então a interface ocupa bem monitores grandes e projetores sem ficar com letra pequena. O conteúdo tem largura máxima e fica centralizado.
- **Pontos de quebra:** 1200 px (colunas empilham), 900 px (menu vira gaveta), 820 px (KPIs em 2 colunas) e 720 px (tabelas viram cartões com rótulos, via `tbl-stack` e `data-label`).
- **Menos ruído:** o seletor de versão da análise é uma linha que abre em “Alterar”; filtros mostram só busca e ordenação, e o resto fica em “Mais filtros”; o aviso de limitações é uma linha com “Ver limitações”.
- **Pop-up “Como funciona”:** três passos com atalhos, aviso de que anomalia não é prova, glossário e créditos. Textos em `src/data.js` (`passos`, `glossario`).
