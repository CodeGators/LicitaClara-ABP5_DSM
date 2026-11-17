import { Info, CircleHelp } from 'lucide-react'
import { nivel, nivelNome } from '../data.js'

// O título e uma frase explicam a tela. O parâmetro `kicker` é aceito por compatibilidade, mas não é exibido.
export const Head = ({ title, sub, action }) => (
  <div className="head">
    <div><h1>{title}</h1>{sub && <p className="sub">{sub}</p>}</div>
    {action}
  </div>
)
export const Score = ({ v }) => <span className={`score t-${nivel(v)}`}>{v}</span>
export const Prioridade = ({ v }) => <span className={`pill ${nivel(v)}`}>{nivelNome[nivel(v)]}</span>
export const Revisao = ({ v }) => <span className={`pill ${v === 'Em análise' ? 'ana' : 'rev'}`}>{v}</span>
export const Aviso = ({ detalhe }) => (
  <div className="aviso">
    <Info size={18} aria-hidden="true" />
    <div>
      Anomalia estatística não é prova de irregularidade: o índice indica onde conferir primeiro e exige revisão humana.
      {detalhe && <details>
        <summary>Ver limitações</summary>
        <p>Há possíveis falsos positivos, itens raros, descrições de qualidade variável e ausência de rótulos. O índice não representa probabilidade de fraude.</p>
      </details>}
    </div>
  </div>
)
export const Progress = ({ pct, cor = 'var(--petroleo)', max = 100 }) => (
  <div className="bar"><i style={{ width: `${(pct / max) * 100}%`, background: cor }} /></div>
)
export const Tip = ({ text, children }) => (
  <span className="tip" tabIndex={0} data-tip={text}>{children}<CircleHelp size={14} /></span>
)
