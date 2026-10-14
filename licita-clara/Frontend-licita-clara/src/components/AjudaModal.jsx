import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, ShieldAlert, ArrowRight, ArrowLeft, Github, ExternalLink } from 'lucide-react'
import { grupo, githubGrupo, desenvolvedores, passos, glossario } from '../data.js'

const iniciais = n => n.split(' ').map(x => x[0]).slice(0, 2).join('')

function Avatar({ d }) {
  const [erro, setErro] = useState(false)
  return erro
    ? <span className="avatar big">{iniciais(d.nome)}</span>
    : <img className="avatar-img" src={`https://github.com/${d.user}.png?size=96`} alt="" onError={() => setErro(true)} />
}

export default function AjudaModal({ onClose }) {
  const nav = useNavigate()
  const [aba, setAba] = useState('como')
  const [i, setI] = useState(0)
  const ref = useRef(null)
  const p = passos[i]
  useEffect(() => {
    ref.current?.focus()
    const k = e => {
      if (e.key === 'Escape') onClose()
      if (aba === 'como' && e.key === 'ArrowRight') setI(v => Math.min(v + 1, passos.length - 1))
      if (aba === 'como' && e.key === 'ArrowLeft') setI(v => Math.max(v - 1, 0))
    }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose, aba])
  const ir = () => { nav(p.to); onClose() }
  const abas = [['como', 'Como funciona'], ['gloss', 'Glossário'], ['cred', 'Créditos']]
  return (
    <div className="overlay" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="ajuda-t" tabIndex={-1} ref={ref}>
        <div className="mini">
          <h2 id="ajuda-t" style={{ fontSize: 20, fontWeight: 600 }}>Bem-vindo ao Licita Clara</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Fechar"><X size={18} /></button>
        </div>
        <div className="tabs" style={{ margin: '12px 0 20px' }} role="tablist">
          {abas.map(([k, l]) => <button key={k} role="tab" aria-selected={aba === k} className={aba === k ? 'on' : ''} onClick={() => setAba(k)}>{l}</button>)}
        </div>

        {aba === 'como' && (
          <div className="modal-body">
            <p>O Licita Clara ajuda a decidir <b>por onde começar a análise</b> de compras públicas. Cada processo recebe um score de 0 a 100: quanto maior, mais urgente a revisão.</p>
            <div className="aviso" style={{ margin: '16px 0' }}><ShieldAlert size={18} /><div>O score não é prova de irregularidade. Os dados são simulados e toda conclusão exige revisão humana.</div></div>
            <div className="wizard">
              <div className="dots" aria-label={`Passo ${i + 1} de ${passos.length}`}>
                {passos.map((x, k) => <button key={x.t} className={k === i ? 'on' : k < i ? 'done' : ''} onClick={() => setI(k)} aria-label={`Ir ao passo ${k + 1}`} />)}
              </div>
              <small className="kicker" style={{ margin: '14px 0 6px', display: 'block' }}>Passo {i + 1} de {passos.length}</small>
              <h3 style={{ fontSize: 18, fontWeight: 600, margin: '0 0 6px' }}>{p.t}</h3>
              <p className="sub" style={{ margin: 0, fontSize: 13 }}>{p.d}</p>
              <button className="link-a" style={{ background: 'none', border: 0, padding: 0, marginTop: 12 }} onClick={ir}>Ir para esta tela <ExternalLink size={14} /></button>
            </div>
            <div className="mini" style={{ marginTop: 16 }}>
              <button className="btn ghost sm" disabled={i === 0} onClick={() => setI(i - 1)}><ArrowLeft size={14} /> Anterior</button>
              {i < passos.length - 1
                ? <button className="btn primary sm" onClick={() => setI(i + 1)}>Próximo <ArrowRight size={14} /></button>
                : <button className="btn primary sm" onClick={onClose}>Começar a usar</button>}
            </div>
          </div>
        )}

        {aba === 'gloss' && (
          <div className="modal-body">
            <dl className="gloss">{glossario.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl>
          </div>
        )}

        {aba === 'cred' && (
          <div className="modal-body" style={{ textAlign: 'center' }}>
            <img src="/brand/codegators.png" alt="Logo do grupo CodeGators" style={{ width: 200, maxWidth: '100%' }} />
            <h3 style={{ fontSize: 24, fontWeight: 650, margin: '0 0 4px' }}>{grupo}</h3>
            <p className="sub" style={{ marginTop: 0 }}>FATEC Jacareí · Governança e Compliance</p>
            <a className="btn outline sm" href={githubGrupo} target="_blank" rel="noopener noreferrer" style={{ marginTop: 12 }}><Github size={16} /> github.com/CodeGators</a>
            <ul className="devs">
              {desenvolvedores.map(d => (
                <li key={d.user}>
                  <a href={`https://github.com/${d.user}`} target="_blank" rel="noopener noreferrer">
                    <Avatar d={d} />
                    <span><b>{d.nome}</b><small>{d.papel}</small></span>
                    <Github size={16} color="var(--secundario)" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
