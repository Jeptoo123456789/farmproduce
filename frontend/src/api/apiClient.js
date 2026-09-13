import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('farmmarket_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('farmmarket_token')
      localStorage.removeItem('farmmarket_user')
      window.dispatchEvent(new Event('farmmarket:unauthorized'))
    }
    return Promise.reject(error)
  },
)

export function unwrap(response) {
  return response.data?.data ?? response.data
}

export function apiError(error) {
  if (!error.response) return 'The marketplace server is unavailable. Start the FastAPI backend and try again.'
  return error.response?.data?.message || error.response?.data?.detail || 'Something went wrong. Please try again.'
}

export default apiClient
