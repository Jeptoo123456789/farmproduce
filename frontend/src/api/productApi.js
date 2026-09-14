import apiClient, { unwrap } from './apiClient'

export const productApi = {
  async getProducts(params = {}) {
    const response = await apiClient.get('/products', { params })
    return { data: unwrap(response), pagination: response.data?.pagination }
  },
  async getProduct(id) { return unwrap(await apiClient.get(`/products/${id}`)) },
  async createProduct(data) { return unwrap(await apiClient.post('/products', data)) },
  async updateProduct(id, data) { return unwrap(await apiClient.patch(`/products/${id}`, data)) },
  async uploadImage(data) { return unwrap(await apiClient.post('/uploads/image', data)) },
  async deleteProduct(id) { return apiClient.delete(`/products/${id}`) },
  async adjustStock(id, amount, direction) { return unwrap(await apiClient.post(`/products/${id}/stock/${direction}`, { amount })) },
  async getFarmerProducts(id) { return unwrap(await apiClient.get(`/farmers/${id}/products`)) },
}
