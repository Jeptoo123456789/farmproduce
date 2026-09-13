import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'

export default function Navbar() {
  const { user, role, logout } = useAuth(); const { count } = useCart()
  const isSeller = role?.toLowerCase() === 'seller' || role?.toLowerCase() === 'farmer'
  return <header className="site-header"><Link to="/" className="brand"><span className="brand-mark">FM</span><span>Farm<span>Market</span></span></Link><nav className="desktop-nav">{!user && <><NavLink to="/">Home</NavLink><NavLink to="/products">Market</NavLink><a href="#categories">Categories</a></>}{user && isSeller ? <><NavLink to="/seller">Dashboard</NavLink><NavLink to="/produce-list">Produce list</NavLink><NavLink to="/seller/products">My products</NavLink><NavLink to="/seller/inventory">Inventory</NavLink><NavLink to="/seller/orders">Orders</NavLink></> : user && <><NavLink to="/produce-list">Produce list</NavLink><NavLink to="/buyer/orders">My orders</NavLink><NavLink to="/buyer/profile">Profile</NavLink></>}</nav><div className="nav-actions">{user ? <><span className="user-chip">{user.name?.split(' ')[0] || 'Account'}</span><button className="button button-quiet" onClick={logout}>Log out</button></> : <><Link className="button button-quiet" to="/login">Log in</Link><Link className="button" to="/register/buyer">Join marketplace</Link></>}{!isSeller && <Link to="/cart" className="cart-link">Cart <b>{count}</b></Link>}</div></header>
}
