import { Link, useLocation, useParams } from 'react-router-dom'
import { Search, ArrowLeft, FilePlus2 } from 'lucide-react'
import { AnalysisGate } from '../AnalysisContext.jsx'
import { Filters, ItemRows, useView } from './Analitico.jsx'
import { Head } from '../components/ui.jsx'
import { Pager, QueryState } from '../components/consultas.jsx'
import PriceReview from '../components/PriceReview.jsx'
import { ifBand, ifBandLabels } from '../ifBands.mjs'
import { ifMeasure, money, selectionLink, reportLink } from '../api.mjs'

const score = value => value == null ? 'Sem medida IF' : ifMeasure(value)
const status = value => ({ analisados: 'Completa nos itens importados', parcial: 'Parcial', nao_analisados: 'Sem análise' })[value]

function Coverage({ row }) {
  return <>{row.itens_com_medida_if} de {row.itens_importados} itens importados<small>{status(row.status_analise)}{row.itens_analise_parcial > 0 ? ` · ${row.itens_analise_parcial} item(ns) com resultados parcialmente analisados` : ''}</small></>
}

function Content() {
  const { id } = useParams()
  const location = useLocation()
  const { query, params, changePage } = useView(id ? `/visao/licitacoes/${encodeURIComponent(id)}` : '/visao/licitacoes')
  const data = query.data, row = data?.licitacao
  const listLink = selectionLink('/licitacoes', params)
  const back = location.state?.from?.startsWith('/licitacoes?') ? location.state.from : listLink
  const detailLink = tenderId => {
    const next = new URLSearchParams(params)
    next.delete('pagina')
    return selectionLink(`/licitacoes/${tenderId}`, next)
  }
  return <div className="tenders-page">
    {id && <Link className="link-a back-link" to={back}><ArrowLeft size={16} />Voltar às licitações</Link>}
    <Head title={id ? row ? `Compra ${row.processo.numero_compra}` : 'Detalhe da licitação' : 'Licitações Sinalizadas'} sub={id ? row?.processo.objeto : undefined} action={row && <Link className="btn primary" to={reportLink(row.id, params)}><FilePlus2 size={16} />Incluir no relatório</Link>} />
    {!id && <Filters purchases />}
    <QueryState query={query} loading="Consultando licitações…" />
    {data && !id && <section className="card"><h2>{data.total} {data.total === 1 ? 'licitação' : 'licitações'}</h2>
      {data.dados.length ? <div className="table-scroll" role="region" aria-label="Licitações sinalizadas; use as setas para rolar na horizontal" tabIndex={0}><table className="tbl tbl-stack tender-table product-table"><thead><tr>
        <th scope="col">Licitação / objeto</th><th scope="col">Órgão</th><th scope="col">Valor total homologado</th><th scope="col">Itens</th><th scope="col"><span className="sr-only">Detalhes</span></th>
      </tr></thead><tbody>{data.dados.map(tender => {
        const band = ifBand({ medida_if: tender.medida_if_media, requer_validacao: tender.requer_validacao })
        return <tr key={tender.id} className={band ? `if-band-${band}` : undefined} data-if-band={band || undefined} title={ifBandLabels[band]}>
          <td>{band && <span className="sr-only">{ifBandLabels[band]}. </span>}<Link className="link-a" to={detailLink(tender.id)} state={{ from: listLink }}>Compra {tender.processo.numero_compra}</Link><small className="tender-description" title={tender.processo.objeto}>{tender.processo.objeto}</small><small>{tender.processo.modalidade_nome}</small>{tender.requer_validacao && <PriceReview />}</td>
          <td data-label="Órgão"><span className="tender-org" title={tender.processo.orgao_nome}>{tender.processo.orgao_nome}</span></td>
          <td className="numeric" data-label="Valor total">{money(tender.valor_homologado)}</td>
          <td className="tender-count" data-label="Itens">{tender.itens_importados}<small>{tender.itens_com_medida_if} com análise</small></td>
          <td><Link className="dashboard-analysis-link" title="Ver itens da licitação" aria-label={`Ver itens da compra ${tender.processo.numero_compra}`} to={detailLink(tender.id)} state={{ from: listLink }}><Search size={17} aria-hidden="true" /></Link></td>
        </tr>
      })}</tbody></table></div> : <p>Nenhuma licitação encontrada neste recorte.</p>}
      <Pager meta={data} onChange={changePage} />
    </section>}
    {row && <>
      <section className="card"><h2>Resumo da licitação</h2>{row.requer_validacao && <PriceReview />}<div className="stats"><div><small>Órgão</small><strong>{row.processo.orgao_nome}</strong></div><div><small>Valor global homologado</small><strong>{money(row.valor_homologado)}</strong></div><div><small>Total dos itens importados</small><strong>{money(row.valores_itens_importados.valor_homologado)}</strong>{row.valores_itens_importados.resultados_sem_total > 0 && <small>Total indisponível: existem resultados sem valor.</small>}</div><div><small>Medida IF média dos itens</small><strong>{score(row.medida_if_media)}</strong></div><div><small>Maior medida IF de item</small><strong>{score(row.maior_medida_if)}</strong></div><div><small>Cobertura de análise</small><strong><Coverage row={row} /></strong></div></div></section>
      <section className="card"><h2>Itens desta licitação</h2>{data.itens.dados.length ? <ItemRows rows={data.itens.dados} params={params} /> : <p>Nenhum item importado nesta compra.</p>}<Pager meta={data.itens} onChange={changePage} /></section>
    </>}
  </div>
}

export default function Licitacoes() { return <AnalysisGate><Content /></AnalysisGate> }
