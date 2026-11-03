import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Painel from './pages/Painel.jsx'
import DemoItens from './pages/DemoItens.jsx'
import Detalhe from './pages/Detalhe.jsx'
import Itens from './pages/Itens.jsx'
import ItemDetalhe from './pages/ItemDetalhe.jsx'
import Processo from './pages/Processo.jsx'
import { BaseGate, BaseProvider } from './BaseContext.jsx'
import Fornecedores from './pages/Fornecedores.jsx'
import Relatorios from './pages/Relatorios.jsx'

export default function App() {
  const location = useLocation()
  const real = /^\/(itens|processos)(\/|$)/.test(location.pathname)
  const legacyParams = new URLSearchParams(location.search)
  legacyParams.delete('aba')
  return (
    <BaseProvider enabled={real}><Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/itens" replace />} />
        <Route path="itens" element={<BaseGate><Itens /></BaseGate>} />
        <Route path="itens/:id" element={<BaseGate><ItemDetalhe /></BaseGate>} />
        <Route path="processos" element={<Navigate to={`/itens?${legacyParams}`} replace />} />
        <Route path="processos/:id" element={<BaseGate><Processo /></BaseGate>} />
        <Route path="demonstracao/painel" element={<Painel />} />
        <Route path="demonstracao/itens" element={<DemoItens />} />
        <Route path="demonstracao/itens/:id" element={<Detalhe />} />
        <Route path="fornecedores" element={<Fornecedores />} />
        <Route path="relatorios" element={<Relatorios />} />
        <Route path="*" element={<div className="card" role="alert"><h1>Página não encontrada</h1><a className="link-a" href="/itens">Consultar itens</a></div>} />
      </Route>
    </Routes></BaseProvider>
  )
}
