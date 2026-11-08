import { useState } from 'react'
import { Field, LookupFilter } from './consultas.jsx'

const advancedKeys = ['orgao_id', 'fornecedor_id', 'modalidade_id', 'homologacao_inicio', 'homologacao_fim', 'valor_minimo', 'valor_maximo']

export default function ItemFilters({ draft, change, apply, clear, baseId, params, purchases = false }) {
  const [advanced, setAdvanced] = useState(false)
  const [lookupReset, setLookupReset] = useState(0)
  const count = advancedKeys.filter(key => params.get(key)).length
  return <form className="card item-filters" aria-label="Filtros do recorte" onSubmit={apply}>
    <h2>{purchases ? 'Filtrar licitações' : 'Filtrar itens'}</h2>
    <div className="item-filters-primary">
      <Field label={purchases ? 'Buscar licitação, item ou fornecedor' : 'Buscar item, compra ou fornecedor'}><input className="input" type="search" placeholder={purchases ? 'Número, objeto, item ou fornecedor' : 'Digite o nome do item, compra ou fornecedor'} maxLength={200} value={draft.busca} onChange={e => change('busca', e.target.value)} /></Field>
      <Field label="Estado da análise"><select className="select" value={draft.analise} onChange={e => change('analise', e.target.value)}><option value="todos">{purchases ? 'Todas as licitações' : 'Todos os itens'}</option><option value="analisados">{purchases ? 'Todos os itens importados com análise completa' : 'Com análise completa'}</option><option value="parcial">{purchases ? 'Parte dos itens/resultados com análise' : 'Com análise parcial'}</option><option value="nao_analisados">Sem análise</option></select></Field>
      <Field label="Ordenação"><select className="select" value={draft.ordenacao} onChange={e => change('ordenacao', e.target.value)}><option value="indice_desc">{purchases ? 'Maior Score médio primeiro' : 'Maior Score primeiro'}</option><option value="descricao_asc">{purchases ? 'Objeto da licitação' : 'Nome do item'}</option><option value="valor_desc">Maior valor homologado</option></select></Field>
    </div>
    <details className="item-filters-advanced" open={advanced} onToggle={e => setAdvanced(e.currentTarget.open)}>
      <summary>Mais filtros{count > 0 && <span className="pill ana">{count} aplicado(s)</span>}</summary>
      {advanced && <><p className="hint">Use apenas os campos necessários. Para localizar um órgão ou fornecedor, digite parte do nome e selecione o resultado.</p>
        <div className="item-filters-lookups">
          <LookupFilter key={`orgao-${lookupReset}`} compact kind="/orgaos" title="Órgão" baseId={baseId} value={draft.orgao_id} onChange={v => change('orgao_id', v)} />
          <LookupFilter key={`fornecedor-${lookupReset}`} compact kind="/fornecedores/opcoes" title="Fornecedor" baseId={baseId} value={draft.fornecedor_id} onChange={v => change('fornecedor_id', v)} />
          <LookupFilter key={`modalidade-${lookupReset}`} compact kind="/modalidades" title="Modalidade" baseId={baseId} value={draft.modalidade_id} onChange={v => change('modalidade_id', v)} />
        </div>
        <div className="item-filters-ranges">
          <fieldset><legend>Período de homologação</legend><div className="item-filters-pair"><Field label="Homologação a partir de"><input className="input" type="date" value={draft.homologacao_inicio} onChange={e => change('homologacao_inicio', e.target.value)} /></Field><Field label="Homologação até"><input className="input" type="date" value={draft.homologacao_fim} onChange={e => change('homologacao_fim', e.target.value)} /></Field></div></fieldset>
          <fieldset><legend>{purchases ? 'Valor global homologado da licitação' : 'Valor homologado no recorte'}</legend><div className="item-filters-pair"><Field label={purchases ? 'Valor global mínimo (R$)' : 'Total do recorte mínimo (R$)'}><input className="input" type="number" min="0" step="0.00000001" placeholder="Sem mínimo" value={draft.valor_minimo} onChange={e => change('valor_minimo', e.target.value)} /></Field><Field label={purchases ? 'Valor global máximo (R$)' : 'Total do recorte máximo (R$)'}><input className="input" type="number" min="0" step="0.00000001" placeholder="Sem máximo" value={draft.valor_maximo} onChange={e => change('valor_maximo', e.target.value)} /></Field></div></fieldset>
        </div>
        <div className="item-filters-page-size"><Field label="Registros por página"><select className="select" value={draft.tamanho_pagina} onChange={e => change('tamanho_pagina', e.target.value)}>{[5,10,20,50,100].map(n => <option key={n}>{n}</option>)}</select></Field></div>
      </>}
    </details>
    <div className="filter-actions"><button className="btn primary" type="submit">Aplicar filtros</button><button className="btn ghost" type="button" onClick={() => { setLookupReset(n => n + 1); clear() }}>Limpar filtros</button></div>
  </form>
}
