import { Info, CircleHelp } from 'lucide-react'
import { nivel, nivelNome } from '../data.js'

export const Head = ({ kicker, title, sub, action }) => (
  <div className="head">
    <div><div className="kicker">{kicker}</div><h1>{title}</h1><p className="sub">{sub}</p></div>
    {action}
  </div>
)
export const Score = ({ v }) => <span className={`score t-${nivel(v)}`}>{v}</span>
export const Prioridade = ({ v }) => <span className={`pill ${nivel(v)}`}>{nivelNome[nivel(v)]}</span>
export const Revisao = ({ v }) => <span className={`pill ${v === 'Em análise' ? 'ana' : 'rev'}`}>{v}</span>
export const Aviso = ({ detalhe }) => (
  <div className="aviso">
    <Info size={18} />
    <div>
      Anomalia estatística não é prova de irregularidade. Os sinais indicam prioridade de análise e exigem revisão humana.
      {detalhe && <small>Limitações: possíveis falsos positivos, itens raros, qualidade variável de descrições e ausência de rótulos. O score não representa probabilidade de fraude.</small>}
    </div>
  </div>
)
export const Progress = ({ pct, cor = 'var(--petroleo)', max = 100 }) => (
  <div className="bar"><i style={{ width: `${(pct / max) * 100}%`, background: cor }} /></div>
)
export const Tip = ({ text, children }) => (
  <span className="tip" tabIndex={0} data-tip={text}>{children}<CircleHelp size={12} /></span>
)
