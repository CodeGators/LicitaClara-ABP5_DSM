import { Link, useLocation } from 'react-router-dom'
import { money, selectionLink } from '../api.mjs'
import { itemRequiresPriceReview } from '../priceValidation.mjs'
import PriceReview from './PriceReview.jsx'

function referenceFor(item, result) {
  const score = (item.scores || []).find(s => s.resultado_item_id === result.id)
  const reference = score?.atributos?.comparacao
  return reference?.unidade_preco?.unidade_preco && Number(reference.mediana) > 0 ? reference : null
}

export default function ItemPriceTable({ rows, params }) {
  const location = useLocation()
  return <div className="table-scroll" role="region" aria-label="Preços dos itens sinalizados; use as setas para rolar na horizontal" tabIndex={0}>
    <table className="tbl tbl-stack"><thead><tr>
      <th scope="col">Item / compra</th><th scope="col">Órgão / fornecedor</th><th scope="col">Valor unitário</th><th scope="col">Total do item</th><th scope="col">Mediana histórica</th>
    </tr></thead><tbody>{rows.map(item => <tr key={item.id}>
      <td><Link className="link-a" to={selectionLink(`/ranking/${item.id}`, params)} state={{ from: location.pathname + location.search }}>{item.descricao}</Link><small>Item {item.numero_item} · Compra {item.processo.numero_compra}</small>{itemRequiresPriceReview(item) && <PriceReview />}</td>
      <td data-label="Órgão / fornecedor">{item.processo.orgao_nome}<small>{[...new Set(item.resultados.map(r => r.fornecedor_nome))].join('; ') || 'Fornecedor não informado'}</small></td>
      <td className="numeric" data-label="Valor unitário">{item.resultados.length ? item.resultados.map(result => <div className="item-price-result" key={result.id}>{money(result.valor_unitario_homologado)}{item.resultados.length > 1 && <small>{result.fornecedor_nome}</small>}</div>) : 'Não informado'}</td>
      <td className="numeric" data-label="Total do item">{money(item.valor_homologado)}{item.resultados_sem_total > 0 && <small>Total incompleto na fonte</small>}</td>
      <td className="numeric" data-label="Mediana histórica">{item.resultados.length ? item.resultados.map(result => {
        const reference = referenceFor(item, result)
        return <div className="item-price-result" key={result.id}>{reference ? <>{money(reference.mediana)}<small>por {reference.unidade_preco.unidade_preco}</small></> : 'Indisponível'}{item.resultados.length > 1 && <small>{result.fornecedor_nome}</small>}</div>
      }) : 'Indisponível'}</td>
    </tr>)}</tbody></table>
  </div>
}
