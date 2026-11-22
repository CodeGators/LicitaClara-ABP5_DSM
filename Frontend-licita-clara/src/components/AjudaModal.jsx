import { useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { X, ShieldAlert, Github } from 'lucide-react'
import useDialogFocus from '../useDialogFocus.js'
import { selectionLink } from '../api.mjs'
import { Mark } from './Logo.jsx'
import { grupo, githubGrupo, desenvolvedores, passos, glossario } from '../data.js'

const iniciais = n => n.split(' ').map(x => x[0]).slice(0, 2).join('')
const abas = [['como', 'Como usar'], ['gloss', 'Glossário'], ['cred', 'Créditos']]

function Avatar({ d }) {
  const [erro, setErro] = useState(false)
  return erro
    ? <span className="avatar big">{iniciais(d.nome)}</span>
    : <img className="avatar-img" src={`https://github.com/${d.user}.png?size=96`} alt="" onError={() => setErro(true)} />
}

export default function AjudaModal({ onClose, fallbackRef }) {
  const nav = useNavigate()
  const location = useLocation()
  const [aba, setAba] = useState('como')
  const ref = useRef(null)
  useDialogFocus(ref, true, onClose, fallbackRef)
  const ir = to => { nav(new URLSearchParams(location.search).has('base_id') ? selectionLink(to, location.search) : to); onClose() }
  const teclas = (e, k) => {
    const index = abas.findIndex(([key]) => key === k)
    const next = e.key === 'ArrowRight' ? (index + 1) % abas.length : e.key === 'ArrowLeft' ? (index + abas.length - 1) % abas.length : e.key === 'Home' ? 0 : e.key === 'End' ? abas.length - 1 : -1
    if (next < 0) return
    e.preventDefault(); setAba(abas[next][0]); document.getElementById(`ajuda-tab-${abas[next][0]}`)?.focus()
  }
  return (
    <div className="overlay" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className="modal welcome" role="dialog" aria-modal="true" aria-labelledby="ajuda-t" tabIndex={-1} ref={ref}>
        <div className="welcome-head">
          <div className="title"><Mark size={44} bracket="var(--azul)" bars="#617587" /><h2 id="ajuda-t">Bem-vindo ao Licita Clara</h2></div>
          <button className="icon-btn" onClick={onClose} aria-label="Fechar"><X size={20} /></button>
        </div>
        <p className="lead">Mostramos quando o preço de um dispositivo ou componente eletrônico comprado por um órgão público foge do padrão de itens parecidos. Qualquer pessoa pode consultar, sem login.</p>
        <div className="tabs" role="tablist" aria-label="Seções da ajuda">
          {abas.map(([k, l]) => <button key={k} id={`ajuda-tab-${k}`} role="tab" aria-controls={`ajuda-panel-${k}`} tabIndex={aba === k ? 0 : -1} onKeyDown={e => teclas(e, k)} aria-selected={aba === k} className={aba === k ? 'on' : ''} onClick={() => setAba(k)}>{l}</button>)}
        </div>

        <div id="ajuda-panel-como" role="tabpanel" aria-labelledby="ajuda-tab-como" hidden={aba !== 'como'} tabIndex={0}>
          {aba === 'como' && <div className="modal-body">
            <ol className="how-list">
              {passos.map((p, i) => <li className="how-step" key={p.t}>
                <span className="n" aria-hidden="true">{i + 1}</span>
                <div><h3>{p.t}</h3><p>{p.d}</p></div>
                <button className="link-a" onClick={() => ir(p.to)}>{p.cta}</button>
              </li>)}
            </ol>
            <div className="callout"><ShieldAlert size={20} aria-hidden="true" /><div><b>Anomalia não é prova de irregularidade.</b> O índice só indica onde vale conferir primeiro. A conclusão depende de revisão humana dos documentos.</div></div>
            <div className="welcome-foot">
              <small>Para rever este guia, use “Como funciona” no topo da página.</small>
              <button className="btn primary" onClick={onClose}>Começar a explorar</button>
            </div>
          </div>}
        </div>

        <div id="ajuda-panel-gloss" role="tabpanel" aria-labelledby="ajuda-tab-gloss" hidden={aba !== 'gloss'} tabIndex={0}>
          {aba === 'gloss' && <div className="modal-body"><dl className="gloss">{glossario.map(([t, d]) => <div key={t}><dt>{t}</dt><dd>{d}</dd></div>)}</dl></div>}
        </div>

        <div id="ajuda-panel-cred" role="tabpanel" aria-labelledby="ajuda-tab-cred" hidden={aba !== 'cred'} tabIndex={0}>
          {aba === 'cred' && <div className="modal-body" style={{ textAlign: 'center' }}>
            <img src="/brand/codegators.png" alt="Logo do grupo CodeGators" style={{ width: 180, maxWidth: '100%' }} />
            <h3 style={{ fontSize: '1.5rem', fontWeight: 650, margin: '0 0 .25rem' }}>{grupo}</h3>
            <p className="sub" style={{ marginTop: 0, marginInline: 'auto' }}>FATEC Jacareí · Governança e Compliance</p>
            <a className="btn outline sm" href={githubGrupo} target="_blank" rel="noopener noreferrer" style={{ marginTop: '.75rem' }}><Github size={16} /> github.com/CodeGators</a>
            <ul className="devs">
              {desenvolvedores.map(d => <li key={d.user}>
                <a href={`https://github.com/${d.user}`} target="_blank" rel="noopener noreferrer">
                  <Avatar d={d} />
                  <span><b>{d.nome}</b><small>{d.papel}</small></span>
                  <Github size={16} color="var(--secundario)" />
                </a>
              </li>)}
            </ul>
          </div>}
        </div>
      </div>
    </div>
  )
}
