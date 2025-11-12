# Zapier Triggers API - Frontend Demo

A modern React frontend for testing and interacting with the Zapier Triggers API.

## Features

- 🚀 **Event Composer**: Create and submit events with JSON payload editor
- 📥 **Event Inbox**: View event history and status
- 🔑 **API Key Management**: Secure API key storage
- 📊 **Real-time Status**: See event submission status
- 🎨 **Modern UI**: Beautiful, responsive design with Tailwind CSS

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

### Configuration

Set the API URL via environment variable:

```bash
# Create .env file
echo "VITE_API_URL=https://your-api-url.execute-api.us-east-1.amazonaws.com/Prod" > .env
```

Or use the default (configured in `src/App.jsx`).

## Usage

1. **Enter API Key**: Get your API key from the backend API
2. **Compose Event**: Write your event payload in JSON format
3. **Submit**: Click "Submit Event" to send it to the API
4. **View Inbox**: Switch to "Event Inbox" tab to see all events

## Features

### Event Composer
- JSON editor with syntax highlighting
- Template events for quick testing
- Real-time validation
- Submit and view results

### Event Inbox
- List all events for your API key
- View event status (pending, delivered, failed)
- Expand to see full payload
- Refresh to get latest events

## Tech Stack

- **React 19**: Modern React with hooks
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Fetch API**: Native browser API for HTTP requests

## API Endpoints Used

- `POST /api/v1/events` - Submit events
- `GET /api/v1/inbox` - Get event history
- `GET /health` - Health check

## Development

The frontend is a standalone React application that communicates with the backend API. It can be:

1. **Developed locally** - Point to local API (`http://localhost:8000`)
2. **Deployed separately** - Deploy to any static hosting (Vercel, Netlify, S3, etc.)
3. **Integrated with backend** - Serve from FastAPI static files

## License

[To be determined]
