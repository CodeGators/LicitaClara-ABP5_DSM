import { Fragment, useId, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, Search } from 'lucide-react'
import { useBase } from '../BaseContext.jsx'
import { useAnalysis } from '../AnalysisContext.jsx'
import { ifBand, ifBandLabels } from '../ifBands.mjs'
import { money } from '../api.mjs'
import useApi from '../useApi.js'
import { QueryState } from './consultas.jsx'
import PriceReview from './PriceReview.jsx'

const coverage = row => row.itens_com_medida_if == null ? 'Não informado' : `${row.itens_com_medida_if} de ${row.itens} ${row.itens === 1 ? 'analisado' : 'analisados'}`

export default function SupplierListRow({ row, detailLink, listLink }) {
  const [open, setOpen] = useState(false)
  const [visited, setVisited] = useState(false)
  const contentId = useId()
  const { baseId } = useBase()
  const analysis = useAnalysis()
  const query = useApi(`/visao/fornecedores/${encodeURIComponent(row.id)}`, {
    base_id: baseId, execucao_id: analysis.executionId, modelo_id: analysis.modelId, tamanho_pagina: 1,
  }, visited && !!analysis.ready)
  const band = ifBand(row)
  const toggle = () => { setVisited(true); setOpen(value => !value) }
  return <Fragment>
    <tr className={`supplier-main-row${band ? ` if-band-${band}` : ''}`} data-if-band={band || undefined} title={ifBandLabels[band]} onClick={event => { if (!event.target.closest('a, button')) toggle() }}>
      <td>{band && <span className="sr-only">{ifBandLabels[band]}. </span>}
        <button className="link-a supplier-expand-trigger" type="button" aria-expanded={open} aria-controls={contentId} onClick={toggle} title={open ? 'Recolher licitações' : 'Mostrar licitações'}><span>{row.nome}</span><ChevronDown size={16} aria-hidden="true" className={open ? 'supplier-chevron open' : 'supplier-chevron'} /></button>
        <small>{row.orgaos} {row.orgaos === 1 ? 'órgão' : 'órgãos'}</small>{row.requer_validacao && <PriceReview />}
      </td>
      <td data-label="Compras">{row.compras_com_resultado}</td>
      <td className="numeric" data-label="Total homologado">{money(row.valor_homologado)}{row.resultados_sem_total > 0 && <small>Total incompleto</small>}</td>
      <td data-label="Itens analisados">{coverage(row)}</td>
      <td><Link className="dashboard-analysis-link" title="Ver fornecedor" aria-label={`Ver fornecedor ${row.nome}`} to={detailLink} state={{ from: listLink }}><Search size={17} aria-hidden="true" /></Link></td>
    </tr>
    <tr className="supplier-expansion-row" aria-hidden={!open}><td colSpan={5}>
      <div id={contentId} className={`supplier-expansion-grid${open ? ' open' : ''}`} aria-hidden={!open} inert={open ? undefined : ''}>
        <div className="supplier-expansion-clip"><section className="supplier-purchases" aria-label={`Licitações de ${row.nome}`}>
          <h3>Licitações do fornecedor</h3>
          <QueryState query={query} loading="Consultando licitações do fornecedor…" />
          {query.data && (query.data.compras?.length ? <ul>{query.data.compras.map(purchase => <li key={purchase.id}>
            <div><strong>{purchase.orgao_nome}</strong><small>Compra {purchase.numero_compra} · {purchase.itens} {purchase.itens === 1 ? 'item' : 'itens'}</small></div>
            <div className="supplier-purchase-amount"><strong>{money(purchase.valor_homologado)}</strong>{purchase.resultados_sem_total > 0 && <small>Total incompleto na fonte</small>}</div>
          </li>)}</ul> : <p>Nenhuma licitação com resultado deste fornecedor na base atual.</p>)}
        </section></div>
      </div>
    </td></tr>
  </Fragment>
}
