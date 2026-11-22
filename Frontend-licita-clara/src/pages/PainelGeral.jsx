import PriceReview from '../components/PriceReview.jsx'
import { requiresPriceReview } from '../priceValidation.mjs'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Files, Wallet, Activity, ScanSearch, CalendarDays, ArrowRight, Search } from 'lucide-react'
import { useBase } from '../BaseContext.jsx'
import { date, decimal, money, selectionLink } from '../api.mjs'
import { QueryState } from '../components/consultas.jsx'
import { Head } from '../components/ui.jsx'

const number = value => Number(value).toLocaleString('pt-BR')
const month = value => value ? new Date(`${value.slice(0, 7)}-15T12:00:00`).toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' }) : 'Período não informado'
const period = (start, end) => start?.slice(0, 7) === end?.slice(0, 7) ? month(start) : `${month(start)} – ${month(end)}`
const compactMoney = value => value == null ? 'Não informado' : Math.abs(Number(value)) >= 1_000_000 ? `R$ ${(Number(value) / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi` : money(value)
const numeric = value => value != null && value !== '' && Number.isFinite(Number(value)) ? Number(value) : null

function comparison(item) {
  // The same result supplies the price, supplier and reference. Never mix winners.
  const score = [...(item?.scores || [])].sort((a, b) => Number(b.score_bruto) - Number(a.score_bruto) || String(a.id).localeCompare(String(b.id)))[0]
  const result = item?.resultados.find(r => r.id === score?.resultado_item_id)
  const reference = score?.atributos?.comparacao
  const basis = reference?.unidade_preco?.unidade_preco
  const price = numeric(result?.valor_unitario_homologado)
  const median = numeric(reference?.mediana)
  const valid = !!basis && price != null && price >= 0 && median != null && median > 0
  return { result, reference, basis, price, median, valid, review: requiresPriceReview(result?.valor_unitario_homologado, reference?.mediana, basis), percent: valid ? (price / median - 1) * 100 : null }
}
const difference = c => !c.valid ? 'Sem referência' : Math.abs(c.percent) < 0.005 ? 'Na mediana' : `${decimal(Math.abs(c.percent), 2, 2)}% ${c.percent > 0 ? 'acima' : 'abaixo'}`

function PriceReading({ item, params }) {
  const c = comparison(item)
  const max = Math.max(c.price || 0, c.median || 0, 1)
  return <section className="card dashboard-reading dashboard-price-reading"><h2>Confira este item</h2>
    {!item ? <p>Selecione um item analisado.</p> : <>
      <h3>{item.descricao}</h3><p className="sub">Compra {item.processo.numero_compra} · item {item.numero_item}</p>
      {c.valid ? <>{c.review ? <><PriceReview /><details><summary>Ver diferença registrada</summary><p>{difference(c)}</p></details></> : <p className="dashboard-price-difference">{difference(c)}</p>}<p className="hint">da mediana histórica do grupo · preços por {c.basis}</p>
        {[["Preço unitário homologado", c.price], ["Mediana histórica dos similares", c.median]].map(([label, value]) => <div className="dashboard-price-bar" key={label}><div><span>{label}</span><strong>{money(value)}</strong></div><div className="dashboard-price-track"><span style={{ width: `${100 * value / max}%` }} /></div></div>)}
      </> : <p className="dashboard-price-empty">Comparação de preço indisponível: falta uma referência histórica com unidade identificada. Consulte os detalhes da análise.</p>}
      <dl className="dashboard-price-facts"><dt>Órgão comprador</dt><dd>{item.processo.orgao_nome || 'Não informado'}</dd><dt>Fornecedor deste resultado</dt><dd>{c.result?.fornecedor_nome || 'Não informado'}</dd><dt>Quantidade homologada</dt><dd>{c.result?.quantidade_homologada == null ? 'Não informada' : decimal(c.result.quantidade_homologada)}</dd><dt>Data do resultado</dt><dd>{date(c.result?.data_resultado)}</dd></dl>
      <Link className="btn primary" to={selectionLink(`/ranking/${item.id}`, params)} state={{ from: selectionLink('/painel', params) }}><Search size={16} aria-hidden="true" /> Ver análise completa</Link>
    </>}
  </section>
}

export default function PainelGeral({ query, ranking, params }) {
  const { baseId, data: baseData } = useBase()
  const [chosen, setChosen] = useState('')
  const data = query.data
  const rows = ranking.data?.dados.filter(r => r.medida_if != null) || []
  const selected = rows.find(r => r.id === chosen) || rows[0]
  const summary = data?.resumo
  const periodLabel = period(baseData?.base?.periodo_inicio, baseData?.base?.periodo_fim)
  const withAnalysis = summary ? summary.analisados + summary.parcial : 0
  const cards = summary ? [
    ['Compras no recorte', number(summary.processos), `${number(summary.orgaos)} órgãos · ${number(summary.fornecedores)} fornecedores`, Files],
    ['Valor homologado', compactMoney(summary.valor_homologado), 'Resultados não cancelados', Wallet],
    ['Itens com análise', number(withAnalysis), `de ${number(summary.itens)} itens importados (${summary.itens ? (100 * withAnalysis / summary.itens).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) : 0}%)`, Activity],
    ['Sem análise', number(summary.nao_analisados), 'Veja os motivos abaixo', ScanSearch],
  ] : []
  return <div className="dashboard">
    <Head title="Painel geral" sub="Todos os dados foram retirados da base Compras.gov.br"
      action={<span className="btn ghost dashboard-period" title="Competência dos arquivos importados; as datas dos resultados podem variar"><CalendarDays size={16} aria-hidden="true" />Base: {periodLabel}</span>} />
    <QueryState query={query} />
    {data && <>
      <div className="dashboard-kpis">{cards.map(([label, value, note, Icon], i) => <section className="card kpi" key={label}><div className="dashboard-kpi-label"><span>{label}</span><Icon size={17} aria-hidden="true" /></div><strong title={i === 1 ? money(summary.valor_homologado) : undefined}>{value}</strong><small>{note}</small></section>)}</div>
      <div className="dashboard-bottom"><section className="card dashboard-start"><div className="mini"><div><h2>Itens para conferir</h2><p className="sub"><strong className="validation-heading">Requer validação:</strong> possível erro de digitação ou de cadastro pelo Compras.gov.br</p></div><Link className="link-a" to={selectionLink('/ranking', params)}>Ver todos <ArrowRight size={13} /></Link></div>
        <QueryState query={ranking} loading="Consultando itens do recorte…" />
        {ranking.data && (!rows.length ? <p>Nenhum item analisado disponível neste recorte.</p> : <div className="table-scroll" role="region" aria-label="Itens para conferir" tabIndex={0}><table className="tbl tbl-stack"><thead><tr><th scope="col">Compra / item</th><th scope="col">Preço unitário</th><th scope="col">Mediana histórica</th><th scope="col">Diferença</th><th scope="col"><span className="sr-only">Análise</span></th></tr></thead><tbody>{rows.map(row => {
          const c = comparison(row)
          return <tr key={row.id} onClick={event => { if (!event.target.closest('a, button')) setChosen(row.id) }} className={selected?.id === row.id ? 'sel' : ''}><td><button className="dashboard-row-select" aria-pressed={selected?.id === row.id} onClick={() => setChosen(row.id)}>Compra {row.processo.numero_compra} · item {row.numero_item}</button><small className="dashboard-clamp" title={row.descricao}>{row.descricao}</small><small className="dashboard-clamp" title={row.processo.orgao_nome}>{row.processo.orgao_nome}</small></td><td className="numeric" data-label="Preço unitário"><span className="dashboard-price-number">{money(c.price)}</span></td><td className="numeric" data-label="Mediana histórica">{c.valid ? <><span className="dashboard-price-number">{money(c.median)}</span><small>por {c.basis}</small></> : 'Indisponível'}</td><td className="numeric" data-label="Diferença">{c.review ? <PriceReview compact /> : c.valid ? <><span className="dashboard-price-number">{decimal(Math.abs(c.percent), 2, 2)}%</span><small>{Math.abs(c.percent) < 0.005 ? 'na mediana' : c.percent > 0 ? 'acima' : 'abaixo'}</small></> : 'Sem referência'}</td><td><Link className="dashboard-analysis-link" to={selectionLink(`/ranking/${row.id}`, params)} state={{ from: selectionLink('/painel', params) }} title="Ver análise" aria-label="Ver análise"><Search size={17} aria-hidden="true" /></Link></td></tr>
        })}</tbody></table></div>)}
      </section><PriceReading key={selected?.id} item={selected} params={params} /></div>
    </>}
  </div>
}
