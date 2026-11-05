# Licita Clara — Frontend

Vite + React 18 + React Router + lucide-react. Consulta real de itens, detalhe, processo e documentos integrada à API. Painel, fornecedores, revisão e relatório demonstrativos permanecem separados e identificados; as demonstrações usam `src/data.js`.

Usar Node.js 20.19+ da linha 20 e npm. A partir desta pasta:

```bash
npm ci
npm run dev     # http://localhost:5173
npm run build
```

Entrada `/` → `/itens`. Detalhes reais em `/itens/:id` e `/processos/:id`. Demonstrações em `/demonstracao/painel`, `/demonstracao/itens`, `/fornecedores` e `/relatorios`.
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
seleção de itens para comparar resultados dos modelos. “Filtros e versão da
análise” fica recolhido; o botão do período abre essa configuração. Ordenação e
paginação permanecem nas listas, sem controles sem efeito na visão consolidada.

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
