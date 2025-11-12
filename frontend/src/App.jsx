import { useState, useEffect } from 'react'
import './App.css'

// Default API URL - can be overridden via environment variable
const API_URL = import.meta.env.VITE_API_URL || 'https://4256sf6wc3.execute-api.us-east-1.amazonaws.com/Prod'

function App() {
  const [apiKey, setApiKey] = useState(() => {
    return localStorage.getItem('zapier_api_key') || ''
  })
  const [eventPayload, setEventPayload] = useState(JSON.stringify({
    event_type: 'order.created',
    order_id: '12345',
    amount: 99.99,
    customer: {
      name: 'John Doe',
      email: 'john@example.com'
    }
  }, null, 2))
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [activeTab, setActiveTab] = useState('compose')
  const [showApiKey, setShowApiKey] = useState(false)

  // Save API key to localStorage
  useEffect(() => {
    if (apiKey) {
      localStorage.setItem('zapier_api_key', apiKey)
    }
  }, [apiKey])

  // Load events on mount and when API key changes
  useEffect(() => {
    if (apiKey) {
      loadEvents()
    }
  }, [apiKey])

  const loadEvents = async () => {
    if (!apiKey) return
    
    try {
      setLoading(true)
      setError(null)
      const response = await fetch(`${API_URL}/api/v1/inbox`, {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(`Failed to load events: ${errorData.detail || response.statusText} (${response.status})`)
      }

      const data = await response.json()
      console.log('Inbox response:', data) // Debug log
      
      // Handle both possible response formats
      const eventsList = data.events || data || []
      setEvents(Array.isArray(eventsList) ? eventsList : [])
      
      if (eventsList.length === 0) {
        console.log('No events found in response')
      }
    } catch (err) {
      console.error('Error loading events:', err)
      setError(err.message)
      setEvents([]) // Clear events on error
    } finally {
      setLoading(false)
    }
  }

  const submitEvent = async () => {
    if (!apiKey) {
      setError('Please enter your API key')
      return
    }

    let payload
    try {
      payload = JSON.parse(eventPayload)
    } catch (err) {
      setError('Invalid JSON payload: ' + err.message)
      return
    }

    try {
      setLoading(true)
      setError(null)
      setSuccess(null)

      const response = await fetch(`${API_URL}/api/v1/events`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ payload })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      setSuccess(`Event submitted successfully! Event ID: ${data.event_id}`)
      
      // Reload events after a short delay
      setTimeout(() => {
        loadEvents()
        setActiveTab('inbox')
      }, 1000)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A'
    try {
      return new Date(timestamp).toLocaleString()
    } catch {
      return timestamp
    }
  }

  return (
    <div className="min-h-screen bg-zapier-gray-50">
      {/* Top Navigation Bar - Zapier Style */}
      <nav className="bg-white border-b border-zapier-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-zapier-orange rounded flex items-center justify-center">
                <span className="text-white font-bold text-sm">Z</span>
              </div>
              <span className="text-zapier-gray-900 font-semibold text-lg">Zapier</span>
            </div>
            <div className="text-sm text-zapier-gray-600">Triggers API</div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-zapier-gray-900 mb-2">
            Event Composer
          </h1>
          <p className="text-zapier-gray-600 text-base">
            Create and manage events for your Zapier integrations
          </p>
        </div>

        {/* API Key Section - Zapier Style Card */}
        <div className="bg-white rounded-lg border border-zapier-gray-200 shadow-sm p-6 mb-6">
          <label className="block text-sm font-medium text-zapier-gray-900 mb-2">
            API Key
          </label>
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <input
                type={showApiKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your API key"
                className="w-full px-4 py-2.5 border border-zapier-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-zapier-orange focus:border-transparent text-zapier-gray-900 placeholder-zapier-gray-400 font-mono"
              />
              {apiKey && (
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-zapier-gray-500 hover:text-zapier-gray-700 text-xs px-2 py-1"
                  title={showApiKey ? "Hide API key" : "Show API key"}
                >
                  {showApiKey ? "👁️ Hide" : "👁️ Show"}
                </button>
              )}
            </div>
            {apiKey && (
              <button
                onClick={() => {
                  setApiKey('')
                  localStorage.removeItem('zapier_api_key')
                  setShowApiKey(false)
                }}
                className="px-4 py-2.5 bg-zapier-gray-100 text-zapier-gray-700 rounded-md hover:bg-zapier-gray-200 text-sm font-medium transition-colors"
              >
                Clear
              </button>
            )}
          </div>
          {!apiKey && (
            <p className="mt-3 text-sm text-zapier-gray-500">
              Don't have an API key? Create one via the API or use a test key.
            </p>
          )}
          {apiKey && (
            <p className="mt-2 text-xs text-zapier-gray-500">
              API Key: <span className="font-mono">{showApiKey ? apiKey : `${apiKey.substring(0, 8)}...${apiKey.substring(apiKey.length - 4)}`}</span>
            </p>
          )}
        </div>

        {/* Error/Success Messages - Zapier Style */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-md mb-6 text-sm">
            <strong className="font-medium">Error:</strong> {error}
          </div>
        )}
        {success && (
          <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-md mb-6 text-sm">
            <strong className="font-medium">Success:</strong> {success}
          </div>
        )}

        {/* Main Content Card */}
        <div className="bg-white rounded-lg border border-zapier-gray-200 shadow-sm mb-6">
          {/* Tabs - Zapier Style */}
          <div className="border-b border-zapier-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('compose')}
                className={`px-6 py-4 font-medium text-sm transition-colors ${
                  activeTab === 'compose'
                    ? 'border-b-2 border-zapier-orange text-zapier-orange'
                    : 'text-zapier-gray-600 hover:text-zapier-gray-900'
                }`}
              >
                Compose Event
              </button>
              <button
                onClick={() => setActiveTab('inbox')}
                className={`px-6 py-4 font-medium text-sm transition-colors ${
                  activeTab === 'inbox'
                    ? 'border-b-2 border-zapier-orange text-zapier-orange'
                    : 'text-zapier-gray-600 hover:text-zapier-gray-900'
                }`}
              >
                Event Inbox
                {events.length > 0 && (
                  <span className="ml-2 px-2 py-0.5 bg-zapier-gray-100 text-zapier-gray-700 rounded-full text-xs">
                    {events.length}
                  </span>
                )}
              </button>
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'compose' && (
              <div>
                <label className="block text-sm font-medium text-zapier-gray-900 mb-2">
                  Event Payload (JSON)
                </label>
                <textarea
                  value={eventPayload}
                  onChange={(e) => setEventPayload(e.target.value)}
                  rows={15}
                  className="w-full px-4 py-3 border border-zapier-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-zapier-orange focus:border-transparent text-zapier-gray-900 bg-white"
                  placeholder='{"event_type": "order.created", ...}'
                />
                <div className="mt-4 flex gap-3">
                  <button
                    onClick={submitEvent}
                    disabled={loading || !apiKey}
                    className="px-6 py-2.5 bg-zapier-orange text-white rounded-md hover:bg-zapier-orange-dark disabled:bg-zapier-gray-300 disabled:cursor-not-allowed font-medium text-sm transition-colors shadow-sm"
                  >
                    {loading ? 'Submitting...' : 'Submit Event'}
                  </button>
                  <button
                    onClick={() => setEventPayload(JSON.stringify({
                      event_type: 'order.created',
                      order_id: '12345',
                      amount: 99.99
                    }, null, 2))}
                    className="px-6 py-2.5 bg-white border border-zapier-gray-300 text-zapier-gray-700 rounded-md hover:bg-zapier-gray-50 font-medium text-sm transition-colors"
                  >
                    Reset Template
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'inbox' && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-lg font-semibold text-zapier-gray-900">
                    Event History
                  </h2>
                  <button
                    onClick={loadEvents}
                    disabled={loading || !apiKey}
                    className="px-4 py-2 bg-white border border-zapier-gray-300 text-zapier-gray-700 rounded-md hover:bg-zapier-gray-50 disabled:bg-zapier-gray-100 disabled:cursor-not-allowed text-sm font-medium transition-colors"
                  >
                    {loading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>

                {!apiKey ? (
                  <div className="text-center py-12 text-zapier-gray-500">
                    <p className="text-sm">Please enter your API key to view events</p>
                  </div>
                ) : loading ? (
                  <div className="text-center py-12 text-zapier-gray-500">
                    <p className="text-sm">Loading events...</p>
                  </div>
                ) : events.length === 0 ? (
                  <div className="text-center py-12 text-zapier-gray-500">
                    <p className="text-sm mb-2">No events found.</p>
                    <p className="text-xs">Submit an event to see it here, or check the browser console for errors.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {events.map((event) => (
                      <div
                        key={event.event_id}
                        className="border border-zapier-gray-200 rounded-md p-4 hover:border-zapier-gray-300 hover:shadow-sm transition-all bg-white"
                      >
                        <div className="flex justify-between items-start mb-3">
                          <div className="flex-1">
                            <div className="font-mono text-sm font-semibold text-zapier-gray-900 mb-1">
                              {event.event_id}
                            </div>
                            <div className="text-xs text-zapier-gray-500">
                              {formatTimestamp(event.timestamp)}
                            </div>
                          </div>
                          <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                            event.status === 'delivered' ? 'bg-green-100 text-green-800' :
                            event.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                            event.status === 'failed' ? 'bg-red-100 text-red-800' :
                            'bg-zapier-gray-100 text-zapier-gray-700'
                          }`}>
                            {event.status || 'unknown'}
                          </span>
                        </div>
                        <details className="mt-2">
                          <summary className="cursor-pointer text-sm text-zapier-orange hover:text-zapier-orange-dark font-medium">
                            View Payload
                          </summary>
                          <pre className="mt-3 p-3 bg-zapier-gray-50 rounded-md text-xs overflow-x-auto border border-zapier-gray-200 font-mono text-zapier-gray-800">
                            {JSON.stringify(event.payload, null, 2)}
                          </pre>
                        </details>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* API Information Card - Zapier Style */}
        <div className="bg-white rounded-lg border border-zapier-gray-200 shadow-sm p-6">
          <h2 className="text-base font-semibold text-zapier-gray-900 mb-4">API Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-zapier-gray-600 mb-1 font-medium">API URL</div>
              <div className="font-mono text-zapier-gray-900 text-xs break-all">{API_URL}</div>
            </div>
            <div>
              <div className="text-zapier-gray-600 mb-1 font-medium">Health Check</div>
              <div className="mt-1">
                <a
                  href={`${API_URL}/health`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-zapier-orange hover:text-zapier-orange-dark text-xs font-medium"
                >
                  {API_URL}/health
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
