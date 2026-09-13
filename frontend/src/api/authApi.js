import apiClient, { unwrap } from './apiClient'

const path = (name, fallback) => import.meta.env[name] || fallback
const persistRegistration = (result) => {
  const token = result?.accessToken || result?.token
  const user = result?.user || result
  if (token) localStorage.setItem('farmmarket_token', token)
  localStorage.setItem('farmmarket_user', JSON.stringify(user))
  window.dispatchEvent(new CustomEvent('farmmarket:authenticated', { detail: { token, user } }))
  return result
}

export const authApi = {
  async login(data) { return unwrap(await apiClient.post(path('VITE_AUTH_LOGIN_PATH', '/auth/login'), data)) },
  async registerBuyer(data) { return persistRegistration(unwrap(await apiClient.post(path('VITE_AUTH_BUYER_REGISTER_PATH', '/auth/register/buyer'), data))) },
  async registerSeller(data) { return persistRegistration(unwrap(await apiClient.post(path('VITE_AUTH_SELLER_REGISTER_PATH', '/auth/register/seller'), data))) },
}
