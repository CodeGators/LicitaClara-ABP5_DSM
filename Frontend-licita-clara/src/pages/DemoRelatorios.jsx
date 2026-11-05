import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Download, Pencil, Calendar, ChevronDown, FileCheck, CircleDot, Circle, Check } from 'lucide-react'
import { Head } from '../components/ui.jsx'
import { Mark } from '../components/Logo.jsx'
import { itens, derivar, razaoTxt, brl } from '../data.js'

const Sec = ({ children }) => <h4 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{children}</h4>

export default function Relatorios() {
  const [params] = useSearchParams()
  const p = params.get('item') ? itens.find(x => x.id === params.get('item')) : itens[0]
  const d = p ? derivar(p) : null
  const [titulo, setTitulo] = useState('Prioridade de análise')
  const [fmt, setFmt] = useState('PDF')
  if (!p) return <div className="card" role="alert"><h1>Relatório indisponível</h1><p className="sub">Esta demonstração não gera relatórios dos itens reais. A emissão estará disponível após a integração dos relatórios.</p></div>
  const marca = p.forn.split(' ')[0]
  const rows = [
    ['Preço unitário / mediana', razaoTxt(p.razao), `${brl(d.unitHom)} / ${brl(d.unitMed)}`],
    ['Participantes', String(p.part), 'Mediana: 6'],
    ['Participação no gasto do órgão', '42%', 'HHI do órgão: 0,31'],
    ['Publicação–contrato', '12 dias', 'Mediana: 28 dias'],
  ]
  return (
    <>
      <Head kicker="Exportação / Auditoria e compliance" title="Relatórios" sub="Defina o item, revise a prévia e documente os sinais com responsabilidade."
        action={<button className="btn primary no-print" onClick={() => window.print()}><Download size={16} /> Exportar {fmt}</button>} />
      <div className="grid stack-md" style={{ gridTemplateColumns: '340px 1fr', alignItems: 'start' }}>
        <div className="grid no-print">
          <div className="card">
            <h2>Configurar exportação</h2><p className="sub">Opções visuais do protótipo</p>
            <div className="field" style={{ marginTop: 16 }}><label>Título do relatório</label><div className="input"><input value={titulo} onChange={e => setTitulo(e.target.value)} /><Pencil size={16} color="var(--secundario)" /></div></div>
            <div className="field" style={{ marginTop: 16 }}><label>Escopo</label><div className="select"><span>Item selecionado</span><ChevronDown size={16} /></div></div>
            <div className="note" style={{ background: 'var(--sel)', marginTop: 16 }}><b className="t-pet">{p.nome}</b>{p.forn}<br />{p.orgao} · score {p.score}</div>
            <div className="field" style={{ marginTop: 16 }}><label>Período de referência</label><div className="select"><span>Jan–Jun 2026</span><Calendar size={16} /></div></div>
            <div className="field" style={{ marginTop: 16 }}><label>Formato</label>
              <div className="radio">{['PDF', 'CSV'].map(f => <button key={f} className={fmt === f ? 'on' : ''} onClick={() => setFmt(f)}>{fmt === f ? <CircleDot size={16} /> : <Circle size={16} />}{f}</button>)}</div></div>
            <hr style={{ border: 0, borderTop: '1px solid var(--divisoria)', margin: '20px 0' }} />
            <label style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 12 }}>O relatório inclui</label>
            {['Síntese e valores de itens', 'Sinais e comparação de itens', 'Limitações'].map(l => <p key={l} className="check-fixo"><Check size={16} color="var(--petroleo)" />{l}</p>)}
            <p className="hint" style={{ display: 'block', marginTop: 12 }}>O aviso de revisão humana é obrigatório e permanece em todas as exportações.</p>
          </div>
          <div className="dark-card"><FileCheck size={22} /><b style={{ fontSize: 16 }}>Prévia pronta para revisão</b>
            <p>1 item · {brl(p.valor)} homologados<br />{fmt} demonstrativo de 1 página.<br />A exportação não gera um arquivo real.</p></div>
        </div>
        <div className="preview">
          <div className="mini no-print"><b>Prévia do relatório</b><span className="hint"><span className="pill rev" style={{ background: 'var(--superficie)' }}>100%</span>&nbsp; Página 1 de 1</span></div>
          <div className="paper">
            <div className="mini"><div className="mono-row"><Mark size={34} /><span style={{ fontSize: 22 }}><b style={{ fontWeight: 650 }}>Licita</b> Clara</span></div>
              <small style={{ textAlign: 'right', color: 'var(--secundario)', fontSize: 11 }}>AUDITORIA E COMPLIANCE<br />30 jun 2026 · emissão simulada</small></div>
            <hr style={{ border: 0, borderTop: '2px solid var(--petroleo)', width: '100%' }} />
            <h3>Relatório de {titulo.toLowerCase()}</h3>
            <p className="sub" style={{ margin: 0 }}>Item: {p.nome} · {p.id} · Jan–Jun 2026 · 1 item selecionado</p>
            <span className="demo" style={{ alignSelf: 'flex-start' }}>Dados simulados • Protótipo acadêmico</span>
            <Sec>01 / Síntese e valores do item</Sec>
            <p>O item “{p.nome}” ({p.cat.toLowerCase()}), adquirido pelo {p.orgao}, foi priorizado para revisão humana. Fornecedor: {p.forn} Modalidade: pregão eletrônico. Situação: {p.rev.toLowerCase()}, sem conclusão de auditoria.</p>
            <div className="stats" style={{ background: 'var(--fundo)', padding: 16 }}>
              <div><small>Estimado</small><strong style={{ fontSize: 22, fontWeight: 500 }}>{brl(d.estimado)}</strong></div>
              <div><small>Homologado</small><strong style={{ fontSize: 22, fontWeight: 500 }}>{brl(p.valor)}</strong></div>
              <div><small>Score ilustrativo</small><strong className="t-alta" style={{ fontSize: 22, fontWeight: 500 }}>{p.score} / 100</strong></div>
            </div>
            <Sec>02 / Sinais e comparação de itens</Sec>
            <table className="tbl" style={{ marginTop: 0 }}><thead><tr><th>Atributo</th><th>Item</th><th>Referência</th></tr></thead>
              <tbody>{rows.map(r => <tr key={r[0]}>{r.map(c => <td key={c}>{c}</td>)}</tr>)}</tbody></table>
            <p className="hint" style={{ display: 'block' }}>Comparação de preço: 18 compras similares de “{p.nome}”. Frequência de {marca} no {p.orgao}: 18 contratos no semestre.</p>
            <Sec>03 / Limitações</Sec>
            <p className="sub" style={{ margin: 0 }}>Isolation Forest: {p.score}/100 · Autoencoder: {d.auto}/100. Comparação simulada e ilustrativa, não uma avaliação validada. Contribuição por atributo também ilustrativa; sem SHAP calculado, modelo treinado ou métricas de acurácia.</p>
            <div style={{ background: 'var(--aviso)', borderLeft: '3px solid var(--media)', padding: '12px 16px' }}>
              <b>Anomalia estatística não é prova de irregularidade. Os sinais indicam prioridade de análise e exigem revisão humana.</b>
              <p className="hint" style={{ display: 'block', marginTop: 4 }}>O score não é probabilidade de fraude. Limitações: falsos positivos, itens raros, qualidade variável de descrições e ausência de rótulos. Confirmar equivalência dos itens e documentos antes de concluir.</p></div>
            <div><b style={{ fontSize: 11 }}>Fonte e rastreabilidade</b><p className="hint" style={{ display: 'block', marginTop: 4 }}>Fonte prevista: Kaggle Brazilian Public Tenders / Licitações e Contratos, compilado do Portal da Transparência. Este relatório não usa registros reais; todos os órgãos, fornecedores e resultados são fictícios.</p></div>
            <div className="hint" style={{ borderTop: '1px solid var(--divisoria)', paddingTop: 12 }}><span>Licita Clara · FATEC Jacareí · Governança e Compliance</span><span>01 / 01</span></div>
          </div>
        </div>
      </div>
    </>
  )
}
