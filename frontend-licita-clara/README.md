# Licita Clara — Frontend (protótipo acadêmico)

Vite + React 18 + React Router + lucide-react. Dados 100% simulados (`src/data.js`).
Análise de anomalias **por item** comprado. Modo claro/escuro e layout responsivo (celular).

```bash
npm install
npm run dev     # http://localhost:5173
npm run build
```

Telas: `/` Painel geral · `/processos` (lista de itens sinalizados) · `/processos/:id` (detalhe do item) · `/fornecedores` · `/relatorios?item=ID`.
Tokens de cor em `src/styles.css` (`:root` e `[data-theme=dark]`).
