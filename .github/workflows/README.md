# Workflows

`python-ci.yml` valida instalação pelo `uv.lock`, lint, formatação, testes unitários e integração com PostgreSQL descartável. As credenciais no YAML existem apenas durante o job de CI.

O workflow está preparado no repositório; sua execução no GitHub depende de publicação/push. Não há workflow de coleta ou implantação nesta etapa.

`frontend-ci.yml` instala o frontend com `npm ci` e gera o build Vite usando Node.js 20.19.0. É acionado por alterações em `Frontend-licita-clara/` ou no próprio workflow. Não publica a aplicação nem substitui testes de navegação. Os comandos de ambos os workflows foram verificados localmente; execução remota não foi realizada nesta entrega.
