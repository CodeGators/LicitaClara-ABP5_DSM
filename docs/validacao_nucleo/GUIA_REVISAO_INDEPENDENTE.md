# Guia para revisão independente dos casos

Usar a planilha `data/validacao_nucleo/revisao_assistida/dossie_revisao_independente.csv`. Salvar uma cópia para cada revisor. Ela contém 18 casos, links para a compra no PNCP, número do item e documentos/páginas localizadas. Não contém scores, posições ou indicação de método. Não ler a tabela de rankings, os achados do assistente ou a procedência reservada antes de registrar os pareceres.

A finalidade é verificar se cada caso merece análise adicional, não concluir que houve fraude. A equipe deve acordar os critérios antes de preencher. Aplicar o mesmo procedimento a todos os casos; não selecionar apenas os mais chamativos. Registrar nome do revisor, data e versão da planilha em arquivo separado, sem alterar os identificadores.

## Para cada caso

1. Abrir a compra e confirmar o número do item e o resultado. Conferir fornecedor quando necessário para distinguir múltiplos resultados. Resultado homologado não comprova entrega ou pagamento.
2. Conferir a especificação efetiva no termo, edital e eventuais retificações: função do produto, material, cor, tamanho e outras exigências. Código de catálogo igual não garante equivalência.
3. Conferir unidade e embalagem, incluindo quantidade por caixa. Não converter sem evidência explícita nem tratar preço de caixa como preço de unidade.
4. Conferir quantidade, preço homologado, datas e condições de entrega/frete. Não confundir estimativa com resultado. Quantidade grande ou pequena não é, isoladamente, irregularidade.
5. Registrar o que foi possível confirmar e as limitações, com URL e página. Se usar referência de preço externa, documentar grupo, período e condições; não escolher uma única referência conveniente.

## Parecer e evidência

Preencher `parecer_humano`, `justificativa` e `evidencia_url`:

- `comparavel_e_justificavel`: condições e referência de comparação verificadas, sem razão documental identificada para investigação adicional;
- `requer_verificacao`: razão concreta e descrita para investigação adicional, sem afirmar fraude; a justificativa deve ir além de “é um outlier”;
- `erro_dado_ou_unidade`: inconsistência apoiada em evidência;
- `nao_comparavel`: especificação ou condições não equivalentes;
- `inconclusivo`: documentação ou referência insuficiente.

Documento faltante deve permanecer inconclusivo, não virar “regular”. Não atribuir parecer com base apenas no preço maior ou na quantidade. Separar a confiança nos dados da interpretação econômica. Se possível, obter duas revisões sem contato entre revisores e discutir divergências depois de preservar os pareceres individuais.

## Comparação após concluir os pareceres

Somente depois da revisão, cruzar os IDs com a procedência dos rankings. Definir previamente se erros de dados contam como utilidade para triagem de qualidade de dados; não misturá-los com indícios de sobrepreço ou irregularidade. Informar separadamente casos úteis, dados inconsistentes, não comparáveis e inconclusivos em cada top-k, preservando o denominador original.

No lote pequeno, diferenças de um ou dois casos têm grande incerteza. Não chamar o resultado de precisão de fraude, e não ajustar o modelo repetidamente sobre os mesmos pareceres para declarar sucesso. Este dossiê auxilia a avaliação acadêmica; não constitui conclusão de auditoria.
