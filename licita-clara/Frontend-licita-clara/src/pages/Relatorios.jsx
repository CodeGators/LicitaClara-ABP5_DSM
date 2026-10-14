import { useState } from 'react'
import { Download, Pencil, Calendar, ChevronDown, FileCheck, CircleDot, Circle } from 'lucide-react'
import { Head } from '../components/ui.jsx'
import { Mark } from '../components/Logo.jsx'

export default function Relatorios() {
  const [titulo, setTitulo] = useState('Prioridade de análise')
  const [fmt, setFmt] = useState('PDF')
  const [sec, setSec] = useState({ sintese: true, sinais: true, metodo: true, anexos: false })
  const tog = k => setSec(s => ({ ...s, [k]: !s[k] }))
  const rows = [['Preço unitário / mediana', '1,60×', 'R$ 12.000 / R$ 7.500'], ['Participantes', '2', 'Mediana: 6'], ['Participação no gasto do órgão', '42%', 'HHI do órgão: 0,31'], ['Publicação–contrato', '12 dias', 'Mediana: 28 dias']]
  const checks = [['sintese', 'Síntese e valores do processo'], ['sinais', 'Sinais e comparação de itens'], ['metodo', 'Método, fontes e limitações'], ['anexos', 'Anexos documentais']]
  const Sec = ({ children }) => <h4 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{children}</h4>
  return (
    <>
      <Head kicker="Exportação / Auditoria e compliance" title="Relatórios" sub="Defina o recorte, revise a prévia e documente os sinais com responsabilidade."
        action={<button className="btn primary no-print" onClick={() => window.print()}><Download size={16} /> Exportar {fmt}</button>} />
      <div className="grid g-rel">
        <div className="grid no-print">
          <div className="card">
            <h2>Configurar exportação</h2><p className="sub">Opções visuais do protótipo</p>
            <div className="field" style={{ marginTop: 16 }}><label>Título do relatório</label><div className="input"><input value={titulo} onChange={e => setTitulo(e.target.value)} /><Pencil size={16} color="var(--secundario)" /></div></div>
            <div className="field" style={{ marginTop: 16 }}><label>Escopo</label><div className="select"><span>Processo selecionado</span><ChevronDown size={16} /></div></div>
            <div className="note" style={{ background: 'var(--sel)', marginTop: 16, color: 'var(--secundario)' }}><b className="t-pet">LC-2026-0142</b>Nexo Suprimentos Ltda.<br />Instituto Vale Azul · score 92</div>
            <div className="field" style={{ marginTop: 16 }}><label>Período de referência</label><div className="select"><span>Jan–Jun 2026</span><Calendar size={16} /></div></div>
            <div className="field" style={{ marginTop: 16 }}><label>Formato</label>
              <div className="radio">{['PDF', 'CSV'].map(f => <button key={f} className={fmt === f ? 'on' : ''} onClick={() => setFmt(f)}>{fmt === f ? <CircleDot size={16} /> : <Circle size={16} />}{f}</button>)}</div></div>
            <hr style={{ border: 0, borderTop: '1px solid var(--divisoria)', margin: '20px 0' }} />
            <label style={{ fontSize: 12, fontWeight: 500, display: 'block', marginBottom: 12 }}>Seções incluídas</label>
            {checks.map(([k, l]) => <label key={k} className="check"><input type="checkbox" checked={sec[k]} onChange={() => tog(k)} />{l}</label>)}
            <p className="hint" style={{ display: 'block' }}>O aviso de revisão humana é obrigatório e permanece em todas as exportações.</p>
          </div>
          <div className="dark-card"><FileCheck size={22} /><b style={{ fontSize: 16 }}>Prévia pronta para revisão</b>
            <p>1 processo · R$ 480.000 homologados<br />{fmt} demonstrativo de 1 página.<br />A exportação não gera um arquivo real.</p></div>
        </div>
        <div className="preview">
          <div className="mini no-print"><b>Prévia do relatório</b><span className="hint"><span className="pill rev" style={{ background: 'var(--superficie)' }}>100%</span>&nbsp; Página 1 de 1</span></div>
          <div className="paper">
            <div className="mini"><div className="mono-row"><Mark size={34} /><span style={{ fontSize: 22 }}><b style={{ fontWeight: 650 }}>Licita</b> Clara</span></div>
              <small style={{ textAlign: 'right', color: 'var(--secundario)', fontSize: 11 }}>AUDITORIA E COMPLIANCE<br />30 jun 2026 · emissão simulada</small></div>
            <hr style={{ border: 0, borderTop: '2px solid var(--petroleo)', width: '100%' }} />
            <h3>Relatório de {titulo.toLowerCase()}</h3>
            <p className="sub" style={{ margin: 0 }}>Processo LC-2026-0142 · Jan–Jun 2026 · 1 processo selecionado</p>
            <span className="demo" style={{ alignSelf: 'flex-start' }}>Dados simulados • Protótipo acadêmico</span>
            {sec.sintese && <>
              <Sec>01 / Síntese do processo</Sec>
              <p>O processo de equipamentos de informática do Instituto Vale Azul foi priorizado para revisão humana. Fornecedor: Nexo Suprimentos Ltda. Modalidade: pregão eletrônico. Situação: a revisar, sem conclusão de auditoria.</p>
              <div className="stats" style={{ background: 'var(--fundo)', padding: 16 }}>
                <div><small>Estimado</small><strong style={{ fontSize: 22, fontWeight: 500 }}>R$ 420.000</strong></div>
                <div><small>Homologado</small><strong style={{ fontSize: 22, fontWeight: 500 }}>R$ 480.000</strong></div>
                <div><small>Score ilustrativo</small><strong className="t-alta" style={{ fontSize: 22, fontWeight: 500 }}>92 / 100</strong></div>
              </div></>}
            {sec.sinais && <>
              <Sec>02 / Sinais para verificação</Sec>
              <table className="tbl" style={{ marginTop: 0 }}><thead><tr><th>Atributo</th><th>Processo</th><th>Referência</th></tr></thead>
                <tbody>{rows.map(r => <tr key={r[0]}>{r.map(c => <td key={c}>{c}</td>)}</tr>)}</tbody></table>
              <p className="hint" style={{ display: 'block' }}>Comparação de preço: 18 compras similares de notebooks i5 / 16 GB / SSD 512 GB. Frequência da Nexo no Instituto Vale Azul: 18 contratos no semestre.</p></>}
            {sec.metodo && <>
              <Sec>03 / Método e limites de interpretação</Sec>
              <p className="sub" style={{ margin: 0 }}>Isolation Forest: 92/100 · Autoencoder: 88/100. Comparação simulada e ilustrativa, não uma avaliação validada. Contribuição por atributo também ilustrativa; sem SHAP calculado, modelo treinado ou métricas de acurácia.</p></>}
            {sec.anexos && <><Sec>04 / Anexos documentais</Sec><p className="sub" style={{ margin: 0 }}>Nenhum documento anexado neste protótipo.</p></>}
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
