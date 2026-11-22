import SignalFilter from './SignalFilter.jsx'
import { Field } from './consultas.jsx'
import FilterPanel from './FilterPanel.jsx'

export default function ItemFilters({ draft, change, apply, clear, purchases = false, suppliers = false, products = false }) {
  const entity = purchases ? 'licitações' : suppliers ? 'fornecedores' : 'itens'
  const orders = products
    ? [['indice_desc', 'Maior preço unitário primeiro'], ['descricao_asc', 'Nome do item'], ['valor_desc', 'Maior mediana primeiro']]
    : [['indice_desc', 'Maior anomalia primeiro'], ['descricao_asc', purchases ? 'Objeto da licitação' : 'Nome do fornecedor'], ['valor_desc', 'Maior valor homologado']]
  return <FilterPanel title={`Filtrar ${entity}`} apply={apply} clear={clear} primary={<>
    <Field label={products ? 'Buscar item ou código de catálogo' : purchases ? 'Buscar licitação' : 'Buscar fornecedor'}><input className="input" type="search" placeholder={products ? 'Digite o nome do item ou o código de catálogo' : purchases ? 'Número ou descrição da licitação' : 'Digite o nome do fornecedor'} maxLength={200} value={draft.busca} onChange={e => change('busca', e.target.value)} /></Field>
    <SignalFilter label={purchases ? 'Sinalização da licitação' : suppliers ? 'Sinalização do fornecedor' : 'Sinalização do item'} value={draft.sinalizacao} onChange={value => change('sinalizacao', value)} />
    <Field label="Ordenação"><select className="select" value={draft.ordenacao} onChange={e => change('ordenacao', e.target.value)}>{orders.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></Field>
  </>} />
}
