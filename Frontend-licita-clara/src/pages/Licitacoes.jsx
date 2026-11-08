import { Link, useParams } from 'react-router-dom'
import { Search, ArrowLeft, FilePlus2 } from 'lucide-react'
import { AnalysisGate, AnalysisSelector } from '../AnalysisContext.jsx'
import { Filters, ItemRows, useView } from './Analitico.jsx'
import { Head } from '../components/ui.jsx'
import { Pager, QueryState } from '../components/consultas.jsx'
import { decimal, money, selectionLink, reportLink } from '../api.mjs'

const score = value => value == null ? 'Sem Score' : decimal(value)
const status = value => ({ analisados: 'Completa nos itens importados', parcial: 'Parcial', nao_analisados: 'Sem análise' })[value]

function Coverage({ row }) {
  return <>{row.itens_com_score} de {row.itens_importados} itens importados<small>{status(row.status_analise)}{row.itens_analise_parcial > 0 ? ` · ${row.itens_analise_parcial} item(ns) com resultados parcialmente analisados` : ''}</small></>
}

function Content() {
  const { id } = useParams()
  const { query, params, changePage } = useView(id ? `/visao/licitacoes/${encodeURIComponent(id)}` : '/visao/licitacoes')
  const data = query.data, row = data?.licitacao
  return <div className="tenders-page">
    {id && <Link className="link-a" to={selectionLink('/licitacoes', params)}><ArrowLeft size={14} />Voltar às licitações</Link>}
    <Head kicker="Visão por licitação / Resumo dos itens" title={id ? row ? `Compra ${row.processo.numero_compra}` : 'Detalhe da licitação' : 'Licitações Sinalizadas'} sub={id ? row?.processo.objeto : 'Uma linha por compra, com média dos Scores disponíveis e cobertura dos itens importados.'} action={row && <Link className="btn primary" to={reportLink(row.id, params)}><FilePlus2 size={16} />Incluir no relatório</Link>} />
    <div className="note"><b>Como o Score médio é calculado</b>Média simples dos Scores dos itens com análise, com o mesmo peso por item. Cada item usa o maior Score dos seus resultados no modelo selecionado ou preferencial do grupo. Itens sem Score ficam fora da média. É um resumo descritivo; não representa probabilidade de fraude ou prioridade validada.</div>
    <AnalysisSelector />
    {!id && <Filters simple purchases />}
    <QueryState query={query} loading="Consultando licitações…" />
    {data && !id && <>
      <div className="grid g3"><section className="card kpi"><span>Licitações no recorte</span><strong>{data.resumo.licitacoes}</strong></section><section className="card kpi"><span>Licitações com Score</span><strong>{data.resumo.com_score}</strong></section><section className="card kpi"><span>Itens com Score / importados</span><strong>{data.resumo.itens_com_score} / {data.resumo.itens_importados}</strong></section></div>
      <section className="card"><h2>{data.total} licitação(ões) encontrada(s)</h2><p className="sub">Os filtros selecionam licitações. A média conserva todos os itens importados de cada compra. A cobertura não confirma que a compra foi importada integralmente.</p>
        {data.dados.length ? <div className="table-scroll" role="region" aria-label="Licitações e Scores; use as setas para rolar" tabIndex={0}><table className="tbl tender-table"><thead><tr><th scope="col">Licitação / objeto</th><th scope="col">Órgão</th><th scope="col">Valor global homologado</th><th scope="col">Itens com Score</th><th scope="col">Score médio</th><th scope="col">Maior Score</th><th scope="col"><span className="sr-only">Detalhes</span></th></tr></thead><tbody>{data.dados.map(r => <tr key={r.id}><td><Link className="link-a" to={selectionLink(`/licitacoes/${r.id}`, params)}>Compra {r.processo.numero_compra}</Link><small>{r.processo.objeto}</small><small>{r.processo.modalidade_nome}</small></td><td>{r.processo.orgao_nome}</td><td className="numeric">{money(r.valor_homologado)}</td><td><Coverage row={r} /></td><td className="numeric">{score(r.score_medio)}</td><td className="numeric">{score(r.maior_score)}</td><td><Link className="dashboard-analysis-link" title="Ver itens da licitação" aria-label={`Ver itens da compra ${r.processo.numero_compra}`} to={selectionLink(`/licitacoes/${r.id}`, params)}><Search size={17} aria-hidden="true" /></Link></td></tr>)}</tbody></table></div> : <p>Nenhuma licitação encontrada neste recorte.</p>}
        <Pager meta={data} onChange={changePage} />
      </section>
    </>}
    {row && <>
      <section className="card"><h2>Resumo da licitação</h2><div className="stats"><div><small>Órgão</small><strong>{row.processo.orgao_nome}</strong></div><div><small>Valor global homologado</small><strong>{money(row.valor_homologado)}</strong></div><div><small>Total dos itens importados</small><strong>{money(row.valores_itens_importados.valor_homologado)}</strong>{row.valores_itens_importados.resultados_sem_total > 0 && <small>Total indisponível: existem resultados sem valor.</small>}</div><div><small>Score médio dos itens</small><strong>{score(row.score_medio)}</strong></div><div><small>Maior Score de item</small><strong>{score(row.maior_score)}</strong></div><div><small>Cobertura de análise</small><strong><Coverage row={row} /></strong></div></div><p className="hint">Não há confirmação do total oficial de itens. Os valores globais e dos itens importados são medidas diferentes.</p></section>
      <section className="card"><h2>Itens desta licitação</h2><p className="sub">Clique no item para consultar a análise salva. A paginação desta lista não altera a média da licitação.</p>{data.itens.dados.length ? <ItemRows rows={data.itens.dados} params={params} /> : <p>Nenhum item importado nesta compra.</p>}<Pager meta={data.itens} onChange={changePage} /></section>
    </>}
  </div>
}

export default function Licitacoes() { return <AnalysisGate><Content /></AnalysisGate> }
