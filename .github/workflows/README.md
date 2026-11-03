# Workflows

`python-ci.yml` valida instalação pelo `uv.lock`, lint, formatação, testes unitários e integração com PostgreSQL descartável. As credenciais no YAML existem apenas durante o job de CI.

O workflow está preparado no repositório; sua execução no GitHub depende de publicação/push. Não há workflow de coleta ou implantação nesta etapa.

`frontend-ci.yml` instala o frontend com `npm ci`, executa testes do cliente e navegação Playwright com respostas artificiais e gera o build Vite usando Node.js 20.19.0. É acionado por alterações em `Frontend-licita-clara/` ou no próprio workflow. Instala Chromium e dependências do sistema no runner. O teste com API real (`npm run test:live`) depende de base importada e é executado separadamente no ambiente local. Não publica a aplicação. Execução remota do workflow não foi realizada nesta entrega.
