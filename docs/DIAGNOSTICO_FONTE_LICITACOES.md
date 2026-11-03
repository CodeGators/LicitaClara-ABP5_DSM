# Diagnóstico inicial — licitações do Portal da Transparência

Data da verificação: 19/10/2026. Responsável: Codex, por execução local autorizada pelo usuário.
Etapa 01 do [checklist](TODO_IMPLEMENTACAO_BACKEND_E_DADOS.md).

> Atualização: a fonte complementar foi testada. Ver [DIAGNOSTICO_COMPRASGOV.md](DIAGNOSTICO_COMPRASGOV.md) para dados recentes, catálogo e recorte piloto. As pendências deste diagnóstico histórico devem ser lidas junto a essa atualização.

## Resultado e decisão inicial

O download automatizado do histórico funciona sem token nos dois arquivos testados. A amostra principal é março de 2024, com 2.653 licitações, 57.381 linhas de itens e 144.711 linhas de participantes. Abril foi baixado para conferir a competência mais recente listada.

A página consultada lista 136 competências, de janeiro de 2013 a abril de 2024. Isso é a disponibilidade anunciada nesta página nesta data, não uma comprovação de integridade de todas as competências. Não encontramos nela arquivos de 2025 ou 2026. Abril tem resultados somente de 01 a 05/04/2024 e não deve ser tratado como mês completo.

Esse pacote permite iniciar uma base histórica e explorar participantes e concentração de vencedores. Ele não oferece todos os atributos previstos no protótipo. Não iniciar carga ampla nem fechar esquema definitivo antes de tratar as limitações abaixo.

Fontes oficiais consultadas:

- [Página de downloads](https://portaldatransparencia.gov.br/download-de-dados/licitacoes).
- [Dicionário de dados](https://portaldatransparencia.gov.br/dicionario-de-dados/licitacoes).
- [Consulta de licitações](https://portaldatransparencia.gov.br/licitacoes/consulta), que também informa atualização até 05/04/2024.
- [Portal de dados abertos do Compras.gov.br](https://www.gov.br/compras/pt-br/cidadao/portal-de-dados-abertos/portal-de-dados-abertos), candidato a complementar unidades, preços, catálogo e dados recentes; endpoints e vínculos ainda não foram testados.

## Aquisição e reprodução

Os endpoints oficiais de competência responderam com redirecionamento para ZIP no domínio `dadosabertos-download.cgu.gov.br`:

- https://portaldatransparencia.gov.br/download-de-dados/licitacoes/202403
- https://portaldatransparencia.gov.br/download-de-dados/licitacoes/202404

Os originais e produtos locais estão em `data/diagnostico/`, ignorado pelo Git. Metadados de aquisição e estatísticas agregadas estão versionáveis em [diagnostico/perfil_licitacoes_202403_202404.json](diagnostico/perfil_licitacoes_202403_202404.json), sem linhas de pessoas/fornecedores. O manifesto contém URLs finais, instante de coleta UTC, tamanhos e SHA-256.

SHA-256 dos ZIPs observados:

```text
202403: 543f7df89d8c3489cfe0c321a9d046f9dbc5d8af4a2fb1d44b09b26734b35627
202404: 5090396018e2ab3a26bd8779373aab893f684a61b8c0f2df0e0a906f8383fcd7
```

Com os ZIPs no diretório, reproduzir o perfil a partir da raiz do repositório:

```bash
python3 collector/scripts/diagnosticar_licitacoes.py --entrada data/diagnostico
```

O script é exploratório: lê cada membro em memória, não extrai caminhos e não é o coletor de produção. A interpretação CP1252 lê os arquivos sem erro e preserva os acentos; o separador observado é ponto e vírgula, campos entre aspas e números com vírgula decimal. Essa compatibilidade não distingue inequivocamente CP1252 de outras codificações semelhantes. Datas não vazias testadas seguem `DD/MM/AAAA`.

Conversão opcional para medir Parquet, preservando colunas como strings e usando Zstandard:

```bash
uv run --locked --group diagnostics python collector/scripts/diagnosticar_licitacoes.py --entrada data/diagnostico --parquet
```

A medição em strings é apenas um baseline de armazenamento, não o esquema analítico final.

## Volume observado

| Competência | ZIP (bytes) | Licitações | Linhas de itens | Linhas de participantes | Empenhos |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024-03 | 2.803.662 | 2.653 | 57.381 | 144.711 | 0 |
| 2024-04 | 832.362 | 721 | 17.729 | 38.737 | 0 |

CSV descompactado total: março, 54.614.123 bytes; abril, 15.379.172 bytes. O arquivo de empenhos tem apenas cabeçalho em ambos. Não inferir ausência de empenhos reais a partir desse arquivo vazio.

Um cenário linear de 12 meses iguais a março ocuparia cerca de 33,6 MB de ZIP e 655,4 MB de CSV. É uma extrapolação de cenário, não previsão: meses, categorias e fontes têm distribuições diferentes. O custo PostgreSQL ainda precisa ser medido após importação, incluindo índices e versões. Não estimar banco a partir do ZIP.

## Arquivos, campos e relações

A lista integral de cabeçalhos e contagens de vazios está no JSON do perfil.

| Arquivo | Campos principais | Destino conceitual |
| --- | --- | --- |
| `Licitação` | Número Licitação, Código UG, Código Modalidade Compra, Número Processo, órgão, objeto, situação, UF/município, Data Resultado Compra, Data Abertura, Valor Licitação | Processos, órgãos, UGs e modalidades |
| `ItemLicitação` | Chaves do processo, Código Item Compra, descrição, quantidade, valor total, Código/Nome Vencedor | Itens e resultados/vencedores |
| `ParticipantesLicitação` | Chaves do processo, Código Item Compra, Código/Nome Participante, Flag Vencedor | Participações por item |
| `EmpenhosRelacionados` | Chaves do processo, Código Empenho, data, observação e valor | Empenhos, se houver registros em outras competências |

A UG deve ser preservada separadamente do órgão; não são identificadores intercambiáveis.

Chave candidata do processo: `(Código UG, Código Modalidade Compra, Número Licitação)`, sempre dentro da fonte. Nos dois meses ela é única. Todos os números de licitação observados têm nove dígitos; investigar a semântica do ano antes de decompor ou generalizar a chave para outras fontes. `Número Processo` não deve ser assumido globalmente único.

Todos os itens e participantes conseguem encontrar um processo pela chave candidata dentro da mesma competência. Isso não prova a unicidade global em todo o histórico.

O dicionário descreve código do item com 22 dígitos, mas nem todas as linhas obedecem ao formato. Preservar o valor original, registrar a inconsistência e evitar parsing obrigatório. Código de item não é um código de catálogo CATMAT/CATSER.

## Qualidade observada

| Verificação | Março | Abril |
| --- | ---: | ---: |
| Linhas de item sem código | 141 | 51 |
| Linhas de item com código vazio ou fora do formato de 22 dígitos | 223 | 64 |
| Duplicatas exatas em itens | 3 | 7 |
| Excesso de linhas sobre códigos de item distintos, incluindo vazios | 148 | 54 |
| Excesso de linhas sobre pares item/vencedor distintos | 92 | 26 |
| Duplicatas exatas em participantes | 118 | 41 |
| Excesso de linhas sobre pares item/participante distintos | 144 | 50 |
| Participações sem código correspondente no arquivo de itens da competência | 1.052 | 169 |
| Licitações com data de abertura vazia | 769 | 144 |
| Licitações com valor total igual a zero | 1.214 | 398 |

“Excesso sobre pares distintos” não equivale a duplicata comprovada: pode haver divergência de descrição ou outra granularidade. Inspecionar antes de remover. Os códigos vazios também afetam a contagem de itens distintos.

Os campos de quantidade e valor de item foram parseados como decimais em todas as linhas, sem valores negativos ou zero. As datas preenchidas passaram no parse. Não se verificou ainda a equivalência contábil entre soma de itens e valor total do processo; vários totais de licitação são zero. Não preencher o total automaticamente com outra medida sem documentar a semântica.

Há 182 códigos de órgão e 5.418 identificadores não vazios de vencedores distintos nas linhas de março; abril tem 127 e 2.392. Esses números são contagens de identificadores da fonte, sem validação cadastral. O cabeçalho real de participantes usa `Código Participante`; o dicionário consultado o chama de CNPJ. Não impor formato de CNPJ sem verificar os valores.

## Viabilidade dos atributos e das telas

| Informação/atributo | Situação nesta amostra | Ação |
| --- | --- | --- |
| Órgão, UG, modalidade, objeto e fornecedor vencedor | Disponível | Normalizar sem perder identificadores |
| Quantidade e valor total do item | Disponível | Preservar precisão; validar semântica e totais |
| Preço unitário | Derivável por valor/quantidade | Não comparar sem conhecer unidade e especificação |
| Participantes por item/processo | Derivável | Contar identificadores distintos e tratar linhas sem item correspondente |
| Frequência de vitória fornecedor–órgão | Derivável no recorte | Nomear como vitória/homologação, não contratos assinados |
| Participação e HHI | Derivável sob condições | Validar universo, valores e deduplicação; não chamar de gasto pago |
| Data do resultado e abertura | Disponível, abertura com ausências | Filtrar competência por resultado; não por abertura |
| Preço/mediana de itens equivalentes | Insuficiente para comparação confiável | Complementar catálogo, unidades e especificação |
| Valor estimado e desvio estimado/homologado | Indisponível como campos próprios | Buscar fonte complementar ou omitir |
| Unidade de medida e código CATMAT/CATSER | Indisponível como campos próprios | Buscar fonte complementar |
| Publicação–assinatura do contrato | Indisponível | Não substituir por abertura–resultado |
| Contratos e documentos completos | Indisponível neste ZIP | Validar fonte complementar e vínculo |
| Empenhos | Arquivo sem registros | Não apresentar métricas de empenhos |

Não construir modelo de sobrepreço usando descrições similares sem comprovar a equivalência dos itens. Um baseline limitado a estrutura de participação/concentração deve explicitar que não mede todos os sinais do protótipo.

## Encaminhamento

- Usar março de 2024 como competência técnica de desenvolvimento e abril como verificação da borda de cobertura.
- Recorte histórico candidato: abril de 2023 a março de 2024, ainda sujeito a amostragem de competências anteriores e à decisão sobre fonte complementar.
- Não escolher categoria de treinamento apenas por busca textual; faltam catálogo e unidade para definir comparabilidade. Categoria e período definitivo continuam pendentes no checklist.
- Antes de treinar comparação de preços ou implementar todos os campos do detalhe, diagnosticar os recursos oficiais do Compras.gov.br e validar ligações com esta fonte. Não alterar silenciosamente a fonte contratada no contexto.
- Próximo trabalho independente: preparar FastAPI e PostgreSQL local, com esquema operacional de coleta e contratos mínimos; adiar o esquema analítico definitivo até resolver as pendências.

Nenhuma conta de nuvem ou token foi necessário para este diagnóstico. Python 3.12.3, Docker 29.6.2 e Docker Compose v5.3.1 foram encontrados e responderam localmente. A instalação de dependências e a execução de serviços do projeto são etapas separadas.

## Medição Parquet executada

Conversão integral exploratória com PyArrow 23.0.1, colunas string e compressão Zstandard. Arquivos vazios também geram metadados Parquet.

| Competência | CSV total (bytes) | Parquet total (bytes) |
| --- | ---: | ---: |
| 202403 | 54.614.123 | 2.074.668 |
| 202404 | 15.379.172 | 715.893 |

Valores medidos não incluem o índice/esquema de um banco PostgreSQL. Tipos analíticos e esquema final podem alterar a compressão.
