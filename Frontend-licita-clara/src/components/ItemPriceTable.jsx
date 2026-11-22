import { Link, useLocation } from 'react-router-dom'
import { money, selectionLink } from '../api.mjs'

const signals = {
  menor_anomalia: ['Menor anomalia', 'baixa', 'green'],
  anomalia_intermediaria: ['Anomalia intermediária', 'media', 'yellow'],
  maior_anomalia: ['Maior anomalia', 'alta', 'red'],
}
const PurchaseChips = ({ item }) => <>
  {item.requer_validacao ? <span className="pill media purchase-chip">Requer validação</span>
    : signals[item.sinalizacao] && <span className={`pill ${signals[item.sinalizacao][1]} purchase-chip`}>{signals[item.sinalizacao][0]}</span>}
  {item.analise_disponivel === false && <span className="pill rev purchase-chip">Sem análise disponível</span>}
</>

const price = value => value == null ? 'Indisponível' : money(value)

export default function ItemPriceTable({ rows, params }) {
  const location = useLocation()
  const itemLink = item => selectionLink(`/ranking/${item.id}`, params)
  const origin = { from: location.pathname + location.search }
  return <div className="table-scroll" role="region" aria-label="Preços por produto e unidade na base atual; use as setas para rolar na horizontal" tabIndex={0}>
    <table className="tbl tbl-stack product-table"><thead><tr>
      <th scope="col">Item</th><th scope="col">Menor valor unitário</th><th scope="col">Maior valor unitário</th><th scope="col">Mediana da base atual</th>
    </tr></thead><tbody>{rows.map(product => {
      const band = signals[product.sinalizacao_predominante || product.sinalizacao]?.[2] || ''
      return <tr key={product.id} className={band ? `if-band-${band}` : undefined} data-if-band={band || undefined} title={band ? `Sinalização predominante: ${signals[product.sinalizacao_predominante || product.sinalizacao][0]}` : undefined}>
      <td>{band && <span className="sr-only">{signals[product.sinalizacao_predominante || product.sinalizacao]?.[0]}. </span>}{product.itens.length === 1 ? <Link className="link-a" to={itemLink(product.itens[0])} state={origin}>{product.descricao}</Link> : <details className="product-purchases"><summary>{product.descricao}</summary><ul>{product.itens.map(item => <li key={item.id}><Link className="link-a" to={itemLink(item)} state={origin}>Compra {item.numero_compra} · item {item.numero_item}</Link><PurchaseChips item={item} /></li>)}</ul></details>}
        <small>{product.catalogo} {product.codigo_catalogo} · {product.unidade_medida || 'Unidade não informada'}</small>
        <small>{product.quantidade_registros} {product.quantidade_registros === 1 ? 'registro com preço' : 'registros com preço'}</small>
        {product.itens.length === 1 && <><PurchaseChips item={product.itens[0]} /></>}
      </td>
      <td className="numeric" data-label="Menor valor unitário">{price(product.preco_minimo)}</td>
      <td className="numeric" data-label="Maior valor unitário">{price(product.preco_maximo)}</td>
      <td className="numeric" data-label="Mediana da base atual">{price(product.mediana)}</td>
    </tr>})}</tbody></table>
  </div>
}
