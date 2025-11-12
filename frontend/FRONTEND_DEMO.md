# Frontend Demo - Quick Start Guide

## 🎨 What's This?

A beautiful, modern React frontend for testing and demonstrating the Zapier Triggers API. Perfect for:
- **Demo purposes**: Show off the API capabilities
- **Testing**: Quickly test event submission and viewing
- **Development**: Interactive way to work with the API

## 🚀 Quick Start

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## ✨ Features

### 1. **Event Composer** 📝
- JSON editor for creating event payloads
- Pre-filled templates for quick testing
- Real-time JSON validation
- One-click event submission

### 2. **Event Inbox** 📥
- View all events for your API key
- See event status (pending, delivered, failed)
- Expandable payload viewer
- Auto-refresh capability

### 3. **API Key Management** 🔑
- Secure API key storage (localStorage)
- Easy key input and clearing
- Persistent across sessions

### 4. **Modern UI** 🎨
- Beautiful gradient design
- Responsive layout
- Tailwind CSS styling
- Smooth animations

## 📋 Usage

1. **Get an API Key**
   - Use the test API key from the backend
   - Or create one via `/admin/test-customer` endpoint

2. **Enter API Key**
   - Paste your API key in the input field
   - It's saved automatically for next time

3. **Compose Event**
   - Edit the JSON payload in the editor
   - Use the template or create your own
   - Click "Submit Event"

4. **View Events**
   - Switch to "Event Inbox" tab
   - See all your events
   - Click "View Payload" to see details

## 🔧 Configuration

### API URL

The frontend connects to the API URL configured in `src/App.jsx`:

```javascript
const API_URL = import.meta.env.VITE_API_URL || 'https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/Prod'
```

To use a different API:
1. Create `.env` file in `frontend/` directory
2. Add: `VITE_API_URL=https://your-api-url.com/Prod`
3. Restart dev server

### Local Development

To connect to local API:
```bash
# In frontend/.env
VITE_API_URL=http://localhost:8000
```

## 🎯 API Endpoints Used

- `POST /api/v1/events` - Submit events
- `GET /api/v1/inbox` - Get event history
- `GET /health` - Health check (linked in UI)

## 🛠️ Tech Stack

- **React 19**: Latest React with hooks
- **Vite 7**: Fast build tool
- **Tailwind CSS 4**: Modern utility-first CSS
- **Fetch API**: Native browser HTTP client

## 📦 Build for Production

```bash
npm run build
```

Outputs to `dist/` directory. Can be deployed to:
- Vercel
- Netlify
- AWS S3 + CloudFront
- Any static hosting

## 🎨 Customization

### Colors
Edit `tailwind.config.js` to customize the color scheme.

### Layout
Modify `src/App.jsx` to change the UI layout and components.

### Features
Add new features by extending the React components.

## 🐛 Troubleshooting

### Tailwind not working?
- Make sure `postcss.config.js` exists
- Check `tailwind.config.js` content paths
- Restart dev server

### API connection errors?
- Check API URL is correct
- Verify CORS is enabled on backend
- Check API key is valid

### Events not loading?
- Verify API key is set
- Check browser console for errors
- Verify backend API is running

## 📝 Next Steps

Potential enhancements:
- [ ] Real-time event updates (WebSocket)
- [ ] Event filtering and search
- [ ] Export events to JSON/CSV
- [ ] Event replay functionality
- [ ] Subscription management UI
- [ ] Rate limit visualization
- [ ] Dark mode toggle

## 🎉 Enjoy!

The frontend is ready to use. Start the dev server and begin testing the API!

