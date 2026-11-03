# Avaliação versionada do Isolation Forest — etapa 05

Branch `feat/05-validacao-isolation-forest`. A etapa 04 foi integrada à `main` local em `3d7923c`; sua branch foi preservada. Não houve push.

## Escopo e interpretação

O comando `licita-ml validar-if` consome o manifesto analítico e seu SHA-256 explícitos, verifica os artefatos e recalcula a política antes de treinar. Não seleciona silenciosamente o dataset mais recente. Somente grupos elegíveis e linhas sem exclusões entram no ensaio. A base de consultas da API é preservada.

O [protocolo operacional](validacao_nucleo/PROTOCOLO_OPERACIONAL_V1.md) foi escrito antes da execução real. Mantém sementes, grade, âncora e critérios anteriores. Os dois modelos usam preço e preço/quantidade; regras unilateral e bilateral servem de comparação. Não há busca de hiperparâmetros para escolher o melhor resultado do teste. Os scores brutos ficam em arquivo reservado e não são convertidos em probabilidade ou escala de risco.

Cada avaliação tem fingerprint por dataset/hash, código, protocolo e dependências. Modelos, relatórios, treino, planilhas e procedência são imutáveis no armazenamento; manifesto escrito por último. Reexecutar verifica integridade e reutiliza. A recarga do modelo recém-gerado precisa reproduzir scores exatamente. Não carregar arquivos joblib recebidos de terceiros.

O manifesto de treino registra as referências realmente utilizadas, fontes, mediana e corte. Não atribui ao piloto operacional o histórico de treino. Nenhuma versão de modelo é inserida em SQL nesta entrega: antes da inferência/publicação, registrar a base correta e seu vínculo em `versoes_modelo.base_treino_id`. Nenhuma migração, consulta HTTP ou publicação é executada aqui.

## Testar nesta instalação

Na raiz `LicitaClara-ABP5_DSM`, com `.env`, objetos e PostgreSQL existentes:

```bash
uv run --locked --all-packages --extra validation pytest ml/tests/test_validation.py -q
uv run --locked --all-packages --extra validation licita-ml validar-if --manifesto analitica/base=1cf57448a5cba11ccfb4def6318a836110ac50c32f60c48c23bf258073832374/manifesto.json --sha256 ee8d1220f7758f746bb2c1ac1fce3754269bfa6af7a13dadbd24e501f42ed480
```

Em outra instalação, usar a chave e o SHA-256 retornados pelo preparo analítico. A aquisição de dados locais não faz parte do clone do Git. Em caso de ausência do extra de modelagem, instalar com `uv sync --locked --all-packages --extra validation`.

A execução retorna `manifesto` e `sha256_manifesto` da avaliação, `reutilizada` e a decisão. Sem pareceres completos, a decisão é `inconclusivo_por_revisao`. Esse status é um resultado da avaliação; não significa falha técnica do comando. Repetir deve manter o fingerprint e retornar `reutilizada: true`.

As saídas ficam em `data/objects/validacao/isolation-forest/{fingerprint}/` no armazenamento local. Em cada grupo:

- `modelos/`: artefatos das duas âncoras;
- `treino_manifesto.json`: IDs reais do treino, fontes e pré-processamento;
- `revisao_treino.csv`: amostra de 20 referências do treino;
- `revisao_avaliacao.csv`: união dos top-k e controles, sem método/score/posição;
- `reservado_rankings.json`: procedência e scores; não fornecer ao revisor antes dos pareceres.

As planilhas originais permanecem imutáveis. Fazer cópias para revisão; importar no editor com IDs como texto, preservando zeros. Cada revisor deve ter sua própria cópia e registrar nome e data. Reexecução não deve substituir pareceres.

Apurar cópias preenchidas (substituir campos em maiúsculas):

```bash
uv run --locked --all-packages --extra validation licita-ml revisao-if --manifesto CHAVE_MANIFESTO_AVALIACAO --sha256 SHA256_MANIFESTO_AVALIACAO --grupo GRUPO --treino CAMINHO_COPIA_TREINO.csv --avaliacao CAMINHO_COPIA_AVALIACAO.csv
```

O comando apenas lê as planilhas e imprime JSON. Pode-se guardar o resultado em arquivo novo por revisor; o resultado registra hashes das planilhas. IDs alterados/duplicados, categorias inválidas ou pareceres preenchidos sem identificação, justificativa, data ou URL são rejeitados. Pendentes e inconclusivos são mantidos; cada ranking conserva seu denominador original. O software não verifica autoria ou independência, nem aprova utilidade automaticamente.

## Que validação humana é necessária?

A revisão documental confere produto, unidade/embalagem, quantidade, preço, datas e condições comerciais nas fontes oficiais. Não é um parecer jurídico nem uma investigação de fraude. Usar o [guia de critérios](validacao_nucleo/GUIA_REVISAO_INDEPENDENTE.md), aplicando as mesmas categorias a todos os casos. A planilha desta etapa é uma nova amostra; o dossiê antigo de 18 casos não a substitui. Seus documentos podem auxiliar somente quando o ID corresponder.

Cada linha informa compra, item, fornecedor hash e localização exata no envelope histórico (arquivo, página e ordinal). Localizar o registro original para obter a identificação completa do fornecedor e suas chaves oficiais; consultar os módulos oficiais e anexos. Ausência de documento ou impossibilidade de confirmar equivalência deve ser `inconclusivo`. Não classificar pelo score ou por quantidade/preço isolados.

Uma pessoa da equipe ou professor pode revisar sem contato prévio com os rankings e achados. Se já conhece os resultados, a conferência serve como revisão interna e deve ser identificada assim. Não afirmar independência apenas porque o CSV não mostra scores.

## Caminho sem revisor independente

É possível concluir a comparação acadêmica técnica e documentar **utilidade inconclusiva por ausência de revisão independente**. Apresentar reprodução, estabilidade, sensibilidade e sobreposição com regras, incluindo resultados negativos. Se houver conferência interna, apresentá-la separadamente como qualidade de dados. Não preencher pareceres automaticamente, não declarar taxa de acerto e não publicar prioridade de auditoria como validada.

A amostra de treino não certifica todo o histórico. Revisões dos snapshots posteriores ao corte impedem chamar o ensaio de backtest ponto no tempo. A confirmação em período operacional posterior continua pendente por falta de lote elegível. Esses limites seguem para a comparação com Autoencoder e para a apresentação acadêmica; a aprovação do escopo acadêmico cabe ao professor.

## Evidências locais

Foi avaliado um grupo de 140 referências de treino e 35 de avaliação, com top-k=4. Ambas as âncoras passaram pelos critérios de estabilidade e reproduziram scores após recarga. Spearman mediano entre sementes: 0,8882 (preço) e 0,9826 (preço/quantidade); Jaccard mediano 1,0 em ambas. Cada top-4 do IF compartilha um caso com o top-4 unilateral e um com o bilateral (25%). Diferença de rankings não comprova superioridade.

A grade completa executou 40 ajustes: duas variantes, quatro configurações e cinco sementes. Não houve seleção de hiperparâmetros pelo resultado. Primeira geração final: 37,697 s; RSS máximo observado 225,35 MiB. Consumo medido neste processo/piloto, sem extrapolação para ampliação. Repetição confirmou reutilização e integridade.

Manifesto da avaliação: `validacao/isolation-forest/96ad887aa58bf0869845f784f2540f91512e41dbffd0cd29977832c253a0bcdc/manifesto.json`.
SHA-256: `5c947b3d4882c8456b7648c2aec20ab26d3cba0cdedcd64772f4db6613ff11ae`.
Grupo: `c2c61e3e795a3068`.

Foram criadas cópias locais para preenchimento em `data/validacao_etapa05/96ad887aa58bf0869845f784f2540f91512e41dbffd0cd29977832c253a0bcdc/revisao_treino.csv` e `revisao_avaliacao.csv` no mesmo diretório. Há 20 e 13 pareceres pendentes, respectivamente. Essas cópias e modelos são ignorados pelo Git. Preservar originais no armazenamento e separar cópias por revisor.

Apuração das cópias ainda vazias confirmou `revisao_pendente` e denominador 4 para cada ranking. Não há pareceres humanos preenchidos, aprovação de utilidade ou confirmação temporal. Consulte a [evidência agregada](diagnostico/conclusao_etapa05.json).
