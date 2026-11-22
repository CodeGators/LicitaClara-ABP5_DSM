# Workflows

`python-ci.yml` instala pelo `uv.lock`, verifica lint e formatação e executa os
testes Python com PostgreSQL descartável. As credenciais do YAML valem somente
para o job de CI. Também verifica os comandos de versão do coletor e da ML.

`frontend-ci.yml` instala com `npm ci`, executa os testes do cliente HTTP e de
navegação Playwright com respostas controladas e gera o build Vite em Node.js
20.19.0. Testes com a API real dependem de uma base populada e são executados
separadamente com `npm run test:live`.

Os workflows são acionados por alterações nos caminhos listados em cada YAML.
Não há coleta automática nem publicação da aplicação nesses jobs.
