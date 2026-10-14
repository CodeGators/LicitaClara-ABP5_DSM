import { Link } from 'react-router-dom'
import { Calendar, Files, Wallet, TriangleAlert, ScanSearch } from 'lucide-react'
import { Head, Score, Aviso, Tip } from '../components/ui.jsx'
import { processos, distribuicao, evolucao, brl } from '../data.js'

const cor = i => (i < 5 ? 'var(--baixa)' : i < 8 ? 'var(--media)' : 'var(--alta)')
const faixas = ['0–9','10–19','20–29','30–39','40–49','50–59','60–69','70–79','80–89','90–100']

function Kpi({ label, value, sub, icon: I, cls, to, tip }) {
  return (
    <Link to={to} className="card kpi click-card" title="Clique para ver a lista">
      <div className="row"><span>{tip ? <Tip text={tip}>{label}</Tip> : label}</span><I size={18} color="var(--petroleo)" /></div>
      <strong className={cls}>{value}</strong><small>{sub}</small>
    </Link>
  )
}

function Linha() {
  const W = 520, H = 170, max = 30
  const pts = evolucao.map(([, v], i) => [40 + i * ((W - 60) / 5), H - 30 - (v / max) * (H - 50)])
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Evolução mensal da alta prioridade">
      {[0, 10, 20, 30].map(t => {
        const y = H - 30 - (t / max) * (H - 50)
        return <g key={t}><line x1="30" x2={W} y1={y} y2={y} stroke="var(--divisoria)" /><text x="0" y={y + 4} fontSize="11" fill="var(--secundario)">{t}</text></g>
      })}
      <path d={`${d} L${pts[5][0]},${H - 30} L${pts[0][0]},${H - 30}Z`} fill="var(--sel)" opacity=".7" />
      <path d={d} fill="none" stroke="var(--petroleo)" strokeWidth="2.5" />
      {pts.map((p, i) => (
        <g key={i}><circle cx={p[0]} cy={p[1]} r="3.5" fill="var(--superficie)" stroke="var(--petroleo)" strokeWidth="2" />
          <text x={p[0]} y={p[1] - 10} fontSize="11" fontWeight="600" textAnchor="middle" fill="var(--petroleo)">{evolucao[i][1]}</text>
          <text x={p[0]} y={H - 10} fontSize="11" textAnchor="middle" fill="var(--secundario)">{evolucao[i][0]}</text></g>
      ))}
    </svg>
  )
}

export default function Painel() {
  return (
    <>
      <Head kicker="Visão consolidada / Jan–Jun 2026" title="Clareza para priorizar a análise." sub="Acompanhe sinais estatísticos de compras públicas em um único lugar."
        action={<button className="btn ghost"><Calendar size={16} /> Jan–Jun 2026</button>} />
      <div className="grid g4">
        <Kpi label="Processos no recorte" value="1.248" sub="8 órgãos fictícios · 146 fornecedores" icon={Files} to="/processos?aba=todos" />
        <Kpi label="Valor homologado" value="R$ 86,4 mi" sub="Compras e contratos do semestre" icon={Wallet} to="/fornecedores" />
        <Kpi label="Alta prioridade" value="96" cls="t-alta" sub="7,7% do recorte · score de 80 a 100" icon={TriangleAlert} to="/processos?aba=alta" tip="Processos com score de 80 a 100, que merecem revisão primeiro." />
        <Kpi label="Em revisão humana" value="24" sub="Dos 96 processos de alta prioridade" icon={ScanSearch} to="/processos?aba=sinalizados" />
      </div>
      <div className="grid g-1-1">
        <div className="card">
          <h2>Distribuição de scores</h2><p className="sub">Score de 0 a 100 · prioridade de análise, não probabilidade de fraude</p>
          <div className="bars">
            {distribuicao.map((v, i) => (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <small style={{ color: 'var(--secundario)', fontSize: 11 }}>{v}</small>
                <div style={{ width: '100%', height: v / 2, background: cor(i), borderRadius: '3px 3px 0 0' }} />
              </div>
            ))}
          </div>
          <div className="bars-lbl">{faixas.map(f => <small key={f} style={{ flex: 1, textAlign: 'center', fontSize: 10, color: 'var(--secundario)' }}>{f}</small>)}</div>
          <div className="hint" style={{ justifyContent: 'flex-start', gap: 16, marginTop: 16 }}>
            <span className="t-baixa">● Baixa · 940</span><span className="t-media">● Média · 212</span><span className="t-alta">● Alta · 96</span>
          </div>
        </div>
        <div className="card">
          <div className="mini"><h2>Evolução da alta prioridade</h2><span className="pill baixa">Simulação</span></div>
          <p className="sub">Quantidade de processos por mês de homologação</p>
          <div style={{ marginTop: 16 }}><Linha /></div>
          <p className="hint" style={{ marginTop: 8 }}>96 processos de alta prioridade no semestre · score ≥ 80</p>
        </div>
      </div>
      <div className="grid g-19-1">
        <div className="card">
          <div className="mini"><h2>Por onde começar</h2><Link to="/processos" className="link-a">Ver todos →</Link></div>
          <p className="sub">Maiores scores do recorte · ordenados por prioridade</p>
          <table className="tbl">
            <thead><tr><th>Processo</th><th>Órgão / Fornecedor</th><th>Homologado</th><th>Score</th></tr></thead>
            <tbody>{processos.slice(0, 3).map((p, i) => (
              <tr key={p.id} className={i === 0 ? 'sel' : ''}>
                <td><Link className="link" to={`/processos/${p.id}`}>{p.id}</Link><small>{p.cat}</small></td>
                <td><b>{p.orgao}</b><small>{p.forn}</small></td><td>{brl(p.valor)}</td><td><Score v={p.score} /></td>
              </tr>))}</tbody>
          </table>
        </div>
        <div className="card">
          <h2>Leitura dos modelos</h2><p className="sub">Comparação ilustrativa · não validada</p>
          <p style={{ margin: '16px 0 12px' }}>Exemplo selecionado: LC-2026-0142</p>
          {[['Isolation Forest', '92'], ['Autoencoder', '88']].map(([n, v]) => (
            <div key={n} className="mini" style={{ padding: '8px 0' }}><span>{n}</span><span className="t-pet">{v} / 100</span></div>
          ))}
          <p className="hint" style={{ marginTop: 16, display: 'block', borderTop: '1px solid var(--divisoria)', paddingTop: 12 }}>Scores simulados em escala ilustrativa. Sem modelo treinado, rótulos ou métricas de acurácia neste protótipo.</p>
        </div>
      </div>
      <Aviso detalhe />
    </>
  )
}
