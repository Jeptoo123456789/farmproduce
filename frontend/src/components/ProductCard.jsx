import { Link } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import { productImage } from '../utils/productMedia'

export default function ProductCard({ product }) {
  const { addItem } = useCart()
  const available = product.status === 'AVAILABLE' && product.quantityAvailable > 0
  return <article className="product-card">
    <div className="product-image" style={{ backgroundImage: `url(${productImage(product)})` }}><span>{product.categoryName || 'Fresh produce'}</span></div>
    <div className="product-card-body"><div className="eyebrow">{product.location}</div><h3>{product.name}</h3><p>{product.description || 'Harvested with care by a local grower.'}</p><div className="product-meta"><strong>KSh {Number(product.price).toLocaleString()}</strong><span>/ {product.unit}</span></div><div className="availability"><i className={available ? 'dot available' : 'dot'} />{available ? `Available now · ${product.quantityAvailable} ${product.unit}s in stock` : 'Currently unavailable'}</div><div className="card-actions"><Link className="text-link" to={`/products/${product.id}`}>View details</Link><button className="button button-small" disabled={!available} onClick={() => addItem(product)}>Add to cart</button></div></div>
  </article>
}
