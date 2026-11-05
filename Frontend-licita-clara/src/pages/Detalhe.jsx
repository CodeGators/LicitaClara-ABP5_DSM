import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { FilePlus2, ClipboardCheck } from 'lucide-react'
import { Head, Aviso, Progress } from '../components/ui.jsx'
import { itens, derivar, razaoTxt, brl, nivel, nivelNome } from '../data.js'

const Info = ({ l, v, s }) => <div><small>{l}</small><strong>{v}</strong>{s && <small style={{ textTransform: 'none' }}>{s}</small>}</div>

export default function Detalhe() {
  const { id } = useParams()
  const p = itens.find(x => x.id === id)
  const d = p ? derivar(p) : null
  const [aba, setAba] = useState('sinais')
  const [status, setStatus] = useState(p?.rev || '')
  const [log, setLog] = useState([])
  if (!p) return <div className="card" role="alert"><h1>Exemplo não encontrado</h1><Link className="link-a" to="/itens">Consultar dados oficiais</Link></div>
  const marca = p.forn.split(' ')[0]
  const cmp = [['Mediana dos similares', d.unitMed, 'var(--petroleo)'], ['Estimado do item', d.unitEst, 'var(--secundario)'], ['Homologado do item', d.unitHom, 'var(--alta)']]
  const contrib = [
    { nome: 'Razão preço / mediana', val: razaoTxt(p.razao), sub: `${d.pctSobre}% acima dos itens comparáveis`, pct: 43 },
    { nome: 'Participação no gasto do órgão', val: '42%', sub: `${marca} · HHI do órgão: 0,31`, pct: 27 },
    { nome: 'Número de participantes', val: String(p.part), sub: 'Mediana dos similares: 6', pct: 18 },
    { nome: 'Publicação–contrato', val: '12 dias', sub: 'Mediana dos similares: 28 dias', pct: 12 },
  ]
  return (
    <>
      <Head kicker="Processos sinalizados / Detalhe do item" title={p.nome} sub={`${p.cat} · ${p.orgao} · Pregão eletrônico · ${p.id}`}
        action={<Link to={`/demonstracao/relatorios?item=${p.id}`} className="btn primary"><FilePlus2 size={16} /> Incluir no relatório</Link>} />
      <div className="card stack-md" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 220px', gap: 24 }}>
        <div className="stats" style={{ gridColumn: '1 / 4' }}>
          <Info l="Valor estimado" v={brl(d.estimado)} /><Info l="Valor homologado" v={brl(p.valor)} s="+14,3% sobre o estimado" /><Info l="Fornecedor" v={p.forn} />
          <Info l="Publicação → contrato" v="04 mai → 16 mai 2026" s="Intervalo de 12 dias" /><Info l="Frequência de contratação" v="18 contratos com o órgão" s={`Jan–Jun 2026 · ${marca}`} /><Info l="Situação da revisão" v={status} s="Sem conclusão de auditoria" />
        </div>
        <div className="score-box">
          <span className={`pill ${nivel(p.score)}`}>{nivelNome[nivel(p.score)]} prioridade</span>
          <div style={{ margin: '12px 0' }}><span className={`t-${nivel(p.score)}`} style={{ fontSize: 48, fontWeight: 500 }}>{p.score}</span> <span style={{ color: 'var(--secundario)' }}>/ 100</span></div>
          <small className="sub">Isolation Forest: {p.score} · Autoencoder: {d.auto}<br />Simulação ilustrativa, não validada</small>
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
            <p className="sub" style={{ marginTop: 16 }}>{p.nome} · {p.qtd.toLocaleString('pt-BR')} unidades<br />18 compras comparáveis no semestre · valores unitários simulados</p>
            <div style={{ display: 'grid', gap: 14, marginTop: 14 }}>
              {cmp.map(([l, v, c]) => (<div key={l}><div className="mini"><span>{l}</span><b style={{ color: c === 'var(--secundario)' ? 'inherit' : c }}>{brl(v)}</b></div><div style={{ height: 8 }} /><Progress pct={v} max={d.unitHom * 1.25} cor={c} /></div>))}
            </div>
            <p className="hint" style={{ justifyContent: 'flex-start', gap: 12, margin: '14px 0', flexWrap: 'wrap' }}><span className="pill alta">+{d.pctSobre}% vs. mediana</span> Faixa interquartil dos similares: {brl(d.faixa[0])}–{d.faixa[1].toLocaleString('pt-BR')}</p>
            <table className="tbl" style={{ marginTop: 0 }}>
              <thead><tr><th>Exemplo similar</th><th>Preço unitário</th><th>Participantes</th></tr></thead>
              <tbody>{d.similares.map(s => <tr key={s.id}><td>{s.id}<small>{s.orgao}</small></td><td>{brl(s.preco)}</td><td>{s.part}</td></tr>)}</tbody>
            </table>
            <p className="hint" style={{ display: 'block', marginTop: 12 }}>A comparação exige confirmar especificação, condições de entrega e equivalência das descrições. Itens raros podem gerar falsos positivos.</p>
          </div>
          <div className="card">
            <h2>Por que este item foi sinalizado?</h2><p className="sub">Contribuição por atributo · simulação explicativa</p>
            <div style={{ display: 'grid', gap: 20, marginTop: 20 }}>
              {contrib.map(c => (
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
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="field"><label>Status de análise</label>
            <select className="select" value={status} onChange={e => setStatus(e.target.value)}><option>A revisar</option><option>Em análise</option></select></div>
          <button className="btn outline" onClick={() => setLog(l => [`${new Date().toLocaleString('pt-BR')} · status: ${status}`, ...l])}><ClipboardCheck size={16} /> Registrar revisão</button>
        </div>
      </div>
    </>
  )
}
