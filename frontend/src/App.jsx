import { useState, useEffect } from 'react'
import './App.css'

// Demo Backend URL (Railway deployment) - can be overridden via environment variable
// The demo backend handles all communication with the production Triggers API
const DEMO_API_URL = import.meta.env.VITE_DEMO_API_URL || 'https://zapier-triggers-production.up.railway.app'

function App() {
  // Demo backend form fields
  const [documentType, setDocumentType] = useState('support_ticket')
  const [priority, setPriority] = useState('high')
  const [description, setDescription] = useState('Customer is very angry about order')
  const [customerEmail, setCustomerEmail] = useState('customer@example.com')
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [activeTab, setActiveTab] = useState('compose')

  // Load events on mount
  useEffect(() => {
    loadEvents()
  }, [])

  const loadEvents = async () => {
    try {
      setLoading(true)
      setError(null)
      // Call demo backend which proxies to production Triggers API
      const response = await fetch(`${DEMO_API_URL}/demo/inbox`, {
        headers: {
          'Content-Type': 'application/json'
        }
      })

      // Check content type before parsing
      const contentType = response.headers.get('content-type') || ''
      const isJson = contentType.includes('application/json')

      if (!response.ok) {
        // Handle error response
        let errorMessage = response.statusText
        if (isJson) {
          try {
            const errorData = await response.json()
            errorMessage = errorData.detail || errorData.message || errorMessage
          } catch {
            // JSON parse failed, use status text
          }
        } else {
          // Non-JSON error response (likely HTML error page)
          const text = await response.text()
          console.error('Non-JSON error response:', text.substring(0, 200))
          errorMessage = `Server error (${response.status}): ${response.statusText}`
        }
        throw new Error(`Failed to load events: ${errorMessage} (${response.status})`)
      }

      // Success response - parse JSON
      if (!isJson) {
        const text = await response.text()
        console.error('Non-JSON response received:', text.substring(0, 200))
        throw new Error(`Server returned ${contentType || 'unknown content type'} instead of JSON`)
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
    if (!documentType || !priority || !description || !customerEmail) {
      setError('Please fill in all fields')
      return
    }

    try {
      setLoading(true)
      setError(null)
      setSuccess(null)

      // Call demo backend /demo/trigger endpoint
      const response = await fetch(`${DEMO_API_URL}/demo/trigger`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          document_type: documentType,
          priority: priority,
          description: description,
          customer_email: customerEmail
        })
      })

      // Check content type before parsing
      const contentType = response.headers.get('content-type') || ''
      const isJson = contentType.includes('application/json')

      if (!response.ok) {
        // Handle error response
        let errorMessage = response.statusText
        if (isJson) {
          try {
            const errorData = await response.json()
            errorMessage = errorData.message || errorData.detail || errorMessage
          } catch {
            // JSON parse failed, use status text
          }
        } else {
          // Non-JSON error response
          const text = await response.text()
          console.error('Non-JSON error response:', text.substring(0, 200))
          errorMessage = `Server error (${response.status}): ${response.statusText}`
        }
        throw new Error(errorMessage)
      }

      // Success response - parse JSON
      if (!isJson) {
        const text = await response.text()
        console.error('Non-JSON response received:', text.substring(0, 200))
        throw new Error(`Server returned ${contentType || 'unknown content type'} instead of JSON`)
      }

      const data = await response.json()

      if (data.triggered) {
        setSuccess(`Event triggered successfully! ${data.message}${data.event_id ? ` Event ID: ${data.event_id}` : ''}${data.email_sent ? ' Email sent!' : ''}`)
        
        // Reload events after a short delay
        setTimeout(() => {
          loadEvents()
          setActiveTab('inbox')
        }, 1000)
      } else {
        setSuccess(`Event not triggered: ${data.reason}`)
      }
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
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-zapier-gray-900 mb-2">
                      Document Type
                    </label>
                    <input
                      type="text"
                      value={documentType}
                      onChange={(e) => setDocumentType(e.target.value)}
                      placeholder="support_ticket"
                      className="w-full px-4 py-2.5 border border-zapier-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-zapier-orange focus:border-transparent text-zapier-gray-900"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-zapier-gray-900 mb-2">
                      Priority
                    </label>
                    <select
                      value={priority}
                      onChange={(e) => setPriority(e.target.value)}
                      className="w-full px-4 py-2.5 border border-zapier-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-zapier-orange focus:border-transparent text-zapier-gray-900"
                    >
                      <option value="low">Low</option>
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-zapier-gray-900 mb-2">
                      Description
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      rows={6}
                      placeholder="Customer is very angry about order..."
                      className="w-full px-4 py-3 border border-zapier-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-zapier-orange focus:border-transparent text-zapier-gray-900 bg-white"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-zapier-gray-900 mb-2">
                      Customer Email
                    </label>
                    <input
                      type="email"
                      value={customerEmail}
                      onChange={(e) => setCustomerEmail(e.target.value)}
                      placeholder="customer@example.com"
                      className="w-full px-4 py-2.5 border border-zapier-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-zapier-orange focus:border-transparent text-zapier-gray-900"
                    />
                  </div>
                </div>
                
                <div className="mt-6 flex gap-3">
                  <button
                    onClick={submitEvent}
                    disabled={loading}
                    className="px-6 py-2.5 bg-zapier-orange text-white rounded-md hover:bg-zapier-orange-dark disabled:bg-zapier-gray-300 disabled:cursor-not-allowed font-medium text-sm transition-colors shadow-sm"
                  >
                    {loading ? 'Submitting...' : 'Trigger Demo Workflow'}
                  </button>
                  <button
                    onClick={() => {
                      setDocumentType('support_ticket')
                      setPriority('high')
                      setDescription('Customer is very angry about order')
                      setCustomerEmail('customer@example.com')
                    }}
                    className="px-6 py-2.5 bg-white border border-zapier-gray-300 text-zapier-gray-700 rounded-md hover:bg-zapier-gray-50 font-medium text-sm transition-colors"
                  >
                    Reset Form
                  </button>
                </div>
                
                <p className="mt-4 text-xs text-zapier-gray-500">
                  The demo backend will run agent logic to decide if the event should be triggered, then call the production Triggers API and send a demo email.
                </p>
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
                    disabled={loading}
                    className="px-4 py-2 bg-white border border-zapier-gray-300 text-zapier-gray-700 rounded-md hover:bg-zapier-gray-50 disabled:bg-zapier-gray-100 disabled:cursor-not-allowed text-sm font-medium transition-colors"
                  >
                    {loading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>

                {loading ? (
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
              <div className="text-zapier-gray-600 mb-1 font-medium">Demo Backend URL</div>
              <div className="font-mono text-zapier-gray-900 text-xs break-all">{DEMO_API_URL}</div>
            </div>
            <div>
              <div className="text-zapier-gray-600 mb-1 font-medium">Health Check</div>
              <div className="mt-1">
                <a
                  href={`${DEMO_API_URL}/health`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-zapier-orange hover:text-zapier-orange-dark text-xs font-medium"
                >
                  {DEMO_API_URL}/health
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
