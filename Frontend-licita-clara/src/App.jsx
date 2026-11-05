import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import DemoPainel from './pages/DemoPainel.jsx'
import { PainelReal, RankingReal, FornecedoresReal } from './pages/Analitico.jsx'
import { AnalysisProvider, AnalysisGate } from './AnalysisContext.jsx'
import DemoItens from './pages/DemoItens.jsx'
import Detalhe from './pages/Detalhe.jsx'
import Itens from './pages/Itens.jsx'
import ItemDetalhe from './pages/ItemDetalhe.jsx'
import Processo from './pages/Processo.jsx'
import { BaseGate, BaseProvider } from './BaseContext.jsx'
import DemoFornecedores from './pages/DemoFornecedores.jsx'
import Relatorios from './pages/Relatorios.jsx'
import DemoRelatorios from './pages/DemoRelatorios.jsx'

export default function App() {
  const location = useLocation()
  const real = /^\/(itens|processos|painel|ranking|fornecedores|relatorios)(\/|$)/.test(location.pathname)
  const analytic = /^\/(painel|ranking|fornecedores|relatorios)(\/|$)/.test(location.pathname) || new URLSearchParams(location.search).has('execucao_id')
  const legacyParams = new URLSearchParams(location.search)
  legacyParams.delete('aba')
  return (
    <BaseProvider enabled={real}><AnalysisProvider enabled={real && analytic}><Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/itens" replace />} />
        <Route path="itens" element={<BaseGate><Itens /></BaseGate>} />
        <Route path="itens/:id" element={<BaseGate><ItemDetalhe /></BaseGate>} />
        <Route path="processos" element={<Navigate to={`/itens?${legacyParams}`} replace />} />
        <Route path="processos/:id" element={<BaseGate><Processo /></BaseGate>} />
        <Route path="painel" element={<BaseGate><PainelReal /></BaseGate>} />
        <Route path="ranking" element={<BaseGate><RankingReal /></BaseGate>} />
        <Route path="demonstracao/painel" element={<DemoPainel />} />
        <Route path="demonstracao/fornecedores" element={<DemoFornecedores />} />
        <Route path="demonstracao/itens" element={<DemoItens />} />
        <Route path="demonstracao/itens/:id" element={<Detalhe />} />
        <Route path="fornecedores" element={<BaseGate><FornecedoresReal /></BaseGate>} />
        <Route path="fornecedores/:id" element={<BaseGate><FornecedoresReal /></BaseGate>} />
        <Route path="relatorios" element={<BaseGate><AnalysisGate><Relatorios /></AnalysisGate></BaseGate>} />
        <Route path="demonstracao/relatorios" element={<DemoRelatorios />} />
        <Route path="*" element={<div className="card" role="alert"><h1>Página não encontrada</h1><a className="link-a" href="/itens">Consultar itens</a></div>} />
      </Route>
    </Routes></AnalysisProvider></BaseProvider>
  )
}
