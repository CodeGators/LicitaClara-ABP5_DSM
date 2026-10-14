import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FilePlus2, ClipboardCheck, ChevronDown } from 'lucide-react'
import { Head, Aviso, Progress } from '../components/ui.jsx'
import { processos, similares, contribuicoes, brl, nivel, nivelNome } from '../data.js'

export default function Detalhe() {
  const { id } = useParams()
  const p = processos.find(x => x.id === id) || processos[0]
  const [aba, setAba] = useState('sinais')
  const [status, setStatus] = useState('A revisar')
  const [log, setLog] = useState([])
  const Info = ({ l, v, s }) => <div><small>{l}</small><strong>{v}</strong>{s && <small style={{ textTransform: 'none' }}>{s}</small>}</div>
  const cmp = [['Mediana dos similares', 7500, 'var(--petroleo)'], ['Estimado do processo', 10500, 'var(--secundario)'], ['Homologado do processo', 12000, 'var(--alta)']]
  return (
    <>
      <Head kicker="Processos sinalizados / Detalhe" title={p.id} sub={`${p.cat} · ${p.orgao} · Pregão eletrônico`}
        action={<Link to="/relatorios" className="btn primary"><FilePlus2 size={16} /> Incluir no relatório</Link>} />
      <div className="card dh">
        <div className="stats">
          <Info l="Valor estimado" v="R$ 420.000" /><Info l="Valor homologado" v={brl(p.valor)} s="+14,3% sobre o estimado" /><Info l="Fornecedor" v={p.forn} />
          <Info l="Publicação → contrato" v="04 mai → 16 mai 2026" s="Intervalo de 12 dias" /><Info l="Frequência de contratação" v="18 contratos com o órgão" s="Jan–Jun 2026 · Nexo Suprimentos" /><Info l="Situação da revisão" v={status} s="Sem conclusão de auditoria" />
        </div>
        <div className="dh-score">
          <span className={`pill ${nivel(p.score)}`}>{nivelNome[nivel(p.score)]} prioridade</span>
          <div style={{ margin: '12px 0' }}><span className={`t-${nivel(p.score)}`} style={{ fontSize: 48, fontWeight: 500 }}>{p.score}</span> <span style={{ color: 'var(--secundario)' }}>/ 100</span></div>
          <small className="sub">Isolation Forest: 92 · Autoencoder: 88<br />Simulação ilustrativa, não validada</small>
        </div>
      </div>
      <Aviso detalhe />
      <div className="tabs">
        {[['sinais', 'Sinais e comparação'], ['docs', 'Documentos · 0'], ['reg', 'Registro da revisão']].map(([k, l]) => <button key={k} className={aba === k ? 'on' : ''} onClick={() => setAba(k)}>{l}</button>)}
      </div>
      {aba === 'sinais' && (
        <div className="grid g-1-1" style={{ alignItems: 'start' }}>
          <div className="card">
            <h2>Comparação com itens similares</h2><p className="sub">Preço homologado por unidade · mesma categoria e especificação</p>
            <p className="sub" style={{ marginTop: 16 }}>Notebook · i5 / 16 GB / SSD 512 GB · 40 unidades<br />18 compras comparáveis no semestre · valores unitários simulados</p>
            <div style={{ display: 'grid', gap: 14, marginTop: 14 }}>
              {cmp.map(([l, v, c]) => (<div key={l}><div className="mini"><span>{l}</span><b style={{ color: c === 'var(--secundario)' ? 'inherit' : c }}>{brl(v)}</b></div><div style={{ height: 8 }} /><Progress pct={v} max={15000} cor={c} /></div>))}
            </div>
            <p className="hint" style={{ justifyContent: 'flex-start', gap: 12, margin: '14px 0' }}><span className="pill alta">+60% vs. mediana</span> Faixa interquartil dos similares: R$ 6.800–8.200</p>
            <table className="tbl" style={{ marginTop: 0 }}>
              <thead><tr><th>Exemplo similar</th><th>Preço unitário</th><th>Participantes</th></tr></thead>
              <tbody>{similares.map(s => <tr key={s.id}><td>{s.id}<small>{s.orgao}</small></td><td>{brl(s.preco)}</td><td>{s.part}</td></tr>)}</tbody>
            </table>
            <p className="hint" style={{ display: 'block', marginTop: 12 }}>A comparação exige confirmar especificação, condições de entrega e equivalência das descrições. Itens raros podem gerar falsos positivos.</p>
          </div>
          <div className="card">
            <h2>Por que este processo foi sinalizado?</h2><p className="sub">Contribuição por atributo · simulação explicativa</p>
            <div style={{ display: 'grid', gap: 20, marginTop: 20 }}>
              {contribuicoes.map(c => (
                <div key={c.nome}><div className="mini"><span>{c.nome}</span><b className="t-media">{c.val}</b></div>
                  <p className="hint" style={{ marginTop: 2 }}>{c.sub}</p>
                  <div style={{ height: 6 }} /><Progress pct={c.pct} max={45} cor="var(--media)" /><p className="hint" style={{ justifyContent: 'flex-end', marginTop: 4 }}>{c.pct}%</p></div>
              ))}
            </div>
            <p className="hint" style={{ display: 'block', borderTop: '1px solid var(--divisoria)', paddingTop: 12, margin: '12px 0 16px' }}>Pesos ilustrativos de contribuição por atributo; não são valores SHAP calculados. Explicam a composição visual do exemplo, sem validação do modelo.</p>
            <div className="note"><b>Próxima etapa da revisão</b>Verificar pesquisa de preços, especificações e justificativa de competitividade antes de qualquer conclusão.</div>
          </div>
        </div>
      )}
      {aba === 'docs' && <div className="card"><h2>Documentos</h2><p className="sub">Nenhuma evidência anexada neste protótipo.</p></div>}
      {aba === 'reg' && <div className="card"><h2>Registro da revisão</h2>{log.length ? log.map((l, i) => <p key={i} className="sub">{l}</p>) : <p className="sub">Nenhuma revisão registrada ainda.</p>}</div>}
      <div className="card mini">
        <div><h2>Registre a revisão humana</h2><p className="sub">Nenhuma evidência anexada neste protótipo. A análise permanece pendente até a verificação documental.</p></div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end' }}>
          <div className="field"><label>Status de análise</label>
            <select className="select" value={status} onChange={e => setStatus(e.target.value)}><option>A revisar</option><option>Em análise</option></select></div>
          <button className="btn outline" onClick={() => setLog(l => [`${new Date().toLocaleString('pt-BR')} · status: ${status}`, ...l])}><ClipboardCheck size={16} /> Registrar revisão</button>
        </div>
      </div>
    </>
  )
}
