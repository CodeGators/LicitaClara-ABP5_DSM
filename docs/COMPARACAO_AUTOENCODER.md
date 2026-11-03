# Autoencoder e comparação acadêmica — etapa 06

Branch `feat/06-autoencoder-comparacao`. A entrega técnica de 05 foi integrada à `main` local em `0fafea5`, por autorização do usuário, preservando a branch. A revisão humana de 05 continua pendente; não houve push.

## Implementação e desenho

O Autoencoder é uma rede neural de reconstrução **2 → 1 → 2**, com sete parâmetros treináveis, implementada com `MLPRegressor` do scikit-learn já presente no ambiente. O alvo do treino é a própria entrada: dois atributos comprimidos num gargalo de um neurônio e reconstruídos em duas saídas. Não é uma regressão supervisionada com rótulo de irregularidade nem uma rede profunda.

Entradas: log(preço/mediana do treino) e log(1+quantidade), iguais às do IF multivariado. Mediana, média e desvio da padronização são ajustados apenas no treino. O artefato preserva a transformação, modelo, semente, IDs do treino, atributos e corte. Não há imputação, ajuste no holdout ou IDs tratados como números contínuos.

Arquitetura, solver, sementes, critérios de convergência/estabilidade e comparação foram escritos no [protocolo v1](validacao_nucleo/PROTOCOLO_AUTOENCODER_V1.md) antes de executar o Autoencoder real. O IF já era conhecido; o resultado é uma comparação retrospectiva no mesmo lote, não confirmação independente ou seleção de arquitetura pelo desempenho no holdout.

Cada uma das cinco sementes é treinada e imediatamente recarregada para reproduzir scores e parcelas do erro exatamente. Âncora fixa 42. Convergência de todas as sementes e estabilidade são condições técnicas, sem equivaler a utilidade. Atributo constante ou falta de coorte elegível é indisponibilidade/inconclusivo, não aprovação por flexibilizar os mínimos.

## Testar

Na raiz `LicitaClara-ABP5_DSM`, usando a configuração, PostgreSQL e objetos locais existentes:

```bash
uv run --locked --all-packages --extra validation pytest ml/tests/test_autoencoder.py -q
uv run --locked --all-packages --extra validation licita-ml comparar-modelos --manifesto-if validacao/isolation-forest/96ad887aa58bf0869845f784f2540f91512e41dbffd0cd29977832c253a0bcdc/manifesto.json --sha256-if 5c947b3d4882c8456b7648c2aec20ab26d3cba0cdedcd64772f4db6613ff11ae
```

O extra `validation` existente fornece as dependências: `uv sync --locked --all-packages --extra validation`. Não houve instalação de framework adicional. Em outra máquina, usar a chave e hash da avaliação IF produzida naquele ambiente; o clone do Git não contém dados e modelos locais.

O comando verifica manifesto IF, seus artefatos, dataset analítico e seus artefatos; reproduz política e confere grupos, IDs, cortes, mediana e regras. Reutiliza os scores IF congelados, sem retreinar o IF ou carregar seus pickles. Somente artefatos AE recém-gerados são carregados nesta etapa.

Repetição deve retornar o mesmo fingerprint com `reutilizada: true`, depois de verificar a integridade das entradas e saídas. Mudanças em fontes/hash, código, protocolo ou dependências geram outra versão; nenhuma saída divergente é sobrescrita. O manifesto é escrito por último e não há gravação de base/modelo/score em SQL. Registro SQL de treino e inferência permanecem em 07.

## Resultado real

Mesmo grupo `c2c61e3e795a3068`: **140 referências de treino, 35 de avaliação, top-k=4**. As cinco sementes do AE convergiram (54 a 107 iterações), e os scores/parcelas foram idênticos após recarga. Não foram alterados parâmetros para obter esse resultado.

| Modelo | Spearman mediano entre sementes | Jaccard mediano top-k | Conclusão técnica |
| --- | ---: | ---: | --- |
| IF preço | 0,8882 | 1,000 | estável neste recorte |
| IF preço/quantidade | 0,9826 | 1,000 | estável neste recorte |
| AE preço/quantidade | 1,0000 | 1,000 | estável e convergente neste recorte |

A correlação AE versus IF multivariado foi 0,4099, com três dos quatro casos compartilhados no top-k (75%, Jaccard 0,60). O AE não compartilhou casos do top-4 com a regra unilateral nem com a bilateral de preço. Isso descreve concordância/divergência, sem comprovar superioridade ou acerto. Os scores de algoritmos diferentes têm escalas e significados distintos; não são combinados nem comparados como probabilidades.

**Sensibilidade limitada ao aumento de preços:** nas 12 cópias elegíveis, triplicar somente o preço aumentou o score AE em 5/12 (41,67%); o deslocamento mediano foi negativo, -0,1497. Multiplicar por 10 aumentou em 10/12 (83,33%), com deslocamento mediano +0,3699. O erro de reconstrução não é monotônico em sobrepreço: aumentar preço pode aproximar um exemplo da relação aprendida e reduzir o erro. Sintéticos são teste de comportamento, não rótulos de fraude. Esse resultado negativo permanece registrado e impede tratar o AE como detector validado de sobrepreço.

Primeira comparação: 0,702 s, RSS máximo observado 210,46 MiB, incluindo leitura/verificação das entradas. O treino IF não foi repetido; não comparar esses 0,702 s ao tempo da grade IF como benchmark equivalente. O tempo individual de treino/avaliação AE também está no relatório. Medidas restritas ao processo/piloto, sem extrapolação para volume maior.

## Score e explicações

Score AE = média dos erros quadráticos dos dois atributos padronizados. Para cada caso, o arquivo reservado preserva os erros individuais e suas frações no erro total. São uma decomposição calculada desse score, sem atribuição causal, evidência de irregularidade ou explicação dos scores IF. Se o erro total for zero, a fração é indisponível.

O IF permanece sem explicação por contribuição calculada nesta entrega; não reaproveitar os pesos ilustrativos do protótipo. A publicação futura deve explicitar quais explicações estão implementadas e quais estão ausentes.

## Revisão conjunta e decisão

A nova amostra conjunta de avaliação contém **14 casos**: união dos top-k IF, AE e regras, mais controles. A amostra de treino mantém 20 casos. As planilhas não mostram scores, método ou posição; sua procedência fica em `reservado_rankings.json`. Amostras e pareceres anteriores foram preservados. O novo caso acrescentado pelo AE ainda não tem parecer; a ampliação não resolve independência ou disponibilidade documental.

O [guia de revisão](validacao_nucleo/GUIA_REVISAO_INDEPENDENTE.md) e as [alternativas sem revisor](AVALIACAO_ISOLATION_FOREST.md) continuam aplicáveis. Conferência interna deve ser identificada assim. Não preencher automaticamente os pareceres ou reaproveitá-los sem conferir IDs e contexto.

Para apurar cópias preenchidas, sem alterar originais:

```bash
uv run --locked --all-packages --extra validation licita-ml revisao-comparacao --manifesto CHAVE_MANIFESTO_COMPARACAO --sha256 SHA256_MANIFESTO_COMPARACAO --grupo c2c61e3e795a3068 --treino COPIA_TREINO.csv --avaliacao COPIA_AVALIACAO.csv
```

O comando rejeita alteração de IDs/contexto, duplicação, pareceres inválidos e conclusões sem identificação/data/justificativa/URL. Conserva pendentes e inconclusivos e o denominador original de cada top-k. Não verifica independência/autoria declaradas nem aprova vencedor automaticamente.

**Decisão:** comparação técnica concluída, utilidade inconclusiva por revisão pendente; sem vencedor validado e sem autorização de publicação como prioridade de auditoria. Não há acurácia, probabilidade de fraude ou superioridade demonstrada. IF e AE ficam disponíveis para demonstração acadêmica experimental separada. A etapa 07 precisará definir explicitamente política de eventual publicação experimental, base de treino correta e estados visíveis, preservando a ausência de validação humana.

Também não há confirmação temporal por lote posterior elegível. Snapshots atualizados depois do corte não são backtest ponto no tempo. A estabilidade atual e a coerência dos hashes não eliminam essas limitações.

## Artefatos e evidência

Manifesto: `validacao/comparacao/0bb0b4ed27d165a1df33b28f3360778fb64f2722a579896851be07bc49aad98f/manifesto.json`.
SHA-256: `50ed84657addcc7f05ef104ae0df373eca0ef0ea689c6a7672820fb32bfe7e64`.

Em armazenamento local, artefatos ficam sob `data/objects/` nessa chave: cinco modelos AE, manifesto de treino preservado, protocolo, CSVs e scores/parcelas reservados. As cópias editáveis das duas planilhas estão em `data/validacao_etapa06/0bb0b4ed27d165a1df33b28f3360778fb64f2722a579896851be07bc49aad98f/revisao_treino.csv` e `revisao_avaliacao.csv` no mesmo diretório. Não foram preenchidos pareceres; apuração real confirmou 20/14 pendentes e denominador 4 para cada ranking.

Validação: **143 testes Python aprovados**, zero falhas/skips, incluindo oito testes AE/comparação; lint e formatação aprovados (109 arquivos). Cobrem ausência de dados, atributos constantes, datas futuras no treino, escalas restritas ao treino, recarga, integridade, pareamento dos IDs, não convergência e revisão sem aprovação automática. Frontend não foi alterado e seus testes browser/build não foram repetidos.

Preservados: contagens das 34 tabelas, duas bases de consulta, 233 arquivos dos ensaios, `.env` e 18 objetos/cópias anteriores do IF. Nenhum modelo ou score foi inserido em SQL. Evidências: [resultado agregado](diagnostico/conclusao_etapa06.json).
