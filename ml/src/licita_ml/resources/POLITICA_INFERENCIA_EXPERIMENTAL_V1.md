# Política de inferência e publicação experimental — v1

Registrada antes da execução local da etapa 07 em 03/11/2026. A comparação técnica de IF/AE não comprovou utilidade, não concluiu revisão humana independente e não é backtest ponto no tempo. Esta política não autoriza apresentar scores como risco validado ou probabilidade de fraude.

- Registrar a base real de treino em `versoes_base`, com `recorte.tipo=treino_modelo`, manifesto e Parquet contendo somente as referências efetivamente usadas. Ela é um registro de dataset de modelagem, sem importação artificial de processos/itens. As consultas operacionais devem excluí-la inclusive quando o UUID é informado explicitamente.
- Registrar apenas âncoras técnicas aprovadas da comparação congelada: IF preço/quantidade (200 árvores, min(256,n), semente 42) e AE semente 42. Verificar hashes, código/dependências compatíveis, IDs/cortes/mediana, e reproduzir os scores de avaliação antes de registrar. Carregar apenas artefatos gerados pela aplicação no armazenamento privado; nunca oferecer upload ou carregamento de pickle por HTTP.
- A inferência exige dataset de atributos explícito, verifica seus artefatos e recalcula atributos contra a base SQL validada. Referências de treino e mediana devem coincidir com o treino registrado. Não treinar, recalibrar ou imputar na inferência. Sem vínculo exato e grupo compatível, resultado conhecido/data/unidade/quantidade suficientes, registrar motivo de indisponibilidade, não score zero.
- Unidade do score: resultado por fornecedor, preservando item/processo/base. Múltiplos vencedores não são somados ou escolhidos arbitrariamente. Permitir múltiplos resultados-modelo por item por meio de FK composta que impeça cruzar resultado/item/base. Cancelados e itens sem resultado mantêm ausência explícita.
- Score bruto IF = -score_samples; score AE = erro médio quadrático de reconstrução no espaço padronizado congelado. Índice normalizado = 100 × proporção dos scores de treino <= score observado (CDF empírica, versão `cdf-treino-v1`), arredondado a 0,001. É posição em relação ao treino do mesmo modelo/grupo, sem calibração de risco; não comparar magnitudes brutas entre algoritmos. Preservar a calibração do treino e seus hashes.
- Não há faixas alta/média/baixa validadas. Prioridade de auditoria permanece indisponível. Não combinar IF/AE. O IF multivariado é a referência experimental predefinida para eventual ordenação, sem alegação de superioridade. Scores dos resultados ficam separados; eventual resumo de item deve identificar o máximo no mesmo modelo e cobertura parcial. **Não calcular score de processo**; registrar ausência de política de agregação em todos os processos.
- Explicação AE: parcelas aditivas = erro quadrático por atributo / 2, cuja soma é o score bruto. Frações do erro total são indisponíveis se total zero. Não são causas ou contribuições ao índice normalizado. IF: contribuição por atributo indisponível, sem pesos fictícios. Mediana, treino, fontes e atributos observados são contexto rastreável, não explicação causal.
- Criar execução com snapshot de configuração e cobertura de todos os itens/resultados. Persistir registro de treino/modelos, vínculos, scores, parcelas e avaliações de processo em uma transação; somente marcar `concluida` depois da reconciliação. Falha desfaz o lote e marca execução `falhou`, mantendo publicação anterior. Repetir retoma sem duplicar; execução concluída não é reescrita. Serializar preparação/inferência/publicação com o lock existente.
- Ativação é comando separado, só para execução completa/reconciliada. Canal permitido nesta versão: `experimental:{base_id}`. Trocar ativa em uma transação preservando publicações e execuções antigas. Não ativar canal de auditoria validada. Semântica pública atual `analise.nao_publicada` continua referente à ausência de publicação de auditoria validada; consultas experimentais são endpoints explícitos e sempre sinalizadas.
- API de leitura permite listar publicações/execuções publicadas e consultar itens/resultados por execução/base explícitas. Publicações anteriores continuam acessíveis pelo ID; nunca misturar modelos ou bases pela seleção silenciosa da mais recente. Falhas/execuções não publicadas não são servidas como resultados públicos.
- No piloto atual pode haver cobertura zero por falta de comparabilidade: é um resultado legítimo, que deve permanecer visível. Não fabricar inferência positiva ou expandir agrupamentos para preencher telas. Testes de sucesso usam exemplos controlados em schemas descartáveis, separados das evidências reais.

## Contrato temporal ML-05

A inferência temporal recebe o diretório privado ML-04 e seu SHA-256 explícito,
valida os artefatos, código/dependências, dataset, âncoras e replay de treino e
avaliação. Reutiliza mediana, escala e CDF de treino, sem fit. Referências de
preços pontuadas são exportadas separadamente de resultados operacionais SQL.

`--resultado-ate` cria um lote operacional com corte de resultados explícito,
igual ou posterior ao corte de aplicação original. Preserva a janela de compras,
treino, avaliação e arquivos ML-03/04. Somente o impedimento isolado
`RESULTADO_POSTERIOR_AO_CORTE` pode ser reavaliado quando o resultado é conhecido
até o novo corte. Outros motivos permanecem impeditivos. A nova configuração e
os motivos originais ficam no manifesto; isso não é retreino nem backtest ponto
no tempo, nem autoriza recalcular métricas de avaliação com a aplicação.

Para persistir score de resultado SQL, exigir identidade oficial de compra,
item e fornecedor, preço, quantidade e data de resultado coincidentes com uma
referência elegível, especificação, catálogo, unidade/embalagem concordantes,
situação informada, compra não excluída, ausência de cancelamento e de moeda
estrangeira. Divergências de data não são corrigidas automaticamente. Embalagem
expressa como `Caixa 5000,00 UN` só concorda com CX de capacidade 5000 e medida
UN; não converter o preço para unidade nem aceitar outra capacidade.
