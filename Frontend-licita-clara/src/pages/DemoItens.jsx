import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { FileOutput, ChevronDown, Calendar, ArrowRight, ScanSearch, ArrowDownWideNarrow } from 'lucide-react'
import { Head, Score, Prioridade, Revisao, Aviso, Tip } from '../components/ui.jsx'
import { itens, razaoTxt, brl } from '../data.js'
import FilterPanel from '../components/FilterPanel.jsx'
import { Field } from '../components/consultas.jsx'

const Visual = ({ label, v, icon: I = ChevronDown }) => (
  <div className="field"><label>{label}</label><div className="select"><span>{v}</span><I size={16} color="var(--secundario)" /></div></div>
)
const Pick = ({ label, value, onChange, todos, opts }) => (
  <Field label={label}>
    <select className="select" value={value} onChange={e => onChange(e.target.value)}>
      <option value="">{todos}</option>
      {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
    </select></Field>
)
const fornecedores = [...new Set(itens.map(p => p.forn))]

export default function Processos() {
  const nav = useNavigate()
  const [params] = useSearchParams()
  const [aba, setAba] = useState(params.get('aba') || 'sinalizados')
  useEffect(() => setAba(params.get('aba') || 'sinalizados'), [params])
  const [q, setQ] = useState('')
  const [item, setItem] = useState('')
  const [forn, setForn] = useState('')
  const [sel, setSel] = useState(itens[0].id)

  const lista = useMemo(() => itens.filter(p => {
    const okAba = aba === 'alta' ? p.score >= 80 : aba === 'media' ? p.score >= 50 && p.score < 80 : aba === 'sinalizados' ? p.score >= 50 : true
    return okAba && (!item || p.id === item) && (!forn || p.forn === forn) && `${p.nome} ${p.cat} ${p.forn}`.toLowerCase().includes(q.toLowerCase())
  }), [aba, q, item, forn])
  const atual = lista.find(p => p.id === sel) || lista[0]
  const limpar = () => { setQ(''); setItem(''); setForn(''); setAba('sinalizados') }
  const tabs = [['sinalizados', 'Sinalizados · 308'], ['alta', 'Alta prioridade · 96'], ['media', 'Média prioridade · 212'], ['todos', 'Todos · 1.248']]

  return (
    <>
      <Head kicker="Fila de análise / Ranking" title="Itens Sinalizados" sub="Encontre os itens prioritários. Dica: clique em uma linha para selecioná-la e depois em “Ver detalhe do item”."
        action={<Link to={`/demonstracao/relatorios?item=${atual?.id || itens[0].id}`} className="btn primary"><FileOutput size={16} /> Preparar relatório</Link>} />
      <FilterPanel title="Filtrar itens" clear={limpar} twoColumns primary={<>
        <Field label="Buscar item ou fornecedor"><input className="input" type="search" placeholder="Buscar item ou fornecedor" value={q} onChange={e => setQ(e.target.value)} /></Field>
        <Pick label="Item" value={item} onChange={setItem} todos="Todos os itens" opts={itens.map(p => [p.id, p.nome])} />
      </>} advanced={<div className="item-filters-lookups">
        <Pick label="Fornecedor" value={forn} onChange={setForn} todos="Todos os fornecedores" opts={fornecedores.map(f => [f, f])} />
        <Visual label="Período de homologação" v="01 jan – 30 jun 2026" icon={Calendar} />
        <Visual label="Valor homologado" v="Qualquer valor" />
        <Visual label="Modalidade" v="Todas" />
      </div>} />
      <div className="tabs">{tabs.map(([k, l]) => <button key={k} className={aba === k ? 'on' : ''} onClick={() => setAba(k)}>{l}</button>)}</div>
      <div className="card">
        <div className="mini">
          <span style={{ color: 'var(--secundario)', display: 'flex', gap: 8 }}><ArrowDownWideNarrow size={16} /> Ordenado por score: maior primeiro</span>
        </div>
        <table className="tbl">
          <thead><tr><th>Item / Categoria</th><th>Fornecedor</th><th>Homologado</th>
            <th><Tip text="Quantas vezes o preço é maior que a mediana de itens similares.">Preço / med.</Tip></th><th>Particip.</th>
            <th><Tip text="Nota de 0 a 100 de prioridade de análise. Não é probabilidade de fraude.">Score ↓</Tip></th><th>Prioridade</th><th>Revisão</th></tr></thead>
          <tbody>
            {lista.map(p => (
              <tr key={p.id} className={`click ${p.id === atual?.id ? 'sel' : ''}`} onClick={() => setSel(p.id)} onDoubleClick={() => nav(`/demonstracao/itens/${p.id}`)}>
                <td><Link className="link" to={`/demonstracao/itens/${p.id}`}>{p.nome}</Link><small>{p.cat}</small></td>
                <td>{p.forn}</td><td>{brl(p.valor)}</td><td>{razaoTxt(p.razao)}</td><td>{p.part}</td>
                <td><Score v={p.score} /></td><td><Prioridade v={p.score} /></td><td><Revisao v={p.rev} /></td>
              </tr>
            ))}
            {!lista.length && <tr><td colSpan="8" style={{ textAlign: 'center', color: 'var(--secundario)', whiteSpace: 'normal' }}>Nenhum item encontrado. Ajuste a busca ou limpe os filtros.</td></tr>}
          </tbody>
        </table>
        <div className="mini" style={{ marginTop: 16 }}>
          <span className="hint">1–{lista.length} de 308 itens sinalizados · score ≥ 50</span>
          <div className="pager"><button className="btn ghost sm">Anterior</button><span className="pill baixa">1 de 52</span><button className="btn ghost sm">Próxima</button></div>
        </div>
      </div>
      {atual && (
        <div className="sel-bar">
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}><ScanSearch color="var(--petroleo)" />
            <div><b>Selecionado: {atual.nome} · {atual.forn}</b><p className="sub" style={{ marginTop: 2 }}>Score {atual.score} · preço {Math.round((atual.razao - 1) * 100)}% acima da mediana · {atual.part} participantes · revisão pendente</p></div></div>
          <Link to={`/demonstracao/itens/${atual.id}`} className="btn primary"><ArrowRight size={16} /> Ver detalhe do item</Link>
        </div>
      )}
      <Aviso />
    </>
  )
}
