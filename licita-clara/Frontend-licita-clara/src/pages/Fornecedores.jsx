import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, FileOutput, Building2, Landmark, ScanSearch, ChevronDown } from 'lucide-react'
import { Head, Score, Prioridade, Revisao, Aviso, Progress, Tip } from '../components/ui.jsx'
import { fornecedores, participacao, processos, brl } from '../data.js'

export default function Fornecedores() {
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(fornecedores[0].nome)
  const lista = useMemo(() => fornecedores.filter(f => f.nome.toLowerCase().includes(q.toLowerCase())), [q])
  const f = fornecedores.find(x => x.nome === sel)
  const rel = processos.filter(p => p.forn === sel)
  const K = ({ l, v, s, i: I }) => <div className="card kpi"><div className="row"><span>{l}</span><I size={18} color="var(--petroleo)" /></div><strong>{v}</strong><small>{s}</small></div>
  return (
    <>
      <Head kicker="Relações e concentração / Jan–Jun 2026" title="Fornecedores" sub="Explore vínculos de contratação e participação no gasto de cada órgão."
        action={<Link to="/relatorios" className="btn primary"><FileOutput size={16} /> Preparar relatório</Link>} />
      <div className="grid g3">
        <K l="Fornecedores no recorte" v="146" s="Entidades fictícias · base demonstrativa" i={Building2} />
        <K l="Órgãos contratantes" v="8" s="Concentração calculada por órgão" i={Landmark} />
        <K l="Com processos de alta prioridade" v="38" s="Fornecedores com pelo menos um score ≥ 80" i={ScanSearch} />
      </div>
      <div className="grid g-15-1">
        <div className="card">
          <h2>Ranking de fornecedores</h2><p className="sub">Ordenação: maior score entre os processos do fornecedor</p>
          <div className="grid g-12-1">
            <div className="field"><label>Fornecedor</label><div className="input"><input placeholder="Buscar por razão social" value={q} onChange={e => setQ(e.target.value)} /><Search size={16} color="var(--secundario)" /></div></div>
            <div className="field"><label>Órgão</label><div className="select"><span>Todos os órgãos</span><ChevronDown size={16} /></div></div>
          </div>
          <table className="tbl">
            <thead><tr><th>Fornecedor</th><th>Contratos</th><th>Homologado</th><th>Maior score</th></tr></thead>
            <tbody>{lista.map(x => (
              <tr key={x.nome} className={`click ${x.nome === sel ? 'sel' : ''}`} onClick={() => setSel(x.nome)}>
                <td><span className={x.nome === sel ? 'link' : ''}>{x.nome}</span><small>{x.orgaos} órgãos · {x.altos} processos com score ≥ 80</small></td>
                <td>{x.contratos}</td><td>{x.valor}</td><td><Score v={x.score} /></td></tr>))}</tbody>
          </table>
          <div className="mini" style={{ marginTop: 16 }}><span className="hint">1–{lista.length} de 146 fornecedores fictícios</span><a className="link-a">Próxima página →</a></div>
        </div>
        <div className="grid">
          <div className="card">
            <div className="mini"><h2>{f.nome}</h2><span className="pill ana">Selecionado</span></div>
            <p className="sub">Fornecedor selecionado · entidade fictícia</p>
            <div className="stats" style={{ margin: '20px 0 16px' }}>
              <div><strong style={{ fontSize: 30, fontWeight: 400 }}>{f.contratos}</strong><small>contratos</small></div>
              <div><strong style={{ fontSize: 24, fontWeight: 400 }}>{f.valor}</strong><small>homologado</small></div>
              <div><strong style={{ fontSize: 30, fontWeight: 400 }}>{f.orgaos}</strong><small>órgãos</small></div>
            </div>
            <p className="hint" style={{ display: 'block' }}>Maior score: {f.score}<br />Frequência no Instituto Vale Azul: 18 contratos no semestre</p>
          </div>
          <div className="card">
            <h2>Participação no gasto por órgão</h2><p className="sub">Valor da Nexo ÷ total homologado pelo órgão no recorte</p>
            <div style={{ display: 'grid', gap: 18, marginTop: 20 }}>
              {participacao.map(o => (
                <div key={o.orgao}><div className="mini"><b>{o.orgao}</b><b className="t-pet">{o.pct}%</b></div><div style={{ height: 8 }} />
                  <Progress pct={o.pct} max={100} /><p className="hint" style={{ marginTop: 4 }}><span>{o.info}</span><Tip text='Índice de concentração de 0 a 1: quanto maior, mais concentrado o gasto do órgão.'>HHI: {o.hhi}</Tip></p></div>))}
            </div>
            <p className="hint" style={{ display: 'block', borderTop: '1px solid var(--divisoria)', paddingTop: 12, marginTop: 16 }}>HHI mede a concentração de todos os fornecedores no órgão, de 0 a 1. Quanto maior, mais concentrado. Concentração, isoladamente, não indica irregularidade.</p>
          </div>
        </div>
      </div>
      <div className="card">
        <div className="mini"><h2>Processos relacionados à {f.nome.split(' ')[0]}</h2><a className="link-a">Ver os {f.contratos} contratos →</a></div>
        <p className="sub">{rel.length ? 'Exemplos de alta prioridade' : 'Nenhum processo de alta prioridade neste fornecedor'}</p>
        {!!rel.length && <table className="tbl">
          <thead><tr><th>Processo / Categoria</th><th>Homologado</th><th>Score</th><th>Prioridade</th><th>Revisão</th></tr></thead>
          <tbody>{rel.map(p => <tr key={p.id}><td><Link className="link" to={`/processos/${p.id}`}>{p.id}</Link><small>{p.cat}</small></td><td>{brl(p.valor)}</td><td><Score v={p.score} /></td><td><Prioridade v={p.score} /></td><td><Revisao v={p.rev} /></td></tr>)}</tbody>
        </table>}
      </div>
      <Aviso />
    </>
  )
}
