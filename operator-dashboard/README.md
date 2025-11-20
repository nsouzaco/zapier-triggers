# Operator Dashboard

Operator dashboard for monitoring the Zapier Triggers API.

## Features

- **System Overview**: Real-time system health metrics
- **Events View**: View all events across all customers
- **Customer Management**: List and view all customers
- **Subscription Management**: View all subscriptions and their status

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

```bash
cd operator-dashboard
npm install
```

### Run Development Server

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173/operator/`

### Build

```bash
npm run build
```

## Configuration

Set the API URL via environment variable:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

Or create a `.env` file:

```
VITE_API_URL=http://localhost:8000
```

## Deployment

The dashboard is configured to deploy to Vercel at the `/operator` path.

### Vercel Configuration

The `vercel.json` file configures:
- Build command: `cd operator-dashboard && npm install && npm run build`
- Output directory: `operator-dashboard/dist`
- Rewrites: All `/operator/*` requests to `/operator/index.html`

## API Endpoints

The dashboard consumes these operator endpoints (no authentication required):

- `GET /admin/operators/system-health` - System health metrics
- `GET /admin/operators/events` - All events across all customers
- `GET /admin/operators/customers` - List of all customers
- `GET /admin/operators/subscriptions` - List of all subscriptions

## Auto-refresh

The dashboard automatically refreshes data every 30 seconds.

