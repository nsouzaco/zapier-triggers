import { useState, useEffect } from 'react'
import { operatorApi } from './services/operatorApi'
import type {
  SystemHealth,
  EventSummary,
  Customer,
  Subscription,
} from './types'
import './App.css'

type Tab = 'overview' | 'events' | 'customers' | 'subscriptions'

function App() {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [events, setEvents] = useState<EventSummary[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  useEffect(() => {
    loadData()
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [health, eventsData, customersData, subscriptionsData] = await Promise.all([
        operatorApi.getSystemHealth(),
        operatorApi.getEvents({ limit: 50 }),
        operatorApi.getCustomers(),
        operatorApi.getSubscriptions(),
      ])

      setSystemHealth(health)
      setEvents(eventsData.events || [])
      setCustomers(customersData.customers || [])
      setSubscriptions(subscriptionsData.subscriptions || [])
    } catch (err) {
      console.error('Error loading data:', err)
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  if (loading && !systemHealth) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            Zapier Triggers API - Operator Dashboard
          </h1>
        </div>
      </header>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {(['overview', 'events', 'customers', 'subscriptions'] as Tab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-2 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-orange-500 text-orange-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            Error: {error}
          </div>
        )}

        {activeTab === 'overview' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-gray-900">System Overview</h2>
            
            {systemHealth && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Status</div>
                  <div className={`text-2xl font-bold mt-1 ${
                    systemHealth.status === 'healthy' ? 'text-green-600' : 
                    systemHealth.status === 'degraded' ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {systemHealth.status}
                  </div>
                </div>
                
                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Events Today</div>
                  <div className="text-2xl font-bold text-gray-900 mt-1">
                    {systemHealth.events_today.toLocaleString()}
                  </div>
                </div>
                
                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Success Rate</div>
                  <div className="text-2xl font-bold text-gray-900 mt-1">
                    {systemHealth.success_rate.toFixed(1)}%
                  </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Total Events</div>
                  <div className="text-2xl font-bold text-gray-900 mt-1">
                    {systemHealth.total_events.toLocaleString()}
                  </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Delivered Today</div>
                  <div className="text-2xl font-bold text-green-600 mt-1">
                    {systemHealth.events_delivered_today.toLocaleString()}
                  </div>
                </div>

                <div className="bg-white p-6 rounded-lg shadow">
                  <div className="text-sm text-gray-500">Failed Today</div>
                  <div className="text-2xl font-bold text-red-600 mt-1">
                    {systemHealth.events_failed_today.toLocaleString()}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900">All Events</h2>
              <button
                onClick={loadData}
                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600"
              >
                Refresh
              </button>
            </div>
            <div className="bg-white shadow rounded-lg overflow-hidden">
              {events.length === 0 ? (
                <div className="p-8 text-center text-gray-500">No events found</div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Event ID</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Event Type</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {events.map((event) => (
                      <tr key={event.event_id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                          {event.event_id.substring(0, 8)}...
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {event.customer_id.substring(0, 8)}...
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            event.status === 'delivered' ? 'bg-green-100 text-green-800' :
                            event.status === 'failed' ? 'bg-red-100 text-red-800' :
                            event.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {event.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {event.event_type || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(event.timestamp).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {activeTab === 'customers' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Customers ({customers.length})</h2>
              <button
                onClick={loadData}
                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600"
              >
                Refresh
              </button>
            </div>
            <div className="bg-white shadow rounded-lg overflow-hidden">
              {customers.length === 0 ? (
                <div className="p-8 text-center text-gray-500">No customers found</div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer ID</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {customers.map((customer) => (
                      <tr key={customer.customer_id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                          {customer.customer_id.substring(0, 8)}...
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {customer.name || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {customer.email || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            customer.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {customer.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {customer.created_at ? new Date(customer.created_at).toLocaleString() : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {activeTab === 'subscriptions' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Subscriptions ({subscriptions.length})</h2>
              <button
                onClick={loadData}
                className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600"
              >
                Refresh
              </button>
            </div>
            <div className="bg-white shadow rounded-lg overflow-hidden">
              {subscriptions.length === 0 ? (
                <div className="p-8 text-center text-gray-500">No subscriptions found</div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Workflow ID</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Event Selector</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Webhook URL</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {subscriptions.map((sub) => (
                      <tr key={sub.workflow_id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                          {sub.workflow_id.substring(0, 8)}...
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500">
                          {sub.customer_id.substring(0, 8)}...
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">
                          <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                            {JSON.stringify(sub.event_selector)}
                          </code>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500 truncate max-w-xs">
                          {sub.webhook_url}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            sub.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {sub.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
