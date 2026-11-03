import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Head, Aviso } from '../components/ui.jsx'
import { Documents, Info, NoAnalysis, Pager, QueryState } from '../components/consultas.jsx'
import { useBase } from '../BaseContext.jsx'
import { baseLink, date, money } from '../api.mjs'
import useApi from '../useApi.js'

export default function Processo() {
  const { id } = useParams()
  const { baseId } = useBase()
  const [page, setPage] = useState(1)
  useEffect(() => setPage(1), [baseId, id])
  const query = useApi(`/processos/${encodeURIComponent(id)}`, { base_id: baseId }, !!baseId)
  const items = useApi(`/processos/${encodeURIComponent(id)}/itens`, { base_id: baseId, pagina: page, tamanho_pagina: 10 }, !!query.data)
  if (!query.data) return <><Link className="link-a" to={baseLink('/itens', baseId)}>← Consultar itens</Link><QueryState query={query} loading="Carregando processo…" /></>
  const process = query.data.processo
  return <>
    <Link className="link-a" to={baseLink('/itens', baseId)}>← Consultar itens</Link>
    <Head kicker="Consulta / Processo da compra" title={`Compra ${process.numero_compra}`} sub={process.objeto} />
    <div className="card stats">
      <Info label="Órgão">{process.orgao_nome}</Info><Info label="Modalidade">{process.modalidade_nome || 'Não informada'}</Info><Info label="Número do processo">{process.numero_processo || 'Não informado'}</Info>
      <Info label="Publicação">{date(process.data_publicacao)}</Info><Info label="Estimado global da compra">{money(process.valor_estimado_processo)}</Info><Info label="Homologado global da compra">{money(process.valor_homologado_processo)}</Info>
      <Info label="Homologado dos itens do recorte">{money(process.valor_homologado_itens_recorte)}</Info><Info label="Situação na origem">{process.situacao}</Info><Info label="Itens no recorte">{process.quantidade_itens_recorte}</Info>
    </div>
    <p className="note">O recorte pode conter apenas parte da compra. O valor global e o total dos itens do recorte são medidas distintas e não devem ser somados.</p>
    <NoAnalysis />
    <section className="card"><h2>Itens deste processo</h2><QueryState query={items} loading="Carregando itens do processo…" />
      {items.data && <>{items.data.dados.length ? <ul className="document-list">{items.data.dados.map(item => <li key={item.id}><Link className="link-a" to={baseLink(`/itens/${item.id}`, baseId)}>Item {item.numero_item} · {item.descricao}</Link></li>)}</ul> : <p className="sub">Nenhum item conhecido neste recorte.</p>}<Pager meta={items.data.meta} onChange={setPage} /></>}
    </section>
    <Documents key={`${baseId}:${id}`} processId={id} baseId={baseId} />
    <Aviso detalhe />
  </>
}
