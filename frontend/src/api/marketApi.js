import apiClient, { unwrap } from './apiClient'

export const marketApi = {
  async getCategories() { return unwrap(await apiClient.get('/categories')) },
  async getBuyer(id) { return unwrap(await apiClient.get(`/buyers/${id}`)) },
  async updateBuyer(id, data) { return unwrap(await apiClient.patch(`/buyers/${id}`, data)) },
  async getFarmer(id) { return unwrap(await apiClient.get(`/farmers/${id}`)) },
  async updateFarmer(id, data) { return unwrap(await apiClient.patch(`/farmers/${id}`, data)) },
  async createBuyer(data) { return unwrap(await apiClient.post('/buyers', data)) },
  async createFarmer(data) { return unwrap(await apiClient.post('/farmers', data)) },
  async createOrder(data) { return unwrap(await apiClient.post('/orders', data)) },
  async getBuyerOrders(id) { return unwrap(await apiClient.get(`/buyers/${id}/orders`)) },
  async getFarmerOrders(id) { return unwrap(await apiClient.get(`/farmers/${id}/orders`)) },
  async updateOrderStatus(id, status) { return unwrap(await apiClient.patch(`/orders/${id}/status`, { status })) },
}
