# 🛡️ BlackBox RL Agent

An AI-powered **blackbox penetration testing** framework that uses LangGraph, Google Gemini, and Reinforcement Learning to automatically discover and exploit vulnerabilities in web applications.

![Demo](https://img.shields.io/badge/Demo-Ready-brightgreen) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![React](https://img.shields.io/badge/React-18-61dafb)

## ✨ Features

- **🤖 Autonomous Web Navigation**: Uses Playwright to interact with web applications like a real user
- **🔍 Intelligent Vulnerability Discovery**: AI-driven approach to finding security issues
- **💉 SQL Injection Detection**: Automatically tests for and exploits SQL injection vulnerabilities
- **📊 Real-time Dashboard**: React-based UI showing pipeline progress, logs, and reports
- **📝 Comprehensive Reporting**: Generates detailed reports with screenshots and executive summaries
- **🧠 Reinforcement Learning**: Learns from successful exploits to improve future performance
- **🎭 CEO/CTO Agent Orchestration**: Dual-agent system for vision + technical validation

## 🆕 What's New (November 2025)

### CEO/CTO Agent Orchestrator
A dual-agent coordination system that iterates toward a pitch-ready demo:
- **CEO Agent** (`@ceo`): Evaluates demo narrative, value proposition, and pitch-readiness
- **CTO Agent** (`@cto`): Validates technical implementation, fixes bugs, ensures stability
- **Shared Checklist**: `DEMO_CHECKLIST.md` for coordinated progress tracking
- **Orchestrator Script**: `orchestrator.py` automates the CEO/CTO loop with human checkpoints

### Recent Improvements
- **Loop Detection**: QA agent now detects when stuck in repetitive action loops
- **Backend Health Gate**: Orchestrator validates backend health before running QA
- **Timestamped Tests**: Generated Playwright tests include timestamps to prevent overwrites
- **Health Endpoints**: Server.py now includes `/` and `/health` endpoints

## 🚀 Quick Start (Demo)

The fastest way to see everything in action:

### 1. Set up your API key

```bash
echo 'GOOGLE_API_KEY=your-key-here' > .env
```

### 2. Run the demo

```bash
./run_demo.sh
```

This single command:
- ✅ Installs all dependencies (npm + pip)
- ✅ Starts the **buggy-vibe** vulnerable test app (ports 3001, 5173)
- ✅ Starts the **API server** (port 8000)
- ✅ Starts the **Dashboard** (port 3000)

### 3. Open the Dashboard

Navigate to **http://localhost:3000** and click **"🚀 Run Full Pipeline"**

Watch the AI:
1. Discover the application structure
2. Find vulnerable endpoints
3. Exploit SQL injection flaws
4. Extract sensitive data
5. Generate an executive report

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- Google API Key(s) for Gemini

## 🔧 Manual Setup

If you prefer manual setup over the demo script:

### 1. Clone the Repository

```bash
git clone https://github.com/enturesting/blackbox-rl-agent.git
cd blackbox-rl-agent
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Install Frontend Dependencies

```bash
cd frontend && npm install && cd ..
cd target-apps/buggy-vibe && npm install && cd ../..
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key(s):

```bash
GOOGLE_API_KEY=your-api-key-here
# For higher rate limits, add multiple keys:
GOOGLE_API_KEY_2=another-api-key
GOOGLE_API_KEY_3=yet-another-key
# ... up to GOOGLE_API_KEY_9
```

**Note**: Each API key provides ~10 requests per minute. Multiple keys increase throughput.

## 🎯 Testing with Dashboard

### Using the Web Dashboard (Recommended)

1. Start everything: `./run_demo.sh`
2. Open **http://localhost:3000**
3. Set target URL (default: `http://localhost:5173`)
4. Click **"🚀 Run Full Pipeline"** for automated scan
5. Or run individual phases:
   - **Recon** - Discover the application
   - **Plan** - Generate attack strategy
   - **Attack** - Execute exploits
   - **Analyze** - Review findings
   - **Report** - Generate executive summary

### Using the CLI

```bash
# Set target URL and run full pipeline
export TARGET_URL=http://localhost:5173
./run_all_agents.sh
```

Or run individual agents:

```bash
python qa_agent_v1.py           # Reconnaissance
python exploit_planner.py       # Attack planning
python attack.py                # Exploitation
python gemini_coderabbit_analyzer.py  # Analysis
python executive_report_generator.py  # Reporting
```

## 📁 Project Structure

```
blackbox-rl-agent/
├── run_demo.sh                 # 🚀 One-command demo launcher
├── run_all_agents.sh           # CLI pipeline runner
├── server.py                   # FastAPI backend for dashboard
├── orchestrator.py             # 🎭 CEO/CTO coordination loop
│
├── qa_agent_v1.py              # Phase 1: Reconnaissance agent
├── exploit_planner.py          # Phase 2: Attack planning
├── attack.py                   # Phase 3: Exploitation
├── gemini_coderabbit_analyzer.py # Phase 4: Analysis
├── executive_report_generator.py # Phase 5: Reporting
│
├── frontend/                   # React dashboard
│   ├── src/App.jsx            # Main UI component
│   └── package.json
│
├── target-apps/
│   └── buggy-vibe/            # Vulnerable test application
│       ├── src/               # React frontend
│       ├── server-vulnerable.cjs # Intentionally vulnerable API
│       └── pw_db.json         # Mock database
│
├── .github/agents/            # Custom GitHub Copilot agents
│   ├── ceo.md                 # CEO agent (vision/narrative)
│   ├── cto.md                 # CTO agent (technical validation)
│
├── DEMO_CHECKLIST.md          # Shared CEO/CTO coordination checklist
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (local only)
├── qa_screenshots/            # Screenshot outputs
├── qa_reports/               # Generated reports
└── rl_training_data.json     # RL training data
```

## 🔄 Pipeline Phases

| Phase | Agent | Description |
|-------|-------|-------------|
| 1. Recon | `qa_agent_v1.py` | Navigate app, discover endpoints, identify attack surfaces |
| 2. Plan | `exploit_planner.py` | Generate attack strategies based on findings |
| 3. Attack | `attack.py` | Execute planned exploits (SQL injection, XSS, etc.) |
| 4. Analyze | `gemini_coderabbit_analyzer.py` | Review and categorize vulnerabilities |
| 5. Report | `executive_report_generator.py` | Generate HTML executive summary |

## 📊 Output Files

After running the pipeline:

- `qa_screenshots/` - Screenshots of each action taken (gitignored)
- `qa_reports/` - Detailed markdown reports per phase (gitignored)
- `generated_tests/` - Timestamped Playwright tests for discovered vulnerabilities
- `executive_report_*.html` - Final executive summary
- `rl_training_data.json` - RL training data for improvement
- `qa_results.json` - JSON report of vulnerabilities found
- `orchestrator_state.json` - CEO/CTO orchestrator state (if using orchestrator)
- `orchestrator_events.json` - Live event log for frontend

## 🎭 CEO/CTO Orchestrator

For demo preparation and iteration, use the orchestrator:

### Interactive Mode (with human checkpoints)
```bash
python orchestrator.py
```

### Non-interactive Mode (fully automated)
```bash
python orchestrator.py --non-interactive --max-iterations=5
```

### Via API
```bash
curl -X POST "http://localhost:8000/api/orchestrator/start?max_iterations=5"
```

### How It Works
1. **CTO validates** environment (API keys, dependencies)
2. **CTO starts** all services (buggy-vibe, frontend, backend)
3. **CTO runs** QA agent against target app
4. **CEO evaluates** demo readiness (0-100 score)
5. **Human checkpoint** for feedback (interactive mode)
6. **Loop** until pitch-ready (score ≥ 80) or max iterations

### Custom Agents (GitHub Copilot)
Use these agents in VS Code with GitHub Copilot:
- `@ceo` - Vision, narrative, demo flow
- `@cto` - Technical validation, bug fixes

## ⚠️ Troubleshooting

### "No Google API keys found"
- Ensure `.env` file exists: `echo 'GOOGLE_API_KEY=your-key' > .env`
- Check that python-dotenv is installed: `pip install python-dotenv`

### Rate Limiting Issues
- Add more Google API keys to increase rate limit (up to 9 keys)
- The agent automatically rotates between available keys

### Port Already in Use
- The demo script automatically kills existing processes on required ports
- Manual cleanup: `lsof -ti:3000,3001,5173,8000 | xargs kill`

### Browser Issues
- Ensure Playwright is installed: `playwright install chromium`
- Check for headless mode issues: set `headless=True` in agent code

## 🔒 Security Notice

This tool is designed for **authorized security testing only**. Never use it against applications you don't own or have explicit permission to test.

Important: do NOT commit your local `.env` containing real API keys.
- Use `.env.example` as a template and keep real keys local only.
- Verify before committing: `git status --porcelain` and ensure `.env` is not listed.
- If you accidentally added `.env` to the repo, remove it from the index: `git rm --cached .env && git commit -m "chore: remove local .env from repo"`.


## 👥 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Test with the buggy-vibe application
4. Submit a pull request

## 📜 License

MIT License - See LICENSE file