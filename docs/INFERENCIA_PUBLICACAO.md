# Inferência e publicação versionada — etapa 07

Branch `feat/07-inferencia-publicacao`. A etapa 06 foi integrada à `main` local em `e9223b0`, preservando sua branch, por autorização do usuário. Sem push.

## O que foi entregue

- Registro de dataset de treino real, âncoras IF/AE e calibração, sem usar o piloto de consultas como se contivesse o treino.
- Inferência em lote com dados/modelos explícitos, reexecução sem duplicação, cobertura de todos os itens/resultados e retomada após falha.
- Scores por resultado/fornecedor, preservando múltiplos vencedores, com FK composta resultado/item/base na migração `0005_resultados`.
- Explicações AE por parcelas de erro calculadas e contribuição IF explicitamente indisponível.
- Publicação atômica em canal experimental por base, preservando versões anteriores; cinco endpoints de leitura com base e execução explícitas.

A [política experimental v1](POLITICA_INFERENCIA_EXPERIMENTAL_V1.md) foi escrita antes da execução local. **Não há aprovação de utilidade, prioridade de auditoria validada ou probabilidade de fraude.** Revisão humana e confirmação temporal permanecem pendentes.

## Treino, modelos e integridade

`versoes_base` agora também registra datasets de modelagem com `recorte.tipo=treino_modelo`. Seu manifesto e Parquet contêm somente as referências realmente usadas no treino, com origem, IDs, preços, quantidades, datas e hash. Não são processos/itens importados artificialmente: o registro identifica um dataset em objetos. `qualidade.entidades_dominio_sql=false` explicita isso. As consultas operacionais excluem esse tipo, inclusive se seu UUID for informado diretamente.

`versoes_modelo.base_treino_id` aponta para esse registro. São aceitas somente âncoras tecnicamente elegíveis da comparação congelada. Antes da carga dos artefatos, o processo verifica manifestos/hashes, compatibilidade do código da comparação e dependências. Depois confere classe, atributos, mediana, corte e reprodução exata dos scores da avaliação. Preserva também a calibração calculada exclusivamente no treino. Modelos são carregados apenas pelo CLI de processamento, do armazenamento privado gerenciado pela aplicação; não há endpoint de upload ou execução de pickles enviados por usuários.

O operador deve manter o armazenamento e as credenciais privados. Um SHA-256 detecta alteração de conteúdo em relação ao manifesto fixado, mas não torna um pickle arbitrário confiável. Não registrar manifestos/artefatos recebidos de terceiros fingindo que foram produzidos pela aplicação. Mudança de código/dependências incompatível exige avaliação/registro versionados, sem contornar a verificação.

A inferência lê o manifesto de atributos indicado, verifica todos os artefatos, reproduz política e recalcula atributos contra o snapshot SQL/base operacional. Referências de treino, valores e mediana devem coincidir com o treino congelado. Não ajusta modelos, escalas ou referências na avaliação/inferência. Limites atuais: 20 mil linhas por tabela/recorte da preparação, até 40 mil pares alvo/modelo na inferência e manifesto de até 64 MiB; ampliar exige nova medição.

## Scores, comparação e explicações

IF: `-score_samples`. AE: erro quadrático médio de reconstrução nos dois atributos padronizados. Persistência decimal: score bruto em 12 casas; índice em três casas. A CDF usa o score antes do arredondamento: para reproduzir empates nas últimas casas, usar modelo/atributos/calibração congelados, não apenas o número exibido. O manifesto também preserva atributos e calibração para reprodução.

`cdf-treino-v1`: índice = 100 × fração dos scores de treino menores ou iguais ao observado. Exemplo conhecido: treino `[1,2,2,4]`, observado `2` → `75.000`. É posição descritiva em relação ao treino do mesmo modelo/grupo, sem calibração como risco ou probabilidade. Não combinar magnitudes IF/AE nem escolher faixas de prioridade pelo protótipo.

Cada resultado por fornecedor tem score próprio. O vínculo composto impede cruzar resultado/item/base. Cancelamento, falta de resultado, data, unidade, embalagem ou comparação exata geram ausência com motivo. A execução preserva também os pares alvo/modelo sem score e itens sem resultado. Um item com parte dos pares disponíveis recebe estado `parcial`; o contrato devolve os resultados separados. Não foi implementado um score agregado de item ou processo. Prioridade é nula, e cada processo tem avaliação `nao_analisado` com `SEM_POLITICA_AGREGACAO_PROCESSO`.

A mediana/grupo, referência histórica exata, número de exemplos e manifesto do treino ficam nos atributos do score por resultado. Essas comparações atravessam datasets por manifesto; não inserir referências históricas em `comparacoes_referencias` fingindo que pertencem à base operacional. Os vínculos FK dessa tabela continuam preservados. A API retorna o contexto rastreável junto aos resultados.

No AE, cada `fatores_sinalizacao.contribuicao` é erro quadrático do atributo / 2; sua soma reproduz o score bruto dentro do arredondamento decimal. Frações do erro total ficam no observado e são nulas quando o total é zero. Isso não é causa, contribuição ao índice normalizado ou explicação do IF. Para IF, a resposta traz `METODO_ATRIBUICAO_IF_NAO_IMPLEMENTADO`, sem pesos fictícios.

## Transações, reexecução e ativação

Preparação/inferência/publicação usam o lock global existente. A execução é registrada com configuração/cobertura imutáveis; treino, modelos, vínculos, scores, parcelas e avaliações de processo são gravados numa única transação. Somente após reconciliar IDs, valores, explicações e cobertura o status vira `concluida`. Falha desfaz o lote, marca execução `falhou` e permite retomar a mesma versão sem duplicação. Artefatos de execução são imutáveis e verificados novamente ao reutilizar.

Ativar é um comando separado, permitido somente para execução experimental concluída/reconciliada. A publicação usa o nome `experimental:{base_id}`; desativar a anterior e ativar a nova ocorre numa transação. Falha na troca conserva a anterior ativa. É possível reativar uma execução antiga completa, mantendo os registros históricos. Não há canal de auditoria validada autorizado nesta versão.

As consultas antigas conservam `analise.status=nao_publicada` no sentido de **nenhuma publicação de auditoria validada**. Resultados experimentais são consultados explicitamente nas rotas abaixo. A interface real ainda não os consome; essa integração é a etapa 08. Não interpretar a ativação experimental como validação acadêmica/humana ou como autorização de risco validado.

## Executar nesta instalação

Na raiz `LicitaClara-ABP5_DSM`, com PostgreSQL/configuração/objetos existentes. Não sobrescrever `.env` e não recriar volumes. A migração adiciona uma coluna/FK e ajusta constraints, mantendo as 34 tabelas:

```bash
uv run --locked --all-packages --extra validation alembic upgrade head
uv run --locked --all-packages --extra validation pytest ml/tests/test_inference.py -q
uv run --locked --all-packages --extra validation licita-ml inferir --comparacao validacao/comparacao/0bb0b4ed27d165a1df33b28f3360778fb64f2722a579896851be07bc49aad98f/manifesto.json --sha256-comparacao 50ed84657addcc7f05ef104ae0df373eca0ef0ea689c6a7672820fb32bfe7e64 --atributos analitica/base=1cf57448a5cba11ccfb4def6318a836110ac50c32f60c48c23bf258073832374/manifesto.json --sha256-atributos ee8d1220f7758f746bb2c1ac1fce3754269bfa6af7a13dadbd24e501f42ed480
```

A migração já foi aplicada nesta instalação; repetir `upgrade head` é idempotente. Repetir a inferência deve retornar `reutilizada: true`, mesma execução e manifesto. Em outra instalação, usar chaves/hashes produzidos naquele ambiente, não copiar UUIDs sem os objetos correspondentes. O clone não inclui dados/modelos privados. A migração bloqueia downgrade se houver scores vinculados a resultados, evitando descarte silencioso de histórico.

Ativar a execução local (já ativada no canal experimental nesta entrega):

```bash
uv run --locked --all-packages --extra validation licita-ml publicar-experimental --execucao c680b7ea-196d-59db-93c7-03f6c7aaebb4
```

Esperado ao repetir: `publicada_experimental`, `reutilizada: true`. Não confundir esse comando local com deploy ou push ao GitHub.

## API e teste manual

Reiniciar a API se estiver executando código antigo:

```bash
uv run --locked --all-packages --extra validation uvicorn licita_backend.main:create_app --factory --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Abrir Swagger http://127.0.0.1:8000/docs. Usar base `a21534e3-e1a9-5d31-9a4e-c3beb608914f` e execução `c680b7ea-196d-59db-93c7-03f6c7aaebb4`.

| GET | Resultado |
| --- | --- |
| `/api/v1/analises/publicacao?base_id=UUID` | estado do canal experimental e execução ativa; sem publicação, `nao_publicada` |
| `/api/v1/analises/execucoes?base_id=UUID` | páginas de execuções publicadas, inclusive versões desativadas |
| `/api/v1/analises/execucoes/{execution_id}?base_id=UUID` | modelos/treino, versão/política, manifesto e contagens |
| `/api/v1/analises/execucoes/{execution_id}/itens?base_id=UUID` | página de itens com cobertura, motivos e scores separados por resultado/modelo |
| `/api/v1/analises/execucoes/{execution_id}/itens/{item_id}?base_id=UUID` | mesma página com um único item (ID estável de item, não versão) |

Todas exigem base explícita; ausência/UUID inválido gera 422. Base/execução cruzada, não publicada ou item inexistente retorna 404. `pagina`/`tamanho_pagina` estão disponíveis nas listas, tamanho máximo 100. Não há HTTP de escrita/publicação; API não carrega modelos nem altera os dados de análise. Versão anterior publicada segue acessível por ID após a troca ativa. Se trocar a publicação, o cliente deve preservar a execução escolhida na navegação.

## Resultado real e limitações

Nesta máquina há duas versões de registro do mesmo treino de 140 referências e quatro versões de modelo (duas âncoras: IF multivariado e AE, sob duas versões do código de inferência). Não são 280 referências distintas nem quatro algoritmos. Duas execuções/publicações experimentais foram preservadas no histórico, e somente a final está ativa. As duas bases operacionais anteriores e seus registros foram preservados; `/base/status` continua na base operacional mais recente, com dez itens. O registro de treino não soma cobertura de consultas.

A execução real concluiu com **dez itens, vinte pares alvo/modelo e zero scores elegíveis**. Motivos por par: oito `RESULTADO_ANTERIOR_AO_PERIODO`, oito `SEM_REFERENCIA_COM_VINCULO_E_ESPECIFICACAO_EXATOS` e quatro `SEM_RESULTADO_CONHECIDO`. Correspondem a quatro, quatro e dois alvos, respectivamente, sob dois modelos. Não representam vinte itens distintos. Na execução final, sete avaliações de processo mantêm score nulo por falta de política de agregação (catorze registros ao contar as duas execuções). Nenhum dado foi alterado para produzir scores positivos.

Manifesto: `inferencia/execucao=bfee2dc488f0cdffbf330e5385bfbccdf3b1df0b56d4a4a17e718aafa426fcb1/manifesto.json`, SHA-256 `4cc4f3db2f5c3021f91fb8f41d21c0f6c8974078c88d6e6ebbe5d6d566f9e44f` (24.723 bytes). Reexecução confirmou reutilização; publicação experimental e API com PostgreSQL/login restrito foram verificadas.

O caminho com scores IF/AE e parcelas AE foi testado com dados controlados em schemas `_test`: dois resultados no mesmo item, registros de treino corretos, recarga, erros de FK, falha/retomada do lote e falha na troca ativa. Essas evidências de implementação não são resultados reais do piloto nem evidência de utilidade.

**OK para inferência/publicação experimental rastreável; cobertura do piloto insuficiente para um ranking com scores.** Ampliar cobertura requer novas aquisições comparáveis e preparadas sob os critérios, sem remover restrições para preencher telas. Utilidade/revisão humana e confirmação temporal continuam inconclusivas. Não há deploy, score validado de auditoria ou teste browser da futura integração visual nesta etapa.

## Verificações da entrega

**146 testes Python aprovados**, sem falhas/skips, lint e formatação aprovados (117 arquivos). Os três cenários focados incluem várias verificações de banco, API restrita, FK, múltiplos fornecedores, retomada, ordenação independente dos alvos e ativação atômica. `alembic check` confirmou ausência de divergência entre schema e metadata. Diagramas regenerados: 34 tabelas e 65 FKs.

No banco real, sete consultas HTTP/ASGI com a identidade restrita foram conferidas, incluindo a publicação ativa, histórico, paginação, base operacional padrão e versão anterior por ID. Todas as linhas anteriores nas 34 tabelas, os 237 arquivos verificados e `.env` foram preservados. Artefatos/modelos de entrada foram verificados por hash. Servidores temporários externos não foram iniciados; o teste ASGI encerrou seu lifespan/engine.

Evidência agregada: [conclusao_etapa07.json](diagnostico/conclusao_etapa07.json). Testes browser/build não foram repetidos porque não houve mudança visual; a integração do canal experimental nas telas permanece em 08.
