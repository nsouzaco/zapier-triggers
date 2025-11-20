import type {
  SystemHealth,
  EventsResponse,
  CustomersResponse,
  SubscriptionsResponse,
  EventQueryParams,
} from '../types'

// API URL - adjust based on your deployment
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const operatorApi = {
  async getSystemHealth(): Promise<SystemHealth> {
    const response = await fetch(`${API_URL}/admin/operators/system-health`)
    if (!response.ok) throw new Error('Failed to fetch system health')
    return response.json()
  },

  async getEvents(params: EventQueryParams = {}): Promise<EventsResponse> {
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        queryParams.append(key, String(value))
      }
    })
    const response = await fetch(`${API_URL}/admin/operators/events?${queryParams}`)
    if (!response.ok) throw new Error('Failed to fetch events')
    return response.json()
  },

  async getCustomers(): Promise<CustomersResponse> {
    const response = await fetch(`${API_URL}/admin/operators/customers`)
    if (!response.ok) throw new Error('Failed to fetch customers')
    return response.json()
  },

  async getSubscriptions(): Promise<SubscriptionsResponse> {
    const response = await fetch(`${API_URL}/admin/operators/subscriptions`)
    if (!response.ok) throw new Error('Failed to fetch subscriptions')
    return response.json()
  },
}
