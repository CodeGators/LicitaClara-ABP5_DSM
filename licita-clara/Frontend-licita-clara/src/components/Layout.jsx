import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { LayoutGrid, ListFilter, Building2, FileText, Layers, ScanSearch, CircleHelp, Menu, X, Sun, Moon } from 'lucide-react'
import Logo from './Logo.jsx'
import AjudaModal from './AjudaModal.jsx'

const nav = [
  { to: '/', label: 'Painel geral', icon: LayoutGrid, end: true },
  { to: '/processos', label: 'Processos sinalizados', icon: ListFilter },
  { to: '/fornecedores', label: 'Fornecedores', icon: Building2 },
  { to: '/relatorios', label: 'Relatórios', icon: FileText },
]
const names = { '': 'Painel geral', processos: 'Processos sinalizados', fornecedores: 'Fornecedores', relatorios: 'Relatórios' }

const lerLS = k => { try { return localStorage.getItem(k) } catch { return null } }
const gravarLS = (k, v) => { try { localStorage.setItem(k, v) } catch { /* modo privado */ } }

function useTema() {
  const [tema, setTema] = useState(() => document.documentElement.getAttribute('data-theme') || 'light')
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', tema)
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', tema === 'dark' ? '#0A1824' : '#102D46')
  }, [tema])
  const alternar = () => setTema(t => { const n = t === 'dark' ? 'light' : 'dark'; gravarLS('lc_tema', n); return n })
  return [tema, alternar]
}

export default function Layout() {
  const { pathname } = useLocation()
  const parts = pathname.split('/').filter(Boolean)
  const [ajuda, setAjuda] = useState(() => !lerLS('lc_ajuda_vista'))
  const [menu, setMenu] = useState(false)
  const [tema, alternarTema] = useTema()
  const fechar = () => { gravarLS('lc_ajuda_vista', '1'); setAjuda(false) }

  useEffect(() => { setMenu(false) }, [pathname])
  useEffect(() => {
    if (!menu) return
    const k = e => e.key === 'Escape' && setMenu(false)
    window.addEventListener('keydown', k)
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', k); document.body.style.overflow = '' }
  }, [menu])

  return (
    <div className="app">
      {ajuda && <AjudaModal onClose={fechar} />}
      <div className={`scrim${menu ? ' show' : ''}`} onClick={() => setMenu(false)} aria-hidden="true" />
      <aside className={`side${menu ? ' open' : ''}`} id="menu-lateral">
        <div className="side-head">
          <Logo />
          <button className="side-close" onClick={() => setMenu(false)} aria-label="Fechar menu"><X size={18} /></button>
        </div>
        <div>
          <div className="eyebrow">Espaço de análise</div>
          <nav className="nav">
            {nav.map(({ to, label, icon: I, end }) => (
              <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive || (to === '/processos' && parts[0] === 'processos') ? 'active' : '')}>
                <I size={18} /> {label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="recorte">
          <small>Recorte demonstrativo</small>
          <strong>Compras públicas</strong>
          <span style={{ fontSize: 12 }}>Jan–Jun 2026<br />Órgãos e empresas fictícios</span>
        </div>
        <div className="side-foot">
          <span style={{ display: 'flex', gap: 8, alignItems: 'center' }}><ScanSearch size={16} /> Auditoria cidadã e compliance</span>
          <hr />
          <span>FATEC Jacareí<br />Governança e Compliance</span>
          <span style={{ textTransform: 'uppercase' }}>Protótipo acadêmico · v0.1</span>
        </div>
      </aside>
      <div className="main">
        <header className="top">
          <button className="menu-btn" onClick={() => setMenu(true)} aria-label="Abrir menu" aria-controls="menu-lateral" aria-expanded={menu}><Menu size={18} /></button>
          <div className="crumb"><Layers size={18} /> Auditoria cidadã / {names[parts[0] || '']}</div>
          <div className="chips">
            <button className="help-btn" onClick={() => setAjuda(true)} aria-label="Como funciona"><CircleHelp size={16} /> <span>Como funciona</span></button>
            <span className="demo">Dados simulados • Protótipo acadêmico</span>
            <button className="theme-btn" onClick={alternarTema} aria-label={tema === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'} title={tema === 'dark' ? 'Tema claro' : 'Tema escuro'}>
              {tema === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>
        <div className="content">
          <Outlet />
          <div className="foot">
            <span>Ambiente demonstrativo · Controles e exportações são representações visuais, sem integração de dados.</span>
            <span>Licita Clara / 2026</span>
          </div>
        </div>
      </div>
    </div>
  )
}
