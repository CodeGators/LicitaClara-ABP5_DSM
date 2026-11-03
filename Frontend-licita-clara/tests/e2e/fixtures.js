export const BASE = '11111111-1111-4111-8111-111111111111'
export const OTHER_BASE = '11111111-1111-4111-8111-222222222222'
export const PROCESS = '22222222-2222-4222-8222-222222222222'
export const ITEM = '33333333-3333-4333-8333-333333333333'
const secondItem = '33333333-3333-4333-8333-444444444444'
export const SUPPLIER = '44444444-4444-4444-8444-444444444444'
const ORGANIZATION = '55555555-5555-4555-8555-555555555555'
const MODALITY = '66666666-6666-4666-8666-666666666666'
const analysis = { status: 'nao_publicada', score: null, prioridade: null }
export const context = { id: PROCESS, processo_versao_id: 'snapshot-processo', fonte: 'teste', chave_oficial: '000001', numero_compra: '00001', numero_processo: null, numero_controle_pncp: null, objeto: 'Material de escritório', orgao_id: ORGANIZATION, orgao_nome: 'Órgão do recorte', modalidade_id: MODALITY, modalidade_nome: 'Pregão', data_publicacao: '2026-09-01' }
const result = { id: 'resultado-1', fornecedor_id: SUPPLIER, fornecedor_nome: 'Fornecedor do recorte', sequencial_resultado: 1, situacao: 'Informado', cancelado: false, quantidade_homologada: '1.00000000', valor_unitario_homologado: '0.10000001', valor_total_homologado: '0.10000001', data_resultado: '2026-09-10' }
export const item = { id: ITEM, item_versao_id: 'snapshot-item', chave_oficial: '00001', numero_item: '00001', descricao: 'Borracha do recorte', unidade_medida: 'UN', quantidade: '3.00000001', valor_unitario_estimado: null, orcamento_sigiloso: false, catalogo: 'CATMAT', codigo_catalogo: '000123', processo: context, resultados: [result, { ...result, id: 'resultado-2', fornecedor_id: 'outro-fornecedor', fornecedor_nome: 'Segundo fornecedor', cancelado: true, valor_total_homologado: '9999.00000000' }], valor_homologado_item: '0.10000001', resultados_ativos: 1, resultados_sem_valor_total: 0, ultima_data_resultado: '2026-09-10', analise: analysis }
export const otherItem = { ...item, id: secondItem, descricao: 'Caneta do recorte', numero_item: '00002', resultados: [], quantidade: null, unidade_medida: null, valor_homologado_item: null, resultados_ativos: 0 }
export const status = { status: 'disponivel', base: { id: BASE, versao: 'teste', status: 'validada', periodo_inicio: '2026-09-01', periodo_fim: '2026-09-30' }, cobertura: { itens: 2, processos: 1 }, analise: analysis }
const pageOf = (rows, url, base = BASE) => {
  const size = Number(url.searchParams.get('tamanho_pagina') || 20)
  const page = Number(url.searchParams.get('pagina') || 1)
  return { dados: rows.slice((page - 1) * size, page * size), meta: { base_id: base, pagina: page, tamanho_pagina: size, total: rows.length, total_paginas: Math.ceil(rows.length / size) } }
}

export async function mockApi(page, overrides = {}) {
  const state = { calls: [], offline: false, noBase: false, latest: BASE, documentsOffline: false, ...overrides }
  await page.addInitScript(() => localStorage.setItem('lc_ajuda_vista', '1'))
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname.slice('/api/v1'.length)
    state.calls.push(url)
    const send = async (body, code = 200) => route.fulfill({ status: code, contentType: 'application/json', body: JSON.stringify(body) }).catch(() => {})
    const error = (message, code = 503) => send({ erro: { codigo: 'teste', mensagem: message, request_id: 'referencia-teste' } }, code)
    if (state.offline) return route.abort('failed')
    if (state.handler && await state.handler({ url, path, send, error })) return
    const base = url.searchParams.get('base_id') || state.latest
    if (![BASE, OTHER_BASE].includes(base)) return error('Não há base validada para esta consulta.', 404)
    if (path === '/base/status') return send(state.noBase ? { status: 'sem_base', base: null, cobertura: null } : { ...status, base: { ...status.base, id: base } })
    if (path === '/orgaos') return send(pageOf([{ id: ORGANIZATION, nome: 'Órgão do recorte' }], url, base))
    if (path === '/modalidades') return send(pageOf([{ id: MODALITY, nome: 'Pregão' }], url, base))
    if (path === '/fornecedores/opcoes') return send(pageOf([{ id: SUPPLIER, nome: 'Fornecedor do recorte' }], url, base))
    if (path === '/itens') {
      if (url.searchParams.get('valor_minimo') === '2' && url.searchParams.get('valor_maximo') === '1') return error('Intervalo inválido.', 422)
      const search = url.searchParams.get('busca')?.toLowerCase() || ''
      return send(pageOf([item, otherItem].filter(i => i.descricao.toLowerCase().includes(search)), url, base))
    }
    if (path === `/itens/${ITEM}`) return send({ base_id: base, item })
    if (path === `/itens/${secondItem}`) return send({ base_id: base, item: otherItem })
    if (path.startsWith('/itens/')) return error('Item não encontrado nesta base.', path.includes('LC-') ? 422 : 404)
    if (path === `/processos/${PROCESS}`) return send({ base_id: base, processo: { ...context, valor_estimado_processo: '300.00000000', valor_homologado_processo: '200.00000001', valor_homologado_itens_recorte: '0.10000001', quantidade_itens_recorte: 2, situacao: 'Homologada' } })
    if (path === `/processos/${PROCESS}/itens`) return send(pageOf([item, otherItem], url, base))
    if (path === `/processos/${PROCESS}/documentos`) {
      if (state.documentsOffline) return error('Documentos indisponíveis.')
      return send(pageOf([{ id: 'doc-1', titulo: 'Edital da compra', url_origem: 'https://pncp.gov.br/arquivo.pdf', ativo: true, publicado_na_origem_em: '2026-09-01', tipo_nome: 'Edital', contrato_versao_id: null }], url, base))
    }
    return error('Rota inexistente.', 404)
  })
  return state
}
