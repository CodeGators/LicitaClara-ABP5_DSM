export const itens = [
  { id: 'LC-2026-0142', nome: 'Notebook i5 / 16 GB / SSD 512 GB', cat: 'Equipamentos de informática', orgao: 'Instituto Vale Azul', forn: 'Nexo Suprimentos Ltda.', valor: 480000, qtd: 40, razao: 1.6, part: 2, score: 92, rev: 'A revisar' },
  { id: 'LC-2026-0087', nome: 'Luva cirúrgica descartável (cx. 100 un.)', cat: 'Material hospitalar', orgao: 'Fundação Serra Clara', forn: 'Prisma Insumos Ltda.', valor: 312000, qtd: 2400, razao: 1.48, part: 3, score: 89, rev: 'Em análise' },
  { id: 'LC-2026-0219', nome: 'Manutenção preventiva de ar-condicionado', cat: 'Serviços de manutenção', orgao: 'Agência Riacho Novo', forn: 'Órbita Serviços Ltda.', valor: 265000, qtd: 530, razao: 1.42, part: 1, score: 86, rev: 'A revisar' },
  { id: 'LC-2026-0104', nome: 'Cadeira ergonômica giratória', cat: 'Mobiliário administrativo', orgao: 'Instituto Vale Azul', forn: 'Nexo Suprimentos Ltda.', valor: 198000, qtd: 220, razao: 1.35, part: 2, score: 83, rev: 'A revisar' },
  { id: 'LC-2026-0316', nome: 'Licença de software de escritório (anual)', cat: 'Licenças de software', orgao: 'Fundação Serra Clara', forn: 'Vértice Digital Ltda.', valor: 156000, qtd: 300, razao: 1.29, part: 4, score: 78, rev: 'Em análise' },
  { id: 'LC-2026-0278', nome: 'Papel sulfite A4 (resma 500 fls.)', cat: 'Material de escritório', orgao: 'Agência Riacho Novo', forn: 'Ponto Sul Comercial', valor: 94000, qtd: 8000, razao: 1.24, part: 3, score: 74, rev: 'A revisar' },
]
export const razaoTxt = r => r.toFixed(2).replace('.', ',') + '×'
export const derivar = p => {
  const unitHom = Math.round(p.valor / p.qtd)
  const unitMed = Math.round(unitHom / p.razao)
  const estimado = Math.round(p.valor / 1.143 / 1000) * 1000
  const base = [['LC-2026-0051', 'Fundação Serra Clara', 0.96, 6], ['LC-2026-0093', 'Agência Riacho Novo', 1, 5], ['LC-2026-0120', 'Instituto Vale Azul', 1.05, 7]]
  return {
    unitHom, unitMed, estimado, unitEst: Math.round(estimado / p.qtd), auto: p.score - 4,
    pctSobre: Math.round((p.razao - 1) * 100),
    faixa: [Math.round(unitMed * 0.9), Math.round(unitMed * 1.09)],
    similares: base.map(([id, orgao, f, part]) => ({ id, orgao, preco: Math.round(unitMed * f), part })),
  }
}
export const distribuicao = [280,220,160,140,140,90,70,52,56,40]
export const evolucao = [['Jan',9],['Fev',12],['Mar',16],['Abr',14],['Mai',21],['Jun',24]]
export const fornecedores = [
  { nome:'Nexo Suprimentos Ltda.', orgaos:3, altos:6, contratos:24, valor:'R$ 6,20 mi', score:92 },
  { nome:'Prisma Insumos Ltda.', orgaos:2, altos:4, contratos:18, valor:'R$ 4,80 mi', score:89 },
  { nome:'Órbita Serviços Ltda.', orgaos:3, altos:3, contratos:16, valor:'R$ 3,40 mi', score:86 },
  { nome:'Vértice Digital Ltda.', orgaos:2, altos:0, contratos:12, valor:'R$ 2,90 mi', score:78 },
  { nome:'Ponto Sul Comercial', orgaos:4, altos:0, contratos:21, valor:'R$ 1,70 mi', score:74 },
  { nome:'Lúmen Materiais Ltda.', orgaos:2, altos:0, contratos:9, valor:'R$ 1,20 mi', score:62 },
]
export const participacao = [
  { orgao:'Instituto Vale Azul', pct:42, info:'R$ 3,36 mi · 18 contratos', hhi:'0,31' },
  { orgao:'Fundação Serra Clara', pct:23, info:'R$ 1,84 mi · 4 contratos', hhi:'0,22' },
  { orgao:'Agência Riacho Novo', pct:12.5, info:'R$ 1,00 mi · 2 contratos', hhi:'0,18' },
]
export const brl = v => 'R$ ' + v.toLocaleString('pt-BR')
export const nivel = s => (s >= 80 ? 'alta' : s >= 50 ? 'media' : 'baixa')
export const nivelNome = { alta:'Alta', media:'Média', baixa:'Baixa' }

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
  { t: 'Consulte os itens', to: '/itens', d: 'Explore os dados oficiais importados. Filtre por descrição, órgão, fornecedor, período e valor; abra um item para consultar os resultados e documentos da compra.' },
  { t: 'Veja o Painel', to: '/painel', d: 'Confira a cobertura da análise, a distribuição dos índices e a evolução dos itens no recorte selecionado. Ausência de análise permanece identificada.' },
  { t: 'Explore o Ranking experimental', to: '/ranking', d: 'Consulte os itens ordenados pelos índices disponíveis e abra o detalhe. Cada item é comparado com seu próprio grupo; o índice não é um score da licitação inteira.' },
  { t: 'Confira os resultados do item', to: '/itens', d: 'No detalhe do item, compare preços e veja os resultados de cada fornecedor e modelo separadamente. Abra o processo para consultar sua cobertura e os documentos conhecidos.' },
  { t: 'Explore os Fornecedores', to: '/fornecedores', d: 'Consulte compras com resultado, contratos vinculados e participação no gasto dos itens filtrados. Abra um fornecedor para ver suas relações por órgão.' },
  { t: 'Prepare o Relatório', to: '/relatorios', d: 'Selecione uma compra, confira a prévia, escolha PDF ou CSV e exporte. Os arquivos reais incluem valores, análises disponíveis, fontes e limitações; não exigem login.' },
]
export const glossario = [
  ['Score', 'Índice de anomalia relativo ao treino do modelo e ao grupo do item. Não mede probabilidade de irregularidade; não some índices de grupos diferentes.'],
  ['Prioridade', 'As faixas baixa, média e alta aparecem apenas nas demonstrações. A consulta real não atribui prioridade validada de auditoria.'],
  ['Mediana', 'Valor central do grupo usado no treino. Exige especificação, unidade e embalagem comparáveis; não é uma cotação atual.'],
  ['Preço / mediana', 'Quantas vezes o preço do item é maior que a mediana dos similares. 1,60× significa 60% acima.'],
  ['HHI', 'Índice de concentração de 0 a 1 no universo filtrado. Valores maiores indicam concentração entre os fornecedores observados, sem representar todo o órgão.'],
  ['Homologado', 'Valor aprovado na contratação; não comprova pagamento ou entrega.'],
  ['Isolation Forest e Autoencoder', 'Modelos não supervisionados que identificam comportamentos atípicos. Nas telas reais, os modelos treinados analisam os grupos compatíveis e seus resultados ficam disponíveis por versão.'],
  ['Falso positivo', 'Item sinalizado que, após revisão, está correto. Por isso toda conclusão exige revisão humana.'],
]
