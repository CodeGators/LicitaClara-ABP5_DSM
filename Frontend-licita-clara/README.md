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

Instruções completas e resultados em [FRONTEND_CONSULTAS_REAIS.md](../docs/FRONTEND_CONSULTAS_REAIS.md). Revisão persistente, ranking e exportação real continuam no [plano de conclusão](../docs/PLANO_CONCLUSAO.md). O botão de exportação da demonstração abre a impressão do navegador; a opção CSV demonstrativa ainda não gera CSV.
