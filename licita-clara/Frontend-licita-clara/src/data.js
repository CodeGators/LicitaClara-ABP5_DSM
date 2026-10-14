export const processos = [
  { id:'LC-2026-0142', cat:'Equipamentos de informática', orgao:'Instituto Vale Azul', forn:'Nexo Suprimentos Ltda.', valor:480000, razao:'1,60×', part:2, score:92, rev:'A revisar' },
  { id:'LC-2026-0087', cat:'Material hospitalar', orgao:'Fundação Serra Clara', forn:'Prisma Insumos Ltda.', valor:312000, razao:'1,48×', part:3, score:89, rev:'Em análise' },
  { id:'LC-2026-0219', cat:'Serviços de manutenção', orgao:'Agência Riacho Novo', forn:'Órbita Serviços Ltda.', valor:265000, razao:'1,42×', part:1, score:86, rev:'A revisar' },
  { id:'LC-2026-0104', cat:'Mobiliário administrativo', orgao:'Instituto Vale Azul', forn:'Nexo Suprimentos Ltda.', valor:198000, razao:'1,35×', part:2, score:83, rev:'A revisar' },
  { id:'LC-2026-0316', cat:'Licenças de software', orgao:'Fundação Serra Clara', forn:'Vértice Digital Ltda.', valor:156000, razao:'1,29×', part:4, score:78, rev:'Em análise' },
  { id:'LC-2026-0278', cat:'Material de escritório', orgao:'Agência Riacho Novo', forn:'Ponto Sul Comercial', valor:94000, razao:'1,24×', part:3, score:74, rev:'A revisar' },
]
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
export const similares = [
  { id:'LC-2026-0051', orgao:'Fundação Serra Clara', preco:7200, part:6 },
  { id:'LC-2026-0093', orgao:'Agência Riacho Novo', preco:7500, part:5 },
  { id:'LC-2026-0120', orgao:'Instituto Vale Azul', preco:7900, part:7 },
]
export const contribuicoes = [
  { nome:'Razão preço / mediana', val:'1,60×', sub:'60% acima dos itens comparáveis', pct:43 },
  { nome:'Participação no gasto do órgão', val:'42%', sub:'Nexo · HHI do órgão: 0,31', pct:27 },
  { nome:'Número de participantes', val:'2', sub:'Mediana dos similares: 6', pct:18 },
  { nome:'Publicação–contrato', val:'12 dias', sub:'Mediana dos similares: 28 dias', pct:12 },
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
  { t: 'Comece pelo Painel geral', to: '/', d: 'Veja a visão do semestre: quantos processos há no recorte, a distribuição dos scores e a evolução da alta prioridade. Clique nos cards do topo para abrir a lista correspondente.' },
  { t: 'Abra os Processos sinalizados', to: '/processos', d: 'Use a busca e as abas (Alta, Média, Todos) para encontrar os casos de maior score. Clique em uma linha para selecioná-la e em "Ver detalhe do processo" para abrir.' },
  { t: 'Leia o Detalhe do processo', to: '/processos/LC-2026-0142', d: 'Compare o preço com itens similares e veja quais atributos mais pesaram para o sinal. Passe o mouse nos ícones ? para ver o significado dos termos.' },
  { t: 'Explore os Fornecedores', to: '/fornecedores', d: 'Veja contratos, valores e a participação de cada fornecedor no gasto dos órgãos. Clique em um fornecedor da lista para ver os detalhes dele.' },
  { t: 'Registre a revisão humana', to: '/processos/LC-2026-0142', d: 'No fim do detalhe, escolha o status da análise e clique em "Registrar revisão". O histórico fica na aba "Registro da revisão".' },
  { t: 'Prepare o Relatório', to: '/relatorios', d: 'Escolha título, formato e seções, confira a prévia ao lado e exporte. O aviso de revisão humana sempre permanece.' },
]
export const glossario = [
  ['Score', 'Nota de 0 a 100 que indica a prioridade de análise de um processo. Não é probabilidade de fraude.'],
  ['Prioridade', 'Baixa (0–49), média (50–79) ou alta (80–100), conforme o score.'],
  ['Mediana', 'Valor do meio entre itens parecidos. Serve de referência para comparar preços.'],
  ['Preço / mediana', 'Quantas vezes o preço do processo é maior que a mediana dos similares. 1,60× significa 60% acima.'],
  ['HHI', 'Índice de concentração de 0 a 1: quanto maior, mais o gasto do órgão está concentrado em poucos fornecedores.'],
  ['Homologado', 'Valor final aprovado da contratação.'],
  ['Isolation Forest e Autoencoder', 'Modelos de aprendizado não supervisionado que apontam processos diferentes do padrão. Neste protótipo os valores são simulados.'],
  ['Falso positivo', 'Processo sinalizado que, após revisão, está correto. Por isso toda conclusão exige revisão humana.'],
]
