import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { LayoutGrid, ListFilter, Building2, FileText, Layers, ScanSearch, CircleHelp, Menu, Sun, Moon } from 'lucide-react'
import Logo from './Logo.jsx'
import AjudaModal from './AjudaModal.jsx'
import useTheme from '../useTheme.js'
import { useBase } from '../BaseContext.jsx'
import { date } from '../api.mjs'
import { selectionLink } from '../AnalysisContext.jsx'

const nav = [
  { to: '/itens', label: 'Consultar itens', icon: ListFilter },
  { to: '/painel', label: 'Painel', icon: LayoutGrid },
  { to: '/ranking', label: 'Ranking experimental', icon: ListFilter },
  { to: '/demonstracao/painel', label: 'Painel · demonstração', icon: LayoutGrid },
  { to: '/fornecedores', label: 'Fornecedores', icon: Building2 },
  { to: '/relatorios', label: 'Relatórios', icon: FileText },
]
const names = { itens: 'Consultar itens', processos: 'Processo da compra', demonstracao: 'Demonstração', painel: 'Painel', ranking: 'Ranking experimental', fornecedores: 'Fornecedores', relatorios: 'Relatórios' }
const readSeen = () => { try { return localStorage.getItem('lc_ajuda_vista') } catch { return null } }

export default function Layout() {
  const { pathname, search } = useLocation()
  const parts = pathname.split('/').filter(Boolean)
  const base = useBase()
  const real = base.enabled
  const [tema, alternar] = useTheme()
  const [menu, setMenu] = useState(false)
  const [ajuda, setAjuda] = useState(() => !readSeen())
  const fechar = () => { try { localStorage.setItem('lc_ajuda_vista', '1') } catch {} setAjuda(false) }

  useEffect(() => { setMenu(false); window.scrollTo(0, 0) }, [pathname])
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
              <NavLink key={to} to={real && base.baseId && !to.startsWith('/demonstracao') ? selectionLink(to, search) : to} end={end} className={({ isActive }) => (isActive || (to === '/itens' && /^\/(itens|processos)(\/|$)/.test(pathname)) ? 'active' : '')}>
                <I size={18} /> {label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="recorte">
          <small>{real ? 'Base selecionada' : 'Recorte demonstrativo'}</small>
          <strong>Compras públicas</strong>
          <span style={{ fontSize: 12 }}>{real ? base.data?.base ? <>{date(base.data.base.periodo_inicio)} – {date(base.data.base.periodo_fim)}<br />{base.data.cobertura.itens} itens · {base.data.cobertura.processos} processos</> : 'Consultando disponibilidade…' : <>Jan–Jun 2026<br />Órgãos e empresas fictícios</>}</span>
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
            <span className="demo">{real ? (/^\/(painel|ranking|fornecedores)(\/|$)/.test(pathname) || (new URLSearchParams(search).get('execucao_id') && new URLSearchParams(search).get('execucao_id') !== 'nenhuma')) ? 'Dados oficiais · análise experimental' : 'Dados oficiais · análise não publicada' : 'Demonstração · dados simulados'}</span>
            <button className="help-btn" onClick={() => setAjuda(true)} aria-label="Como funciona"><CircleHelp size={16} /><span className="hide-sm">Como funciona</span></button>
            <button className="help-btn" onClick={alternar} aria-label={tema === 'dark' ? 'Ativar modo claro' : 'Ativar modo escuro'} title={tema === 'dark' ? 'Modo claro' : 'Modo escuro'}>
              {tema === 'dark' ? <Sun size={16} /> : <Moon size={16} />}<span className="hide-sm">{tema === 'dark' ? 'Claro' : 'Escuro'}</span>
            </button>
          </div>
        </header>
        <div className="content">
          {!real && <div className="note"><b>Esta tela é demonstrativa e usa dados fictícios.</b>Os números, scores e controles desta demonstração não representam a base real. <Link className="link-a" to="/itens">Consultar dados oficiais →</Link></div>}
          <Outlet />
          <div className="foot">
            <span>{real ? 'Fonte: Compras.gov.br e complemento PNCP · Cobertura limitada ao recorte importado.' : 'Demonstração acadêmica · Revisões e exportações ainda não integradas.'}</span>
            <span>Licita Clara / 2026</span>
          </div>
        </div>
      </div>
    </div>
  )
}
