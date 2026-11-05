import { Link, useLocation, useParams } from 'react-router-dom'
import { Head, Aviso } from '../components/ui.jsx'
import { Documents, Info, QueryState, Results } from '../components/consultas.jsx'
import { useBase } from '../BaseContext.jsx'
import { baseLink, date, decimal, money, reportLink } from '../api.mjs'
import useApi from '../useApi.js'
import AnaliseItem from '../components/AnaliseItem.jsx'
import { selectionLink } from '../AnalysisContext.jsx'

export default function ItemDetalhe() {
  const { id } = useParams()
  const { baseId } = useBase()
  const location = useLocation()
  const query = useApi(`/itens/${encodeURIComponent(id)}`, { base_id: baseId }, !!baseId)
  const back = /^\/(itens|ranking|fornecedores)(\/[^?]*)?\?/.test(location.state?.from || '') ? location.state.from : baseLink('/itens', baseId)
  if (!query.data) return <><Link className="link-a" to={back}>← Voltar à consulta</Link><QueryState query={query} loading="Carregando item…" /></>
  const item = query.data.item
  const process = item.processo
  return <>
    <Link className="link-a" to={back}>← Voltar à consulta</Link>
    <Head kicker="Consulta / Detalhe do item" title={item.descricao} sub={`Item ${item.numero_item} · Compra ${process.numero_compra} · ${process.orgao_nome}`} action={<Link className="btn primary" to={selectionLink(`/processos/${process.id}`, location.search)}>Ver processo da compra</Link>} />
    <div className="card stats">
      <Info label="Quantidade do item">{decimal(item.quantidade)}</Info><Info label="Unidade">{item.unidade_medida || 'Não informada'}</Info>
      <Info label="Preço unitário estimado">{money(item.valor_unitario_estimado)}</Info><Info label="Total homologado do item">{money(item.valor_homologado_item)}</Info>
      <Info label="Catálogo">{item.catalogo ? `${item.catalogo} ${item.codigo_catalogo}` : 'Não informado'}</Info><Info label="Último resultado não cancelado">{date(item.ultima_data_resultado)}</Info>
    </div>
    {item.resultados_sem_valor_total > 0 && <p className="note">O total do item está indisponível porque há {item.resultados_sem_valor_total} resultado(s) não cancelado(s) sem valor total informado.</p>}
    <AnaliseItem item={item} />
    <Results results={item.resultados} />
    <Documents key={`${baseId}:${process.id}`} processId={process.id} baseId={baseId} />
    <section className="card"><h2>Revisão e relatório</h2><p className="sub">Exporte o processo da compra com os itens do recorte e as análises disponíveis.</p><Link className="btn primary" to={reportLink(process.id, location.search)}>Preparar relatório</Link></section>
    <Aviso detalhe />
  </>
}
