import { createContext, useContext, useEffect, useState } from 'react'
import { authApi } from '../api/authApi'

const AuthContext = createContext(null)
const read = (key) => { try { return JSON.parse(localStorage.getItem(key)) } catch { return null } }

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => read('farmmarket_user'))
  const [token, setToken] = useState(() => localStorage.getItem('farmmarket_token'))

  useEffect(() => {
    const signOut = () => { setUser(null); setToken(null) }
    const signIn = (event) => { setUser(event.detail.user); setToken(event.detail.token) }
    window.addEventListener('farmmarket:unauthorized', signOut)
    window.addEventListener('farmmarket:authenticated', signIn)
    return () => { window.removeEventListener('farmmarket:unauthorized', signOut); window.removeEventListener('farmmarket:authenticated', signIn) }
  }, [])

  const login = async (credentials) => {
    const result = await authApi.login(credentials)
    return authenticate(result)
  }

  const authenticate = (result) => {
    const nextToken = result?.accessToken || result?.token
    const nextUser = result?.user || result
    if (nextToken) { localStorage.setItem('farmmarket_token', nextToken); setToken(nextToken) }
    localStorage.setItem('farmmarket_user', JSON.stringify(nextUser))
    setUser(nextUser)
    return nextUser
  }

  const register = async (details, role) => {
    const result = role === 'seller' ? await authApi.registerSeller(details) : await authApi.registerBuyer(details)
    return authenticate(result)
  }

  const logout = () => { localStorage.removeItem('farmmarket_token'); localStorage.removeItem('farmmarket_user'); setToken(null); setUser(null) }
  const value = { user, token, isAuthenticated: Boolean(user), role: user?.role || user?.userType, login, register, logout }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
