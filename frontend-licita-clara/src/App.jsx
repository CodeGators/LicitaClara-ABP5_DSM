import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Painel from './pages/Painel.jsx'
import Processos from './pages/Processos.jsx'
import Detalhe from './pages/Detalhe.jsx'
import Fornecedores from './pages/Fornecedores.jsx'
import Relatorios from './pages/Relatorios.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Painel />} />
        <Route path="processos" element={<Processos />} />
        <Route path="processos/:id" element={<Detalhe />} />
        <Route path="fornecedores" element={<Fornecedores />} />
        <Route path="relatorios" element={<Relatorios />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
