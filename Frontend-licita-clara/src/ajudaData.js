export const grupo = 'CodeGators'
export const githubGrupo = 'https://github.com/CodeGators'
export const desenvolvedores = [
  { nome: 'Anderson Fontes', papel: 'Scrum Master', user: 'Anderson-Fontes' },
  { nome: 'Stefan Souza', papel: 'Product Owner', user: 'Stefan0212' },
  { nome: 'Gustavo Silva', papel: 'Desenvolvedor', user: 'GustavoReis-xml' },
  { nome: 'Arthur Augusto', papel: 'Desenvolvedor', user: 'ArthurAugusto10' },
  { nome: 'Rafael Shinji', papel: 'Desenvolvedor', user: 'RafaelShinjiTomokame' },
  { nome: 'Rodrigo Augusto', papel: 'Desenvolvedor', user: 'rodrigoaslima' },
]
export const passos = [
  { t: 'Veja o panorama', to: '/painel', cta: 'Abrir o Painel geral', d: 'O Painel destaca itens para conferir e compara o preço unitário com a mediana histórica de similares. Selecione um item para ver fornecedor, órgão e unidade da referência.' },
  { t: 'Abra um item sinalizado', to: '/ranking', cta: 'Ver itens sinalizados', d: 'Compare o preço homologado com a mediana de itens parecidos e entenda a medida IF.' },
  { t: 'Leve o relatório', to: '/relatorios', cta: 'Preparar relatório', d: 'Escolha uma compra e baixe em PDF ou CSV, com valores, fontes e limitações. Não precisa de login.' },
]
export const glossario = [
  ['Medida IF', 'Saída original do Isolation Forest, de 0 a 1. Maior indica maior anomalia. Não é percentil nem probabilidade; grupos não têm calibração comum de gravidade.'],
  ['Mediana', 'O valor do meio entre os preços de itens parecidos usados no treino do modelo. Serve de referência; não é cotação atual.'],
  ['Preço ÷ mediana', 'Quantas vezes o preço pago passa da mediana. 1,6× quer dizer 60% acima.'],
  ['Homologado', 'Valor aprovado na contratação. Não prova pagamento nem entrega.'],
  ['Modelo', 'Método automático que procura comportamentos atípicos. Usamos o Isolation Forest e o Autoencoder, sempre separados.'],
  ['HHI', 'Mede a concentração de fornecedores num órgão, de 0 a 1. Quanto maior, mais concentrado. Concentração sozinha não indica irregularidade.'],
  ['Falso positivo', 'Item sinalizado que, depois de conferido, estava correto. Por isso toda conclusão depende de revisão humana.'],
]
