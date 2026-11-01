import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { LayoutGrid, ListFilter, Building2, FileText, Layers, ScanSearch, CircleHelp, Menu, Sun, Moon } from 'lucide-react'
import Logo from './Logo.jsx'
import AjudaModal from './AjudaModal.jsx'
import useTheme from '../useTheme.js'

const nav = [
  { to: '/', label: 'Painel geral', icon: LayoutGrid, end: true },
  { to: '/processos', label: 'Processos sinalizados', icon: ListFilter },
  { to: '/fornecedores', label: 'Fornecedores', icon: Building2 },
  { to: '/relatorios', label: 'Relatórios', icon: FileText },
]
const names = { '': 'Painel geral', processos: 'Processos sinalizados', fornecedores: 'Fornecedores', relatorios: 'Relatórios' }

export default function Layout() {
  const { pathname } = useLocation()
  const parts = pathname.split('/').filter(Boolean)
  const [tema, alternar] = useTheme()
  const [menu, setMenu] = useState(false)
  const [ajuda, setAjuda] = useState(() => !localStorage.getItem('lc_ajuda_vista'))
  const fechar = () => { localStorage.setItem('lc_ajuda_vista', '1'); setAjuda(false) }

  useEffect(() => setMenu(false), [pathname])
  useEffect(() => {
    const esc = e => e.key === 'Escape' && setMenu(false)
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [])

  return (
    <div className="app">
      {ajuda && <AjudaModal onClose={fechar} />}
      {menu && <div className="scrim" onClick={() => setMenu(false)} />}
      <aside className={`side ${menu ? 'open' : ''}`}>
        <Logo />
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
          <div className="crumb">
            <button className="icon-btn menu-btn" onClick={() => setMenu(true)} aria-label="Abrir menu"><Menu size={20} /></button>
            <Layers size={18} className="hide-sm" />
            <span><span className="hide-sm">Auditoria cidadã / </span>{names[parts[0] || '']}</span>
          </div>
          <div className="chips">
            <span className="demo">Dados simulados<span className="hide-sm"> • Protótipo acadêmico</span></span>
            <button className="help-btn" onClick={() => setAjuda(true)} aria-label="Como funciona"><CircleHelp size={16} /><span className="hide-sm">Como funciona</span></button>
            <button className="help-btn" onClick={alternar} aria-label={tema === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'} title={tema === 'dark' ? 'Modo claro' : 'Modo escuro'}>
              {tema === 'dark' ? <Sun size={16} /> : <Moon size={16} />}<span className="hide-sm">{tema === 'dark' ? 'Claro' : 'Escuro'}</span>
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
