import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Search, FileOutput, ChevronDown, Calendar, ArrowRight, ScanSearch, ArrowDownWideNarrow } from 'lucide-react'
import { Head, Score, Prioridade, Revisao, Aviso, Tip } from '../components/ui.jsx'
import { processos, brl } from '../data.js'

const Sel = ({ label, v, icon: I = ChevronDown }) => (
  <div className="field"><label>{label}</label><div className="select"><span>{v}</span><I size={16} color="var(--secundario)" /></div></div>
)

export default function Processos() {
  const nav = useNavigate()
  const [params] = useSearchParams()
  const [aba, setAba] = useState(params.get('aba') || 'sinalizados')
  useEffect(() => setAba(params.get('aba') || 'sinalizados'), [params])
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(processos[0].id)
  const lista = useMemo(() => processos.filter(p => {
    const okAba = aba === 'alta' ? p.score >= 80 : aba === 'media' ? p.score >= 50 && p.score < 80 : aba === 'sinalizados' ? p.score >= 50 : true
    return okAba && `${p.id} ${p.cat} ${p.forn} ${p.orgao}`.toLowerCase().includes(q.toLowerCase())
  }), [aba, q])
  const atual = processos.find(p => p.id === sel)
  const tabs = [['sinalizados', 'Sinalizados · 308'], ['alta', 'Alta prioridade · 96'], ['media', 'Média prioridade · 212'], ['todos', 'Todos · 1.248']]
  return (
    <>
      <Head kicker="Fila de análise / Ranking" title="Processos sinalizados" sub="Encontre os casos prioritários. Dica: clique em uma linha para selecioná-la e depois em “Ver detalhe do processo”."
        action={<Link to="/relatorios" className="btn primary"><FileOutput size={16} /> Preparar relatório</Link>} />
      <div className="card">
        <div className="mini"><h2>Refine o recorte</h2><button className="link-a" style={{ background: 'none', border: 0 }} onClick={() => { setQ(''); setAba('sinalizados') }}>Limpar filtros</button></div>
        <p className="sub">Filtros visuais · nenhum filtro adicional aplicado</p>
        <div className="filters">
          <Sel label="Órgão contratante" v="Todos os órgãos" /><Sel label="Fornecedor" v="Todos os fornecedores" />
          <Sel label="Período de homologação" v="01 jan – 30 jun 2026" icon={Calendar} /><Sel label="Valor homologado" v="Qualquer valor" /><Sel label="Modalidade" v="Todas" />
        </div>
        <div className="tags">{['Preço / mediana: todos', 'Participantes: todos', 'Concentração / HHI: todos', 'Publicação–contrato: todos'].map(t => <span key={t} className="tag">{t}</span>)}<a className="link-a" style={{ fontSize: 11 }}>+ Atributos avançados</a></div>
      </div>
      <div className="tabs">{tabs.map(([k, l]) => <button key={k} className={aba === k ? 'on' : ''} onClick={() => setAba(k)}>{l}</button>)}</div>
      <div className="card">
        <div className="mini">
          <div className="input" style={{ maxWidth: 380 }}><Search size={16} color="var(--secundario)" /><input placeholder="Buscar processo, item ou fornecedor" value={q} onChange={e => setQ(e.target.value)} /></div>
          <span style={{ color: 'var(--secundario)', display: 'flex', gap: 8 }}><ArrowDownWideNarrow size={16} /> Ordenado por score: maior primeiro</span>
        </div>
        <table className="tbl">
          <thead><tr><th> Itens </th><th>Órgão / Fornecedor</th><th>Homologado</th><th><Tip text='Quantas vezes o preço é maior que a mediana de itens similares.'>Preço / med.</Tip></th><th>Particip.</th><th><Tip text='Nota de 0 a 100 de prioridade de análise. Não é probabilidade de fraude.'>Score ↓</Tip></th><th>Prioridade</th><th>Revisão</th></tr></thead>
          <tbody>
            {lista.map(p => (
              <tr key={p.id} className={`click ${p.id === sel ? 'sel' : ''}`} onClick={() => setSel(p.id)} onDoubleClick={() => nav(`/processos/${p.id}`)}>
                <td><Link className="link" to={`/processos/${p.id}`}>{p.id}</Link><small>{p.cat}</small></td>
                <td><b>{p.orgao}</b><small>{p.forn}</small></td><td>{brl(p.valor)}</td><td>{p.razao}</td><td>{p.part}</td>
                <td><Score v={p.score} /></td><td><Prioridade v={p.score} /></td><td><Revisao v={p.rev} /></td>
              </tr>
            ))}
            {!lista.length && <tr><td colSpan="8" style={{ textAlign: 'center', color: 'var(--secundario)' }}>Nenhum processo encontrado. Ajuste a busca ou limpe os filtros.</td></tr>}
          </tbody>
        </table>
        <div className="mini" style={{ marginTop: 16 }}>
          <span className="hint">1–{lista.length} de 308 processos sinalizados · score ≥ 50</span>
          <div className="pager"><button className="btn ghost sm">Anterior</button><span className="pill baixa">1 de 52</span><button className="btn ghost sm">Próxima</button></div>
        </div>
      </div>
      {atual && (
        <div className="sel-bar">
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}><ScanSearch color="var(--petroleo)" />
            <div><b>Selecionado: {atual.id} · {atual.forn}</b><p className="sub" style={{ marginTop: 2 }}>Score {atual.score} · preço {Math.round((parseFloat(atual.razao.replace(',', '.')) - 1) * 100)}% acima da mediana · {atual.part} participantes · revisão pendente</p></div></div>
          <Link to={`/processos/${atual.id}`} className="btn primary"><ArrowRight size={16} /> Ver detalhe do processo</Link>
        </div>
      )}
      <Aviso />
    </>
  )
}
