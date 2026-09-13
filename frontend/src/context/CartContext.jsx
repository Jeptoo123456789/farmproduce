import { createContext, useContext, useMemo, useState } from 'react'

const CartContext = createContext(null)

export function CartProvider({ children }) {
  const [items, setItems] = useState(() => JSON.parse(localStorage.getItem('farmmarket_cart') || '[]'))
  const persist = (next) => { setItems(next); localStorage.setItem('farmmarket_cart', JSON.stringify(next)) }
  const addItem = (product, quantity = 1) => {
    const existing = items.find((item) => item.id === product.id)
    const nextQuantity = Math.min((existing?.quantity || 0) + quantity, product.quantityAvailable)
    persist(existing ? items.map((item) => item.id === product.id ? { ...item, quantity: nextQuantity, product } : item) : [...items, { product, quantity: nextQuantity }])
  }
  const updateQuantity = (id, quantity) => persist(items.map((item) => item.id === id ? { ...item, quantity: Math.max(1, Math.min(quantity, item.product.quantityAvailable)) } : item))
  const removeItem = (id) => persist(items.filter((item) => item.id !== id))
  const subtotal = useMemo(() => items.reduce((sum, item) => sum + item.product.price * item.quantity, 0), [items])
  return <CartContext.Provider value={{ items, addItem, updateQuantity, removeItem, subtotal, count: items.reduce((sum, item) => sum + item.quantity, 0) }}>{children}</CartContext.Provider>
}

export const useCart = () => useContext(CartContext)
