# Licita Clara — Frontend (protótipo acadêmico)

Vite + React 18 + React Router + lucide-react. Dados 100% simulados (`src/data.js`).

Usar Node.js 20.19+ da linha 20 e npm. A partir desta pasta:

```bash
npm ci
npm run dev     # http://localhost:5173
npm run build
```

Telas: `/` Painel geral · `/processos` · `/processos/:id` · `/fornecedores` · `/relatorios`.
Tokens de cor/tipografia em `src/styles.css` (`:root`), seguindo a proposta de identidade (Inter, #102D46, #087F83...).

O frontend incorporou a entrega de 01/11/2026 da equipe. A integração com a API, revisão persistente, paginação e exportação real seguem no [plano de conclusão](../docs/PLANO_CONCLUSAO.md). Compilar não comprova funcionamento desses fluxos. O botão de exportação atual abre a impressão do navegador; a opção CSV ainda não gera CSV.
