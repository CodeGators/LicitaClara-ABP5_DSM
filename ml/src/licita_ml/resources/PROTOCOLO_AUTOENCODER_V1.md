# Protocolo Autoencoder e comparação — v1

Registrado em 03/11/2026, antes do treino real desta etapa. Os resultados anteriores do IF já são conhecidos. Esta comparação é retrospectiva sobre o mesmo holdout, não uma nova confirmação independente. Nenhuma decisão abaixo será ajustada para superar o IF neste lote.

## Desenho fixo

- Entrada: manifesto da avaliação IF da etapa 05 e seu SHA-256 explícitos. Verificar todos os artefatos, o dataset analítico referenciado e seus hashes; reproduzir política, exclusões, mínimos e seleção dos mesmos IDs de treino/avaliação. Nenhuma linha excluída ou grupo insuficiente entra no modelo.
- Modelo: autoencoder neural pequeno, implementado com `sklearn.neural_network.MLPRegressor`, alvo igual à entrada. Arquitetura **2 → 1 → 2**, gargalo de uma unidade com tanh e saída linear; sete parâmetros treináveis. Esse desenho permite reconstrução comprimida com o pequeno treino, sem instalar outro framework ou assumir vantagem de rede profunda.
- Dois atributos idênticos aos do IF multivariado: log(preço/mediana do treino) e log(1+quantidade). Mediana e `StandardScaler` ajustados exclusivamente no treino; transformação congelada e preservada com o modelo. Nenhuma imputação, código de órgão ou fornecedor numérico.
- Solver L-BFGS, `alpha=0.001`, `max_iter=2000`, `max_fun=50000`, `tol=0.00001`; sementes 11, 23, 42, 71, 101, âncora fixa 42. Sem busca de arquitetura/hiperparâmetros, seleção por resultado do holdout ou early stopping com a avaliação. Registrar avisos de convergência, iterações, perda, recursos e versões. Treino com atributo constante impede o ensaio multivariado principal, sem imputar diversidade.
- Score = média dos dois erros quadráticos de reconstrução no espaço padronizado. Maior erro significa reconstrução pior, sem interpretação probabilística. Parcelas por atributo são erros quadráticos efetivamente calculados; sua fração no erro total não é causa, importância do IF ou evidência de irregularidade. Erro total zero tem participação percentual indisponível.
- Comparar todos os scores nas mesmas referências de avaliação, com desempate por ID. Usar o k, sementes e limites de estabilidade do protocolo IF: Spearman mediano >=0,80 e Jaccard mediano >=0,60. Sem correlações válidas, estabilidade é inconclusiva. Falha de convergência de qualquer semente impede aprovação técnica do AE; os resultados permanecem registrados, sem retreinar para obter aprovação.
- Comparação principal: AE versus IF preço/quantidade, por compartilharem entradas. IF preço isolado e regras unilateral/bilateral entram como referências adicionais. Reportar top-k, correlação e sobreposição; diferença de ranking não comprova utilidade. Não comparar numericamente magnitudes brutas dos scores de algoritmos diferentes e não calcular média deles.
- Sensibilidade: cópias de casos com razão de preço entre 0,8 e 1,2, multiplicando somente preço por 3 e 10; relatar deslocamento do score. Sintéticos não entram no ranking real nem recebem rótulo de fraude. Nenhuma meta de sensibilidade escolhida depois do resultado.
- Preservar modelo/pré-processamento, scores finitos e reprodução exata após recarga imediata de artefato recém-gerado. Não carregar joblib recebido de terceiros. Suficiência técnica do piloto não significa validade estatística geral.

## Revisão e decisão

Preservar amostra de treino e avaliação já preparada em 05. Para comparação conjunta, gerar nova planilha de avaliação sem scores/método, contendo a união dos top-k IF, AE e regras, mais até três controles por SHA-256 `['revisao-v1', id]`. Não sobrescrever planilhas anteriores ou pareceres. Mapeamento reservado permanece separado. A ampliação da amostra não cria revisão independente; pareceres antigos só podem ser reaproveitados com ID e contexto iguais, identificando sua origem.

Aplicar o mesmo guia de revisão documental. Sem revisão humana independente, registrar utilidade inconclusiva, inclusive se os dois modelos forem estáveis. Sem lote posterior elegível observado à época, confirmação temporal continua inconclusiva. Snapshots com atualizações posteriores ao corte não são backtest ponto no tempo.

Decisão operacional desta etapa: **não escolher um vencedor validado nem publicar prioridade de auditoria** sem evidência de utilidade. Preservar os algoritmos para demonstração acadêmica experimental, com seus limites e eventual reprovação técnica explícitos. Qualquer futura publicação experimental precisa de política própria, identificação do modelo e rastreabilidade; não é autorizada automaticamente pela estabilidade. Registro SQL de base de treino/modelo e inferência permanecem na etapa 07.

## Referências de implementação

- [MLPRegressor (scikit-learn)](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPRegressor.html): regressão com múltiplas saídas, ativações e solver L-BFGS. A escolha de treinar entrada → entrada com gargalo constitui o autoencoder deste projeto.
- [StandardScaler (scikit-learn)](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html): estatísticas ajustadas no treino e aplicadas posteriormente com `transform`.

A versão efetivamente instalada é registrada no manifesto e no lockfile; as páginas oficiais consultadas nesta etapa descrevem scikit-learn 1.9.1.
