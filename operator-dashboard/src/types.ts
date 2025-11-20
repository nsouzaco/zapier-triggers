export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  total_events: number
  events_today: number
  events_delivered_today: number
  events_failed_today: number
  success_rate: number
  queue_depth?: number | null
}

export interface EventSummary {
  event_id: string
  customer_id: string
  status: 'pending' | 'delivered' | 'failed' | 'unmatched'
  timestamp: string
  event_type?: string | null
}

export interface EventsResponse {
  events: EventSummary[]
  total: number
  has_more: boolean
}

export interface Customer {
  customer_id: string
  name: string | null
  email: string | null
  status: 'active' | 'inactive'
  created_at: string | null
}

export interface CustomersResponse {
  customers: Customer[]
  total: number
}

export interface Subscription {
  workflow_id: string
  customer_id: string
  event_selector: Record<string, unknown>
  webhook_url: string
  status: 'active' | 'disabled'
  created_at: string | null
}

export interface SubscriptionsResponse {
  subscriptions: Subscription[]
  total: number
}

export interface EventQueryParams {
  status?: string
  event_type?: string
  limit?: number
  start_time?: string
  end_time?: string
}

