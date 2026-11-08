import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Download, FileCheck, Check } from 'lucide-react'
import { Head } from '../components/ui.jsx'
import { Mark } from '../components/Logo.jsx'
import { Field, QueryState } from '../components/consultas.jsx'
import { AnalysisSelector, useAnalysis } from '../AnalysisContext.jsx'
import { useBase } from '../BaseContext.jsx'
import { date, decimal, exactDecimal, money } from '../api.mjs'
import useApi from '../useApi.js'
import FilterPanel from '../components/FilterPanel.jsx'

const apiBase = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
export default function Relatorios() {
  const { baseId } = useBase()
  const analysis = useAnalysis()
  const [params, setParams] = useSearchParams()
  const processId = params.get('processo_id') || ''
  const [busca, setBusca] = useState('')
  const [search, setSearch] = useState('')
  const [titulo, setTitulo] = useState('Relatório de anomalias')
  const [appliedTitle, setAppliedTitle] = useState('Relatório de anomalias')
  const [format, setFormat] = useState('pdf')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const processes = useApi('/processos', { base_id: baseId, busca: search, tamanho_pagina: 100 }, !!baseId)
  const selectionReady = analysis.ready && (!analysis.executionId || !!analysis.run.data)
  const queryParams = { base_id: baseId, execucao_id: analysis.executionId || undefined, titulo: appliedTitle }
  const preview = useApi(`/relatorios/processos/${encodeURIComponent(processId)}/previa`, queryParams, !!processId && selectionReady)
  const data = preview.data
  const setProcess = value => { setError(''); setParams(previous => { const next = new URLSearchParams(previous); next.set('processo_id', value); next.delete('item'); return next }) }
  const download = async () => {
    setBusy(true); setError('')
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 30000)
    try {
      const options = new URLSearchParams({ base_id: baseId, titulo: data.titulo, formato: format, snapshot_sha256: data.snapshot_sha256 })
      if (data.analise) options.set('execucao_id', data.analise.id)
      const response = await fetch(`${apiBase}/relatorios/processos/${encodeURIComponent(processId)}/arquivo?${options}`, { signal: controller.signal })
      if (!response.ok) { const body = await response.json(); throw new Error(body.erro?.mensagem || 'Não foi possível gerar o arquivo.') }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url; anchor.download = `licita-clara-${processId.slice(0, 8)}.${format}`
      document.body.appendChild(anchor); anchor.click(); anchor.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (e) { setError(e.name === 'AbortError' ? 'A exportação demorou mais que o esperado. Tente novamente.' : e.message || 'Não foi possível exportar.') }
    finally { clearTimeout(timer); setBusy(false) }
  }
  const process = data?.processo
  return <>
    <Head kicker="Exportação / Anomalias em compras públicas" title="Relatórios" sub="Selecione o processo, confira a prévia e baixe os dados reais."
      action={<button className="btn primary" onClick={download} disabled={!data || busy || titulo !== appliedTitle}><Download size={16} />{busy ? 'Gerando arquivo…' : `Exportar ${format.toUpperCase()}`}</button>} />
    <AnalysisSelector allModels />
    <FilterPanel title="Selecionar licitação" ariaLabel="Filtros do relatório" twoColumns apply={e => { e.preventDefault(); setSearch(busca.trim()) }} applyLabel="Buscar" clear={() => { setBusca(''); setSearch(''); setProcess('') }} primary={<>
      <Field label="Buscar processo"><input className="input" type="search" value={busca} maxLength={200} onChange={e => setBusca(e.target.value)} /></Field>
      <Field label="Processo selecionado"><select className="select" value={processId} onChange={e => setProcess(e.target.value)}>
        <option value="">Selecione um processo</option>
        {processId && !processes.data?.dados.some(p => p.id === processId) && <option value={processId}>{process?.numero_compra || processId}</option>}
        {processes.data?.dados.map(p => <option value={p.id} key={p.id}>Compra {p.numero_compra} · {p.orgao_nome}</option>)}
      </select></Field>
    </>}>
      <QueryState query={processes} loading="Carregando processos…" />
      {processes.data?.meta.total > 100 && <p className="hint">Mostrando os primeiros 100 processos. Refine a busca para encontrar os demais.</p>}
    </FilterPanel>
    <div className="grid stack-md report-grid">
      <div className="grid report-config">
        <section className="card"><h2>Configurar exportação</h2>
          <form onSubmit={e => { e.preventDefault(); setAppliedTitle(titulo.trim()); setTitulo(titulo.trim()); setError('') }}>
            <Field label="Título do relatório"><input className="input" required maxLength={120} value={titulo} onChange={e => setTitulo(e.target.value)} /></Field>
            <button className="btn" type="submit" disabled={!titulo.trim()}>Atualizar prévia</button>
          </form>
          <Field label="Formato"><div className="radio">{['pdf', 'csv'].map(f => <button key={f} type="button" aria-pressed={format === f} className={format === f ? 'on' : ''} onClick={() => setFormat(f)}>{f.toUpperCase()}</button>)}</div></Field>
          <p className="hint">Período da base: {date(data?.base.periodo_inicio)} – {date(data?.base.periodo_fim)}</p>
          <hr />
          <h3>O relatório inclui</h3>
          {['Síntese e valores do processo', 'Itens, resultados e índices dos modelos', 'Comparações disponíveis, fontes e limitações'].map(text => <p className="check-fixo" key={text}><Check size={16} />{text}</p>)}
          <p className="hint">Até 200 itens por processo. O PDF pode ter várias páginas. O CSV tem uma linha por resultado/modelo; não some valores repetidos entre modelos.</p>
        </section>
        {data && <div className="dark-card"><FileCheck size={22} /><b>Prévia pronta para revisão</b><p>{data.resumo.itens} itens importados · {data.resumo.itens_analisados} com análise<br />{data.resumo.scores} pontuações, mantendo os algoritmos separados.</p></div>}
      </div>
      <div>
        {error && <div className="card" role="alert">{error} <button className="link-a" onClick={preview.retry}>Atualizar prévia</button></div>}
        {!processId ? <section className="card"><h2>{params.has('item') ? 'Relatório indisponível' : 'Selecione um processo'}</h2><p>Escolha uma compra na configuração ou abra o relatório pelo detalhe do processo.</p></section> : <QueryState query={preview} loading="Preparando a prévia…" />}
        {data && <div className="preview report-preview"><div className="mini"><b>Prévia do relatório</b><span className="hint">{data.resumo.itens} itens no recorte</span></div>
          <article className="paper">
            <div className="mini"><div className="mono-row"><Mark size={34} /><span><b>Licita</b> Clara</span></div><small>ANÁLISE DE ANOMALIAS</small></div>
            <hr className="report-rule" /><h2>{data.titulo}</h2>
            <p className="sub">Compra {process.numero_compra} · {process.orgao_nome}</p>
            <span className="demo">Dados oficiais · {data.analise ? 'análise experimental' : 'sem análise selecionada'}</span>
            <h3>01 / Síntese do processo</h3><p>{process.objeto}</p>
            <div className="stats"><div><small>Estimado global</small><strong>{money(process.valor_estimado_processo)}</strong></div><div><small>Homologado global</small><strong>{money(process.valor_homologado_processo)}</strong></div><div><small>Homologado no recorte</small><strong>{money(process.valor_homologado_itens_recorte)}</strong></div></div>
            <p className="hint">Valores globais e do recorte são medidas distintas. O recorte pode conter somente parte da compra.</p>
            <h3>02 / Sinais e comparação de itens</h3>
            {data.itens.map(item => <section className="report-item" key={item.id}><h4>Item {item.numero_item} · {item.descricao}</h4><p title={`Estimado unitário original: ${exactDecimal(item.valor_unitario_estimado)}`}>Unidade: {item.unidade_medida || 'Não informada'} · Quantidade: {decimal(item.quantidade)} · Estimado unitário: {money(item.valor_unitario_estimado)}</p>
              {item.resultados.length ? item.resultados.map(r => <p key={r.id} title={`Preço unitário original: ${exactDecimal(r.valor_unitario_homologado)}`}>{r.fornecedor_nome} · {r.cancelado ? 'Cancelado' : 'Não cancelado'} · Unitário: {money(r.valor_unitario_homologado)} · Quantidade homologada: {decimal(r.quantidade_homologada)} · Total: {money(r.valor_total_homologado)} · Data: {date(r.data_resultado)}</p>) : <p>Sem resultado conhecido.</p>}
              {item.scores.length ? item.scores.map(s => <div className="note" key={s.id} title={`Mediana original: ${exactDecimal(s.mediana_treino)}`}><b>{s.algoritmo} · Índice {decimal(s.indice)} / 100</b>Mediana do treino: {money(s.mediana_treino)} · Preço/mediana: {decimal(s.razao_preco_mediana)} · Exemplos de treino: {s.n_treino ?? 'Não informado'}<small>Resultado: {s.resultado_item_id} · Modelo: {s.modelo_id}<br />Fonte: {s.fonte.membro || 'Não informada'} · registro {s.fonte.linha ?? 'não informado'} · SHA-256: {s.fonte.arquivo_sha256 || 'não informado'}</small></div>) : <p>Sem análise disponível para este item na seleção.</p>}
              {!!item.cobertura.filter(r => r.motivo).length && <p className="hint">Motivos de ausência: {[...new Set(item.cobertura.map(r => r.motivo).filter(Boolean))].join(', ')}</p>}
            </section>)}
            <h3>03 / Método e limites de interpretação</h3><div className="note">{data.limites.map(text => <p key={text}>{text}</p>)}</div>
            <h3>Fonte e rastreabilidade</h3><p>{data.fonte}</p>
            <p className="hint">Base: {data.base.id} · versão {data.base.versao}<br />Manifesto da base: {data.base.manifesto_sha256}<br />Execução: {data.analise?.id || 'Sem análise selecionada'}<br />Manifesto da análise: {data.analise?.manifesto_sha256 || 'Não disponível'}<br />Snapshot: {data.snapshot_sha256}</p>
            <Link className="link-a" to={`/processos/${process.id}?${new URLSearchParams({ base_id: baseId, ...(data.analise ? { execucao_id: data.analise.id } : {}) })}`}>Ver processo da compra →</Link>
          </article>
        </div>}
      </div>
    </div>
  </>
}
