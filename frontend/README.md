# 🖥️ BlackBox RL Agent - Dashboard Frontend

A React-based dashboard UI for the BlackBox AI penetration testing framework.

## Overview

This is the **control center** for the BlackBox RL Agent - an AI-powered blackbox penetration testing tool. The dashboard provides:

- **Real-time Pipeline Monitoring**: Watch the AI agent discover and exploit vulnerabilities
- **Phase Control**: Run individual phases or the full pipeline
- **Live Logs**: Stream agent output as it navigates and tests
- **Vulnerability Reports**: View discovered vulnerabilities with severity ratings
- **Executive Summaries**: Generate HTML reports for stakeholders

## Features

| Feature | Description |
|---------|-------------|
| 🚀 **Run Full Pipeline** | One-click to run all 5 phases |
| 📊 **Phase Status** | Visual indicators for Recon → Plan → Attack → Analyze → Report |
| 📝 **Live Logs** | Real-time streaming of agent activity |
| 🔍 **Vulnerability Cards** | Color-coded by severity (Critical, High, Medium, Low) |
| 📋 **Reports** | View and download executive summaries |
| ⚙️ **Target Config** | Set target URL for scanning |

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool with HMR
- **CSS** - Custom styling (no framework dependency)
- **Fetch API** - Communication with FastAPI backend

## Quick Start

### Development Mode

```bash
# From project root
cd frontend
npm install
npm run dev
```

Dashboard will be available at **http://localhost:3000**

### With Full Stack (Recommended)

From the project root, use the demo script which starts everything:

```bash
./run_demo.sh
```

This starts:
- Dashboard frontend (port 3000)
- FastAPI backend (port 8000)
- buggy-vibe test app (ports 5173, 3001)

## Connecting to Backend

The dashboard communicates with the FastAPI backend at `http://localhost:8000`:

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Health check |
| `GET /health` | Detailed health status |
| `POST /api/run/full-pipeline` | Run all phases |
| `POST /api/run/{phase}` | Run specific phase |
| `GET /api/events` | SSE stream for live logs |
| `GET /api/report` | Get executive report |

## Project Structure

```
frontend/
├── src/
│   ├── App.jsx          # Main dashboard component
│   ├── App.css          # Dashboard styles
│   ├── main.jsx         # React entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── index.html           # HTML template
├── package.json         # Dependencies
└── vite.config.js       # Vite configuration
```

## Environment Variables

The frontend uses Vite's environment variable system:

```bash
# .env.local (create if needed)
VITE_API_URL=http://localhost:8000
```

## Customization

### Changing the API URL

Edit `src/App.jsx` and update the `API_BASE_URL` constant:

```javascript
const API_BASE_URL = 'http://localhost:8000';
```

### Adding New Phases

1. Add phase button in the UI
2. Create API endpoint in `server.py`
3. Add event handling for new phase logs

## Related Components

- **FastAPI Backend** (`server.py`) - API server powering the dashboard
- **QA Agent** (`qa_agent_v1.py`) - The AI agent that finds vulnerabilities
- **buggy-vibe** (`target-apps/buggy-vibe/`) - Vulnerable test application

## Troubleshooting

### Dashboard won't connect to backend

```bash
# Check if backend is running
curl http://localhost:8000/health

# If not, start it
python server.py
```

### Port 3000 already in use

```bash
# Kill existing process
lsof -ti:3000 | xargs kill

# Or use different port
npm run dev -- --port 3001
```

### Blank page / React errors

```bash
# Clear cache and reinstall
rm -rf node_modules
npm install
npm run dev
```

---

Part of the [BlackBox RL Agent](https://github.com/enturesting/blackbox-rl-agent) project.
