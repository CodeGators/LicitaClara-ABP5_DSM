# Front-end — Licita Clara

Aplicação React com Vite, React Router e lucide-react. Todas as telas de negócio
consultam a API; as páginas demonstrativas e os dados fictícios foram removidos.

## Instalação e execução

Use Node.js 20.19+ da linha 20. Para instalar e preparar o projeto completo,
incluindo banco e treinamento, siga o [README principal](../README.md).

Com a API disponível na porta 8000, execute nesta pasta:

```bash
npm ci
npm run dev
```

A aplicação abre em `http://localhost:5173`. No desenvolvimento, o Vite encaminha
`/api` para `http://127.0.0.1:8000`. Para outro destino, configure
`API_PROXY_TARGET` no `.env` desta pasta. Para o build, `VITE_API_URL` pode apontar
para a URL pública da API até `/api/v1`; configure também o CORS do backend.
Nenhuma credencial deve ser colocada nas variáveis públicas do Vite.

```bash
npm run build
```

## Telas e navegação

| Rota | Conteúdo |
| --- | --- |
| `/painel` | Indicadores da base e comparação de preços dos itens priorizados. |
| `/ranking` | Itens Sinalizados: produtos agrupados por catálogo, especificação e unidade. |
| `/ranking/:id` | Detalhe de uma ocorrência do item: preços, fornecedor e compra vinculada. |
| `/licitacoes` | Licitações Sinalizadas, com valores e cobertura de análise. |
| `/licitacoes/:id` | Resumo da licitação e seus itens paginados. |
| `/processos/:id` | Dados da compra importada e links para seus itens. |
| `/fornecedores` | Fornecedores, totais e compras na expansão de cada linha. |
| `/fornecedores/:id` | Resumo, participação por órgão e itens do fornecedor. |
| `/relatorios` | Prévia e exportação da compra em PDF ou CSV. |

A entrada `/` abre `/ranking`. Os endereços antigos `/itens` e `/itens/:id`
redirecionam para as telas correspondentes de `/ranking`, preservando parâmetros.
As rotas `/demonstracao/*` não existem mais.

As listagens de produtos, licitações e fornecedores usam busca, ordenação e
seleção múltipla das cinco sinalizações. A execução publicada ativa é selecionada
automaticamente. Detalhes podem manter uma execução explícita na URL. Não há
botão de treinamento, autenticação ou registro de revisão na interface.

## Preços e sinalizações

Em Itens Sinalizados, mínimo, máximo e mediana são calculados sobre os resultados
não cancelados da base operacional atual. A mediana não é ponderada pela
quantidade. Unidades e especificações diferentes permanecem separadas.
O detalhe do item pode apresentar a mediana histórica usada pela análise;
essa referência é distinta da mediana da base atual.

Cada ocorrência na expansão mostra sua própria sinalização. As faixas visuais
usam o IF bruto: abaixo de 0,50, menor anomalia; de 0,50 a menos de 0,70,
anomalia intermediária; de 0,70 a 1, maior anomalia. Preço acima de seis vezes
a mediana operacional recebe “Requer validação”. Ausência de IF recebe
“Sem análise disponível”, sem substituir a medida por zero.

O fundo do produto segue o nível de anomalia com mais ocorrências. Empates usam
o maior nível. Ocorrências que requerem validação ou não têm análise não votam;
sem votos, o fundo fica neutro. Os filtros das três faixas usam a predominância;
os de validação e ausência de análise incluem produtos com qualquer ocorrência
nessas condições, sem esconder as outras compras do grupo.

As licitações usam a média das medidas máximas por item, excluindo ausências.
Os fornecedores usam a maior medida de seus próprios resultados. Não é uma
probabilidade de irregularidade. Na expansão do fornecedor, cada valor inclui
somente os resultados desse fornecedor naquela compra, sem exibir IF.

O botão “Gerar relatório da licitação” seleciona a compra em Relatórios. A
exportação inclui os itens importados da compra, não apenas o item aberto.
Não há abas de documentos ou revisão no detalhe do item.

Valores monetários e percentuais de comparação usam duas casas na apresentação;
valores pequenos não nulos conservam casas quando o arredondamento os zeraria.
Cálculos, respostas da API e CSV preservam a precisão original. Medidas IF
exibidas nas telas técnicas e relatórios usam quatro casas.

## Verificação

```bash
npm test
npx playwright install chromium
npm run test:e2e
npm run build
```

`npm test` valida o cliente HTTP, números e links. `test:e2e` usa respostas
controladas da API para navegação, erros, filtros e acessibilidade. Para usar
Chrome já instalado, prefixe os comandos Playwright com `PLAYWRIGHT_CHANNEL=chrome`.

Com a API e uma base populada, execute `npm run test:live`. As verificações visuais
adicionais usam os projetos `interface-live`, `detalhe-live` e `painel-live` e a
variável `LICITA_INTERFACE_CONFIG`, que aponta para um JSON local com `base`,
`execucao` e `routes` (pares de nome e URL). Saídas de teste ficam fora do Git.
