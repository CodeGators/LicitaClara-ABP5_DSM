import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { useBase } from '../BaseContext.jsx'
import { AnalysisGate, AnalysisSelector, selectionLink, useAnalysis, viewFields } from '../AnalysisContext.jsx'
import { decimal, money } from '../api.mjs'
import { Field, LookupFilter, Pager, QueryState } from '../components/consultas.jsx'
import { Head } from '../components/ui.jsx'
import useApi from '../useApi.js'

export const indexText = value => value == null ? 'Indisponível' : decimal(value)
const read = params => Object.fromEntries(viewFields.map(key => [key, params.get(key) || (key === 'analise' ? 'todos' : key === 'ordenacao' ? 'indice_desc' : key === 'tamanho_pagina' ? '20' : '')]))

function Filters() {
  const { params, setParams } = useAnalysis()
  const { baseId } = useBase()
  const [draft, setDraft] = useState(() => read(params))
  useEffect(() => setDraft(read(params)), [params])
  const change = (key, value) => setDraft(previous => ({ ...previous, [key]: value }))
  const apply = event => {
    event.preventDefault()
    setParams(previous => {
      const next = new URLSearchParams(previous)
      for (const key of [...viewFields, 'pagina']) next.delete(key)
      for (const key of viewFields) if (draft[key]) next.set(key, draft[key])
      return next
    })
  }
  return <form className="card" onSubmit={apply}><h2>Filtros do recorte</h2><div className="filters real-filters">
    <Field label="Buscar item, compra ou fornecedor"><input className="input" type="search" maxLength={200} value={draft.busca} onChange={e => change('busca', e.target.value)} /></Field>
    <LookupFilter kind="/orgaos" title="Órgão" baseId={baseId} value={draft.orgao_id} onChange={v => change('orgao_id', v)} />
    <LookupFilter kind="/fornecedores/opcoes" title="Fornecedor" baseId={baseId} value={draft.fornecedor_id} onChange={v => change('fornecedor_id', v)} />
    <LookupFilter kind="/modalidades" title="Modalidade" baseId={baseId} value={draft.modalidade_id} onChange={v => change('modalidade_id', v)} />
    <Field label="Homologação a partir de"><input className="input" type="date" value={draft.homologacao_inicio} onChange={e => change('homologacao_inicio', e.target.value)} /></Field>
    <Field label="Homologação até"><input className="input" type="date" value={draft.homologacao_fim} onChange={e => change('homologacao_fim', e.target.value)} /></Field>
    <Field label="Total do recorte mínimo (R$)"><input className="input" type="number" min="0" step="0.00000001" value={draft.valor_minimo} onChange={e => change('valor_minimo', e.target.value)} /></Field>
    <Field label="Total do recorte máximo (R$)"><input className="input" type="number" min="0" step="0.00000001" value={draft.valor_maximo} onChange={e => change('valor_maximo', e.target.value)} /></Field>
    <Field label="Estado da análise"><select className="select" value={draft.analise} onChange={e => change('analise', e.target.value)}><option value="todos">Todos</option><option value="analisados">Analisados integralmente</option><option value="parcial">Parcialmente analisados</option><option value="nao_analisados">Não analisados</option></select></Field>
    <Field label="Ordenação"><select className="select" value={draft.ordenacao} onChange={e => change('ordenacao', e.target.value)}><option value="indice_desc">Maior índice disponível</option><option value="descricao_asc">Nome / descrição</option><option value="valor_desc">Maior total conhecido</option></select></Field>
    <Field label="Registros por página"><select className="select" value={draft.tamanho_pagina} onChange={e => change('tamanho_pagina', e.target.value)}>{[5,10,20,50,100].map(n => <option key={n}>{n}</option>)}</select></Field>
  </div><div className="filter-actions"><button className="btn primary" type="submit">Aplicar filtros</button><button className="btn ghost" type="button" onClick={() => setParams(previous => {
    const next = new URLSearchParams(previous); for (const key of [...viewFields, 'pagina']) next.delete(key); return next
  })}>Limpar filtros</button></div><p className="hint">O fornecedor seleciona itens com resultado dele. Valores e HHI conservam os demais vencedores desses itens no período. Contratos são vínculos conhecidos, não contagem de compras.</p></form>
}

function Notice() {
  return <div className="note"><b>Análise experimental · utilidade não validada</b>O índice é uma posição em relação ao treino do modelo, não probabilidade de fraude ou prioridade de auditoria. Sem faixas de risco validadas. Ausência de índice não representa regularidade.</div>
}

function Cards({ summary }) {
  return <div className="grid g3">
    {[
      ['Itens no recorte', summary.itens, `${summary.processos} compras · ${summary.contratos_vinculados} contratos vinculados`],
      ['Total homologado no recorte', money(summary.valor_homologado), summary.resultados_sem_total ? `${summary.resultados_sem_total} resultado(s) sem total; soma conhecida: ${money(summary.soma_valores_conhecidos)}` : `${summary.resultados} resultados não cancelados; não é valor pago`],
      ['Fornecedores exibidos', summary.fornecedores, `${summary.orgaos} órgãos · ${summary.fornecedores_no_denominador} fornecedores no universo de concentração`],
      ['Analisados integralmente', summary.analisados, 'Todos os resultados selecionados têm índice neste modelo'],
      ['Parcialmente analisados', summary.parcial, 'Há resultados sem score; cobertura não é completada com zero'],
      ['Não analisados', summary.nao_analisados, 'Motivo disponível na consulta; sem conclusão de auditoria'],
    ].map(([label, value, text]) => <div className="card kpi" key={label}><span>{label}</span><strong>{value}</strong><small>{text}</small></div>)}
  </div>
}

function useView(path) {
  const { baseId } = useBase()
  const s = useAnalysis()
  const filters = read(s.params)
  const query = useApi(path, { base_id: baseId, execucao_id: s.executionId, modelo_id: s.modelId, ...filters, pagina: s.params.get('pagina') || '1' }, !!s.ready)
  const changePage = page => s.setParams(previous => { const next = new URLSearchParams(previous); next.set('pagina', String(page)); return next })
  return { query, params: s.params, changePage }
}

function ItemRows({ rows, params }) {
  const location = useLocation()
  return <div className="table-scroll"><table className="tbl"><thead><tr><th>Item / compra</th><th>Órgão / fornecedores</th><th>Total homologado no recorte</th><th>Índice experimental</th><th>Cobertura</th></tr></thead><tbody>{rows.map(r => <tr key={r.id}>
    <td><Link className="link-a" to={selectionLink(`/itens/${r.id}`, params)} state={{ from: location.pathname + location.search }}>{r.descricao}</Link><small>Item {r.numero_item} · Compra {r.processo.numero_compra}</small></td>
    <td>{r.processo.orgao_nome}<small>{[...new Set(r.resultados.map(e => e.fornecedor_nome))].join('; ') || 'Nenhum resultado conhecido'}</small></td>
    <td>{money(r.valor_homologado)}{r.resultados_sem_total > 0 && <small>Total incompleto na fonte</small>}</td>
    <td>{indexText(r.indice_experimental)}{r.indice_experimental != null && <small>Máximo dos resultados neste modelo</small>}</td>
    <td>{r.status_analise === 'analisados' ? 'Integral' : r.status_analise === 'parcial' ? 'Parcial' : 'Não analisado'}<small>{r.resultados_analisados}/{r.resultados_ativos} resultados</small>{Object.keys(r.motivos).map(reason => <small key={reason}>{reason.replaceAll('_', ' ').toLocaleLowerCase('pt-BR')}</small>)}</td>
  </tr>)}</tbody></table></div>
}

function Shell({ title, children }) {
  return <><Head kicker="Dados oficiais / Recorte selecionado" title={title} sub="Consultas reais, com base e análise versionadas. Filtros compartilhados entre painel, ranking e fornecedores." /><AnalysisSelector /><Notice /><Filters />{children}</>
}

function DashboardContent() {
  const { query } = useView('/visao/painel')
  const data = query.data
  return <Shell title="Painel do recorte"><QueryState query={query} />{data && <><Cards summary={data.resumo} />
    <div className="grid g-1-1"><section className="card"><h2>Distribuição dos índices experimentais</h2><p className="sub">Um índice máximo por item no modelo escolhido. Parcialmente analisados são identificados nos contadores.</p>
      {!data.distribuicao.some(b => b.itens) ? <p className="empty-chart">Nenhum índice disponível neste recorte.</p> : <><div className="distribution" role="img" aria-label="Distribuição de itens por faixa do índice experimental">{data.distribuicao.map((b,i) => <div key={b.inicio}><span>{b.itens}</span><div style={{ height: `${120*b.itens/Math.max(...data.distribuicao.map(x => x.itens))}px` }} /><small>{i === 9 ? '90–100' : `${b.inicio}–<${b.fim}`}</small></div>)}</div><table className="tbl"><caption>Contagem por intervalo</caption><tbody>{data.distribuicao.map((b,i) => <tr key={b.inicio}><th>{i === 9 ? '90–100' : `${b.inicio}–<${b.fim}`}</th><td>{b.itens}</td></tr>)}</tbody></table></>}
    </section><section className="card"><h2>Evolução dos itens por último resultado</h2><p className="sub">Cada item conta uma vez, no mês do último resultado do recorte. Não mede pagamento ou alta prioridade.</p>
      {!data.evolucao.length ? <p>Nenhum item neste recorte.</p> : <div className="table-scroll compact-table" role="region" aria-label="Evolução dos itens por mês" tabIndex="0"><table className="tbl"><thead><tr><th>Mês</th><th>Itens</th><th>Integrais</th><th>Parciais</th><th>Sem análise</th></tr></thead><tbody>{data.evolucao.map(m => <tr key={m.mes}><td>{m.mes === 'sem_data' ? 'Sem data conhecida' : m.mes.split('-').reverse().join('/')}</td><td>{m.itens}</td><td>{m.analisados}</td><td>{m.parcial}</td><td>{m.nao_analisados}</td></tr>)}</tbody></table></div>}
    </section></div><section className="card"><h2>Motivos de indisponibilidade</h2>{Object.keys(data.motivos_indisponibilidade).length ? <ul>{Object.entries(data.motivos_indisponibilidade).map(([reason,n]) => <li key={reason}>{reason.replaceAll('_', ' ').toLocaleLowerCase('pt-BR')}: {n} ocorrência(s)</li>)}</ul> : <p>Nenhum motivo registrado neste recorte.</p>}</section></>}
  </Shell>
}

function RankingContent() {
  const { query, params, changePage } = useView('/visao/ranking')
  const data = query.data
  return <Shell title="Ranking experimental"><QueryState query={query} />{data && <><Cards summary={data.resumo} /><section className="card"><h2>{data.total} item(ns) no ranking</h2><p className="sub">Índices disponíveis primeiro; ausências ficam ao final, sem receber zero. Não é uma fila de risco validado.</p>{data.dados.length ? <ItemRows rows={data.dados} params={params} /> : <p>Nenhum item encontrado nesta página.</p>}<Pager meta={data} onChange={changePage} /></section></>}</Shell>
}

function SuppliersContent() {
  const { id } = useParams()
  const { query, params, changePage } = useView(id ? `/visao/fornecedores/${encodeURIComponent(id)}` : '/visao/fornecedores')
  const data = query.data
  return <Shell title={id ? 'Relações do fornecedor' : 'Fornecedores do recorte'}><QueryState query={query} />{data && <><Cards summary={data.resumo} />
    {id ? <><Link className="link-a" to={selectionLink('/fornecedores', params)}>← Todos os fornecedores</Link><section className="card"><h2>{data.fornecedor.nome}</h2><p>{data.fornecedor.compras_com_resultado} compras com resultado · {data.fornecedor.contratos_vinculados} contratos vinculados conhecidos · {data.fornecedor.orgaos} órgãos</p><p>Total homologado deste fornecedor: {money(data.fornecedor.valor_homologado)} · Maior índice disponível: {indexText(data.fornecedor.indice_experimental)}</p></section>
      <section className="card"><h2>Participação e concentração por órgão</h2><p className="sub">HHI de todos os fornecedores dos itens filtrados, no período selecionado. Não representa o universo completo do órgão. Concentração não comprova irregularidade.</p><div className="table-scroll"><table className="tbl"><thead><tr><th>Órgão</th><th>Compras com resultado</th><th>Homologado ao fornecedor</th><th>Total do universo</th><th>Participação</th><th>HHI</th></tr></thead><tbody>{data.relacoes.map(r => <tr key={r.orgao_id}><td>{r.orgao_nome}</td><td>{r.compras_com_resultado}</td><td>{money(r.valor_fornecedor)}</td><td>{money(r.valor_homologado)}</td><td>{r.participacao == null ? 'Indisponível' : `${decimal((Number(r.participacao)*100).toFixed(2))}%`}</td><td>{r.hhi == null ? 'Indisponível' : decimal(Number(r.hhi).toFixed(4))}{r.motivo && <small>{r.motivo.replaceAll('_',' ').toLowerCase()}</small>}</td></tr>)}</tbody></table></div></section>
      <section className="card"><h2>Itens com resultado deste fornecedor</h2><p className="sub">Valores e índices abaixo consideram somente seus resultados; o detalhe do item apresenta todos os vencedores.</p><ItemRows rows={data.itens.dados} params={params} /><Pager meta={data.itens} onChange={changePage} /></section></>
      : <section className="card"><h2>{data.total} fornecedor(es) encontrado(s)</h2>{data.dados.length ? <div className="table-scroll"><table className="tbl"><thead><tr><th>Fornecedor</th><th>Compras com resultado</th><th>Contratos vinculados</th><th>Homologado</th><th>Maior índice disponível</th></tr></thead><tbody>{data.dados.map(r => <tr key={r.id}><td><Link className="link-a" to={selectionLink(`/fornecedores/${r.id}`, params)}>{r.nome}</Link><small>{r.itens} itens · {r.orgaos} órgãos</small></td><td>{r.compras_com_resultado}</td><td>{r.contratos_vinculados}</td><td>{money(r.valor_homologado)}{r.resultados_sem_total > 0 && <small>Total incompleto</small>}</td><td>{indexText(r.indice_experimental)}</td></tr>)}</tbody></table></div> : <p>Nenhum fornecedor encontrado nesta página.</p>}<Pager meta={data} onChange={changePage} /></section>}
    </>}</Shell>
}

export const PainelReal = () => <AnalysisGate><DashboardContent /></AnalysisGate>
export const RankingReal = () => <AnalysisGate><RankingContent /></AnalysisGate>
export const FornecedoresReal = () => <AnalysisGate><SuppliersContent /></AnalysisGate>
