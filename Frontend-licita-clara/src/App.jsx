import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import { PainelReal, RankingReal, FornecedoresReal } from './pages/Analitico.jsx'
import { AnalysisProvider, AnalysisGate } from './AnalysisContext.jsx'
import DetalheAnalise from './pages/DetalheAnalise.jsx'
import Licitacoes from './pages/Licitacoes.jsx'
import Processo from './pages/Processo.jsx'
import { BaseGate, BaseProvider } from './BaseContext.jsx'
import Relatorios from './pages/Relatorios.jsx'

function LegacyItemRedirect() {
  const { pathname, search, state } = useLocation()
  return <Navigate to={pathname.replace(/^\/itens/, '/ranking') + search} state={state} replace />
}

export default function App() {
  const location = useLocation()
  const real = /^\/(itens|processos|painel|ranking|licitacoes|fornecedores|relatorios)(\/|$)/.test(location.pathname)
  const analytic = /^\/(painel|ranking|licitacoes|fornecedores|relatorios)(\/|$)/.test(location.pathname) || new URLSearchParams(location.search).has('execucao_id')
  const legacyParams = new URLSearchParams(location.search)
  legacyParams.delete('aba')
  return (
    <BaseProvider enabled={real}><AnalysisProvider enabled={real && analytic} automatic={/^\/(ranking|licitacoes|fornecedores)\/?$/.test(location.pathname)}><Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to={`/ranking${location.search}`} replace />} />
        <Route path="itens" element={<LegacyItemRedirect />} />
        <Route path="itens/:id" element={<LegacyItemRedirect />} />
        <Route path="processos" element={<Navigate to={`/ranking?${legacyParams}`} replace />} />
        <Route path="processos/:id" element={<BaseGate><Processo /></BaseGate>} />
        <Route path="painel" element={<BaseGate><PainelReal /></BaseGate>} />
        <Route path="licitacoes" element={<BaseGate><Licitacoes /></BaseGate>} />
        <Route path="licitacoes/:id" element={<BaseGate><Licitacoes /></BaseGate>} />
        <Route path="ranking/:id" element={<BaseGate><AnalysisGate><DetalheAnalise /></AnalysisGate></BaseGate>} />
        <Route path="ranking" element={<BaseGate><RankingReal /></BaseGate>} />
        <Route path="fornecedores" element={<BaseGate><FornecedoresReal /></BaseGate>} />
        <Route path="fornecedores/:id" element={<BaseGate><FornecedoresReal /></BaseGate>} />
        <Route path="relatorios" element={<BaseGate><AnalysisGate><Relatorios /></AnalysisGate></BaseGate>} />
        <Route path="*" element={<div className="card" role="alert"><h1>Página não encontrada</h1><a className="link-a" href="/ranking">Itens Sinalizados</a></div>} />
      </Route>
    </Routes></AnalysisProvider></BaseProvider>
  )
}
