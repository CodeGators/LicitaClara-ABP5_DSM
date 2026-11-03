# Base e atributos analíticos — etapa 04

Política `atributos-v1`, registrada em 03/11/2026 antes da execução operacional sobre o histórico real desta entrega. Branch: `feat/04-base-atributos-analiticos`. Complementa o [plano](PLANO_CONCLUSAO.md) e preserva os [ensaios anteriores](validacao_nucleo/RESULTADO.md).

## Escopo e unidades

O coletor registra o histórico da pesquisa de preços como aquisições operacionais, com URLs, hashes, respostas originais e observações no PostgreSQL. A preparação analítica produz Parquets e manifesto imutáveis no armazenamento de objetos. Não cria outra base validada para a API, não muda seu recorte ativo, não treina modelos e não publica scores.

Há duas entidades no dataset:

- **Referência histórica:** chave compra + ID da referência do item + fornecedor + forma. Usada para ajustar/evaluar atributos de preço/quantidade. Os IDs abreviados SHA-256 preservam a associação aos casos dos ensaios.
- **Resultado operacional:** resultado de fornecedor vinculado ao item e processo de uma base explícita. Itens sem resultado conhecido recebem uma linha de indisponibilidade. Resultados múltiplos não viram um único preço arbitrário.

A base operacional identifica os alvos da aplicação, enquanto as aquisições históricas identificam o universo de treino. **Não são a mesma base nem coberturas equivalentes.** Antes de persistir um modelo na etapa 05/07, registrar corretamente a versão da base de treino e seu manifesto; não usar o UUID do pequeno piloto como se descrevesse o histórico completo. A modelagem atual aceita score de item/processo, não score por resultado; uma política explícita de agregação continua necessária na etapa 07.

## Comparabilidade e resolução

- Grupo: CATMAT + descrição detalhada normalizada em caixa/acentos/pontuação + unidade de fornecimento + capacidade + medida. Ordem de palavras e conteúdo são preservados; não há similaridade textual ou equivalência inferida.
- Zero de capacidade em UN é código conhecido da fonte, não divisor. Caixas/embalagens com capacidade ausente ou não positiva são rejeitadas. Não converter CX em UN.
- Identificadores textuais preservam zeros. Identificadores numéricos já truncados pela origem não têm zeros reconstruídos; conservar o original e exigir vínculo exato no alvo operacional.
- Preços positivos e quantidades não negativas usam Decimal/NUMERIC(28,8). Ausência não vira zero; NaN, infinito, negativos e precisão incompatível são rejeitados.
- Versões usam atualização do item e da compra, nessa ordem. Timestamps com offset são comparados em UTC; valores sem fuso permanecem locais sem inventar offset. Mistura sem/com fuso entre versões exige rejeição, não precedência presumida.
- Empate divergente rejeita o grupo de versões; repetições equivalentes e versões superadas têm contagem própria. Nenhuma versão é escolhida pelo preço.
- Proveniência histórica aponta arquivo registrado, página, ordinal e hash da resposta original. Proveniência operacional aponta arquivo/importação/membro/ordinal do snapshot já importado.
- [Exclusões documentais v1](analitica/exclusoes_v1.json) suspendem os dois casos já diagnosticados: detector de falsidade em papel-moeda e destaca-texto verde agrupados como amarelo. A política é copiada e tem hash no manifesto; não altera arquivos/ensaios anteriores.

Igualdade estrutural não garante condições comerciais equivalentes. Frete, marca, entrega e especificação efetiva do treino ainda precisam de revisão documental. A etapa não converte corroboração estrutural em aprovação de comparabilidade.

## Cortes e suficiência previamente definidos

Para o exercício real: histórico 01/10/2025–30/09/2026, treino até 30/06/2026, avaliação julho–setembro/2026. O comando exige datas explícitas; as regras abaixo são versionadas no manifesto.

- `dataCompra` define período/partição; `dataResultado` deve existir e ser menor ou igual ao fim da respectiva partição. Resultados posteriores não entram retroativamente no treino ou na avaliação.
- Compra observada no período de treino é excluída da avaliação, inclusive se reaparecer em outro grupo. A identificação conservadora da compra não é relaxada quando sua referência de treino foi segregada.
- Mais de cinco referências elegíveis por compra/grupo/partição são segregadas para investigação de cobertura. Ausência de quantidade impede uso no coorte de preço+quantidade.
- A mediana requer pelo menos 20 referências e dez compras no treino. É congelada no fim do treino; não usa preços da avaliação.
- Elegibilidade técnica do grupo principal: pelo menos 100 referências/20 compras no treino, 30 referências/dez compras na avaliação, três órgãos e três fornecedores no treino, e no máximo 10% das referências de treino por compra.
- Esses mínimos são operacionais do piloto, não garantia estatística universal ou aprovação de publicação. Grupos insuficientes continuam documentados; não reduzir mínimos para obter aprovação.
- Revisões de origem posteriores ao corte são contadas, não apagadas. Mesmo com controle da data de resultado, o snapshot adquirido depois não comprova disponibilidade histórica de todos os campos; `snapshot_ponto_no_tempo` permanece falso.

Na fase de ajuste, a mediana do conjunto de treino é pré-processamento ajustado naquele conjunto, não uma previsão em cada data de compra do treino. A avaliação posterior usa somente essa referência congelada. Para um alvo operacional anterior ao fim do treino, não reutilizar uma mediana de treino que ainda não estaria disponível.

## Atributos, fórmulas e ausências

Cada atributo exportado tem `valor`, `motivo` quando indisponível e metadados necessários. Decimais permanecem strings/Decimal até a transformação numérica explicitada; logaritmos são floats finitos calculados só a partir de valores válidos.

| Atributo | Fórmula / granularidade | Ausência ou limite |
| --- | --- | --- |
| `preco_mediana` histórico | Preço unitário da referência / mediana do grupo de treino | Grupo insuficiente, unidade/especificação incompatível, exclusão documental ou data inválida/posterior ao corte |
| `log_preco_mediana` | ln(preço/mediana) | Mesmos controles da razão; não é dinheiro nem score |
| `log_quantidade` | ln(1 + quantidade conhecida) | Quantidade ausente fica nula; zero conhecido gera log zero |
| Diferença estimado/homologado | (preço unitário homologado − estimado unitário) / estimado unitário, por resultado | Unidade ou preço ausente; estimativa não positiva; resultado cancelado ou fora do corte |
| Número de participantes | Identificadores distintos das propostas do item | Só calculado com cobertura completa comprovada; duas propostas de uma empresa não são duas empresas; cobertura do piloto não é completa |
| Frequência fornecedor–órgão no recorte | Processos distintos com resultado do fornecedor no mesmo órgão, dentro da janela e base | Não representa todos os contratos do órgão; data desconhecida no universo torna o atributo indisponível |
| HHI do órgão no recorte | Soma dos quadrados das participações de todos os fornecedores no total homologado do universo | Cancelados excluídos; total desconhecido ou denominador não positivo não gera soma parcial nem HHI zero |
| Frequência/HHI completos do órgão | Exigiriam universo completo do órgão | Indisponíveis: essa cobertura não foi comprovada no piloto |
| Publicação–assinatura | Dias entre publicação do processo e assinatura contratual explicitamente vinculada | Não usar vigência como assinatura; sem vínculo/data ou com vários contratos sem política, fica indisponível |

Janela de frequência/HHI: 365 dias anteriores à data do resultado-alvo, sem o próprio dia e sem a compra atual. Mesma data sem ordem intradiária comprovada não é usada como passado. Datas de resultado, período do arquivo e publicação são dimensões distintas. O universo é **todos os resultados não cancelados do mesmo órgão presentes na base selecionada**, não apenas sinalizados ou o fornecedor selecionado. O manifesto/contexto da linha identifica esse recorte e sua cobertura parcial.

O HHI retorna também total, quantidade de fornecedores e participações. Frequência zero significa nenhuma compra observada naquele universo explícito, não inexistência de contratos na realidade. HHI de universo vazio fica nulo. Pagamento, contrato assinado e homologação não são equivalentes.

Uma comparação de preço operacional exige referência com ID oficial do item, catálogo, fornecedor, especificação, unidade, quantidade e preço compatíveis, resultado conhecido até a data do alvo e corte posterior ao treino. Mesmo assim permanece marcada como comparabilidade documental não verificada. Nenhum resultado atual herda análise de uma referência sem vínculo demonstrado.

Categorias e identificadores ficam como contexto: não tratar CNPJ, código de órgão ou CATMAT como variáveis numéricas contínuas. Codificação, escalas e imputações futuras devem ser ajustadas exclusivamente no treino e salvas com o modelo na etapa 05. Não completar atributos ausentes para satisfazer a interface.

## Comandos operacionais

Na raiz, com PostgreSQL/configuração existentes. Preservar `.env`, dados e volume. Há snapshots dos ensaios nesta máquina; em outra instalação é necessário adquiri-los ou usar o modo online explicitamente.

Registrar os históricos locais, sem rede:

```bash
uv run --locked --all-packages --extra validation licita-collector historico-material --inicio 2025-10-01 --fim 2026-09-30 --catalogo 486374 --cache data/validacao_nucleo
uv run --locked --all-packages --extra validation licita-collector historico-material --inicio 2025-10-01 --fim 2026-09-30 --catalogo 486054 --cache data/validacao_nucleo
```

Guardar os `arquivo_id` retornados. A competência do registro histórico identifica o mês final da consulta, não afirma que todas as linhas sejam desse mês. Se metadados antigos não têm data da coleta, ela permanece desconhecida; o registro operacional de agora não é uma observação retroativa. Uma repetição pode acrescentar observação de coleta, mas reutiliza o mesmo conteúdo/ID do arquivo.

Sem `--cache`, o comando acessa a API oficial de pesquisa de preços pelo CATMAT e período, com os limites de aquisição já implementados. Não executar modo online para fingir reprodução do snapshot antigo.

Preparar atributos (IDs desta instalação; em outra, usar os retornados pelo coletor):

```bash
uv run --locked --all-packages --extra validation licita-ml atributos --base-id a21534e3-e1a9-5d31-9a4e-c3beb608914f --historicos b37a76e6-5e63-419e-8657-e169e22f1f92 454cf8ee-66bc-4838-80d5-13d3f966934e --inicio 2025-10-01 --treino-fim 2026-06-30 --fim 2026-09-30 --exclusoes docs/analitica/exclusoes_v1.json
```

O `base-id` acima é o piloto desta instalação; em outro ambiente selecionar a base operacional validada correspondente. Os UUIDs são entradas explícitas, sem seleção silenciosa da aquisição mais recente.

Os arquivos ficam em `analitica/base={fingerprint}/` no armazenamento configurado: Parquet de referências, Parquet de resultados operacionais, rejeições JSONL, política de exclusões, cópia do manifesto operacional e manifesto analítico. Em armazenamento local, ficam sob `data/objects/`, fora do Git.

O fingerprint usa fontes/IDs/hashes, política, código, ambiente Arrow/Python, exclusões e hash do manifesto da base operacional. O manifesto é gravado por último; sua existência com checksums válidos confirma o dataset. Repetir verifica originais/artefatos e reutiliza o mesmo fingerprint; corrupção gera erro. Arquivo novo, mudança de regra ou fonte gera outra versão. Escrita usa lock de preparação e não sobrescreve conteúdo divergente sob a mesma chave.

O preparo normal `licita-ml preparar` exclui o namespace `historico/` da seleção automática: esses arquivos não devem transformar a base de consulta por acidente. A nova aquisição/preparação não modifica ensaios, modelos ou pareceres existentes.

## Verificação e medidas

```bash
uv run --locked --all-packages --extra validation pytest ml/tests/test_analytical.py collector/tests/test_api.py collector/tests/test_database_collection.py -q
uv run --locked --all-packages --extra validation pytest -q
uv run --locked --all-packages --extra validation ruff check .
uv run --locked --all-packages --extra validation ruff format --check .
```

Testes de integração usam schemas descartáveis no banco `_test`, incluindo precisão Parquet, reexecução, corrupção de fonte/artefato e permissões separadas. Exemplos conhecidos: HHI de 75%/25% = 0,625; duas linhas da mesma compra contam uma contratação observada; estimativa zero não é denominador; vigência não substitui assinatura.

Limites atuais: 100 páginas/100 MiB por aquisição JSON conforme configuração; leitura analítica de até 20 mil referências históricas e 20 mil registros por tabela operacional. Não extrapolar consumo do pequeno piloto para anos/categorias sem nova medição. Tempo, RSS e bytes são registrados na primeira geração do manifesto.

## Resultado local

Das 658 entradas, 641 foram normalizadas e 17 rejeitadas. Nos diferentes grupos há 360 linhas de treino, 126 de avaliação e 155 excluídas; não formam uma única coorte comparável.

Somente o grupo `c2c61e3e795a3068` atingiu os mínimos técnicos: treino de 140 linhas/118 compras e avaliação de 35 linhas/34 compras; mediana de treino R$ 0,87. Os ensaios antigos permanecem intactos. Há 193 snapshots atualizados após o corte e duas referências suspensas documentalmente. Motivos podem se sobrepor; não somar como registros distintos.

O piloto gerou 10 alvos. Não há vínculo/especificação suficientes para transferir a mediana histórica com segurança. Participantes completos, contratos e universo integral do órgão não estão comprovados. Ausências têm motivo por atributo.

Primeira geração: 1,427 s; RSS máximo observado de 117,11 MiB; 2.311.906 bytes de fontes e 145.031 bytes de artefatos. A repetição retornou `reutilizada: true`. Medidas restritas ao piloto.

Fingerprint: `1cf57448a5cba11ccfb4def6318a836110ac50c32f60c48c23bf258073832374`. [Evidência agregada](diagnostico/conclusao_etapa04.json). Comparabilidade documental e utilidade continuam não aprovadas; snapshots não representam observação ponto no tempo.
