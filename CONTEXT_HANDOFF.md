# 🛡️ BlackBox RL Agent - Context Handoff Document

> **Date**: November 28, 2025  
> **Branch**: `feature/mvp`  
> **Repo**: `enturesting/blackbox-rl-agent`

---

## 📋 Executive Summary

This is an **AI-powered blackbox penetration testing tool** (BlackBox RL Agent). It uses:
- **LangGraph** for state machine orchestration
- **Google Gemini** for AI decision-making
- **Playwright** for browser automation
- **Reinforcement Learning** to improve exploit discovery

---

## 🔀 Branch Comparison & Merged Design

### Branches Compared

| Branch | Owner | Strengths |
|--------|-------|-----------|
| `feature/qa-agentnick` | Nick | Core RL agent, LangGraph state machine, SQL injection discovery |
| `feature/qa-agent-improvements` | Other | Better prompts, safety guardrails |
| `matt-ui` | Matt | React dashboard, FastAPI server, phase visualization |

### What Was Merged (into `feature/qa-agentnick`)

| Component | Source Branch | Status |
|-----------|--------------|--------|
| React Dashboard (`frontend/`) | matt-ui | ✅ Integrated |
| FastAPI Server (`server.py`) | matt-ui | ✅ Fixed & integrated |
| Phase Progress UI | matt-ui | ✅ Working |
| QA Agent (`qa_agent_v1.py`) | qa-agentnick | ✅ Original + headless fix |
| Target App (`target-apps/buggy-vibe/`) | External repo | ✅ Cloned into repo |
| Run Demo Script (`run_demo.sh`) | New | ✅ Created |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Security Testing Suite                     │
├─────────────────────────────────────────────────────────────────┤
│  Dashboard (React)              │  Target App (buggy-vibe)       │
│  http://localhost:3000          │  http://localhost:5173         │
│  - Phase progress UI            │  - Intentionally vulnerable    │
│  - Live logs                    │  - SQL injection endpoints     │
│  - Report viewer                │  - XSS vulnerabilities         │
├─────────────────────────────────┼─────────────────────────────────┤
│  API Server (FastAPI)           │  Vuln Backend                   │
│  http://localhost:8000          │  http://localhost:3001          │
│  - Pipeline orchestration       │  - /api/users/search (SQLi)    │
│  - Log streaming                │  - /api/login (SQLi)           │
│  - Stats & reports              │  - /products                   │
└─────────────────────────────────┴─────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    5-Phase Pipeline                              │
├─────────────────────────────────────────────────────────────────┤
│ 1. RECON          │ qa_agent_v1.py        │ RL-based discovery   │
│ 2. PLAN           │ exploit_planner.py    │ Attack strategy      │
│ 3. ATTACK         │ attack.py             │ Execute exploits     │
│ 4. ANALYZE        │ gemini_coderabbit*.py │ Code analysis        │
│ 5. REPORT         │ executive_report*.py  │ HTML summary         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 MVP Goals

1. ✅ **Single-command demo**: `./run_demo.sh` starts everything
2. ✅ **Dashboard UI**: Shows phase progress, logs, reports
3. ✅ **Target app included**: buggy-vibe in `target-apps/` folder
4. ✅ **SQL injection discovery**: Agent finds and exploits SQLi
5. ⏳ **Full pipeline**: Recon works, other phases need testing
6. ⏳ **Executive report**: Generator exists, needs integration

---

## 🔧 Technical Decisions

### Environment
- **Platform**: GitHub Codespaces (Ubuntu 24.04)
- **Python**: 3.12
- **Node**: 16+

### Key Configurations

| Setting | Value | Reason |
|---------|-------|--------|
| Playwright headless | `true` (env: `HEADLESS`) | No display in Codespace |
| CORS | Allow all origins | Codespace URL compatibility |
| Vite proxy | `/api/*` → `:3001` | Fix cross-origin in Codespace |
| API Base URL | Dynamic detection | Works locally & in Codespace |

### Files Modified

```
qa_agent_v1.py          - Added headless mode, TARGET_URL env var
server.py               - Complete rewrite, added pipeline endpoints
frontend/src/App.jsx    - Dynamic API_BASE, phase UI, tabs
target-apps/buggy-vibe/ - Added Vite proxy config
run_demo.sh             - New single-command launcher
README.md               - Complete rewrite with new docs
.env.example            - Added TARGET_URL
```

---

## ⚠️ Known Issues / Remaining Work

### Critical
1. **Rate limiting**: Google API key hits 10 RPM limit
   - Solution: Add more API keys in `.env`
   
2. **Pipeline phases 2-5**: Not fully tested
   - `exploit_planner.py` - needs `rl_training_data.json` ✅ exists
   - `attack.py` - needs `final_exploit_plan.json`
   - Others need testing

### Medium Priority
3. **Executive report**: May need path fixes
4. **Dashboard status**: Shows "Failed" even on success (UI bug)
5. **UI_README.md**: File reference still in editor (deleted)

### Nice to Have
6. Screenshot gallery in dashboard
7. Video recording of attacks
8. Better error messages in UI

---

## 🚀 How to Run

### Quick Start
```bash
# 1. Set API key
echo 'GOOGLE_API_KEY=your-key' > .env

# 2. Run everything
./run_demo.sh

# 3. Open http://localhost:3000
# 4. Click "Run Full Pipeline"
```

### Manual Start
```bash
# Terminal 1: Buggy-vibe backend
cd target-apps/buggy-vibe && node server-vulnerable.cjs

# Terminal 2: Buggy-vibe frontend
cd target-apps/buggy-vibe && npm run dev

# Terminal 3: API server
python server.py

# Terminal 4: Dashboard
cd frontend && npm run dev
```

### CLI Only
```bash
export TARGET_URL=http://localhost:5173
./run_all_agents.sh
```

---

## 📁 Project Structure

```
blackbox-rl-agent/
├── run_demo.sh              # 🚀 One-command launcher
├── run_all_agents.sh        # CLI pipeline runner
├── server.py                # FastAPI backend
│
├── qa_agent_v1.py           # Phase 1: RL reconnaissance
├── exploit_planner.py       # Phase 2: Attack planning
├── attack.py                # Phase 3: Exploitation
├── gemini_coderabbit_analyzer.py  # Phase 4: Analysis
├── executive_report_generator.py  # Phase 5: Reporting
│
├── frontend/                # React dashboard
│   ├── src/App.jsx         # Main UI
│   └── vite.config.js      # Port 3000
│
├── target-apps/
│   └── buggy-vibe/         # Vulnerable test app
│       ├── server-vulnerable.cjs  # SQLi backend
│       ├── src/            # React frontend
│       └── vite.config.js  # Proxy config
│
├── .env                     # API keys (create from .env.example)
├── requirements.txt         # Python deps
├── rl_training_data.json   # Generated by recon
├── qa_screenshots/         # Attack evidence
└── qa_reports/             # Generated reports
```

---

## 🔑 Environment Variables

```bash
# Required
GOOGLE_API_KEY=your-gemini-api-key

# Optional (for higher rate limits)
GOOGLE_API_KEY_2=another-key
GOOGLE_API_KEY_3=another-key
# ... up to GOOGLE_API_KEY_9

# Optional
TARGET_URL=http://localhost:5173  # Default target
HEADLESS=true                      # Playwright mode (default: true)
```

---

## ✅ Verified Working

| Component | Status | Notes |
|-----------|--------|-------|
| buggy-vibe backend | ✅ | SQL injection works |
| buggy-vibe frontend | ✅ | Proxy routing fixed |
| API server | ✅ | All endpoints work |
| Dashboard | ✅ | UI loads, shows phases |
| Recon phase | ✅ | Found 20,500 high-reward actions |
| Playwright headless | ✅ | Fixed for Codespace |
| Screenshots | ✅ | 14 captured |
| Training data | ✅ | 29MB generated |

---

## 🎪 Demo Script

For presentation:

1. Open Dashboard (port 3000)
2. Show buggy-vibe target app (port 5173)
3. Navigate to Users page, show SQL injection warning
4. Go back to Dashboard
5. Click "Run Full Pipeline"
6. Watch phases light up
7. Check Logs tab for real-time output
8. Show Report tab when complete
9. Open `qa_screenshots/` to show captured evidence

---

## 📞 Contact / Next Steps

- **Current branch**: `feature/mvp`
- **Next**: Test phases 2-5, fix dashboard status display
- **Goal**: Live demo of AI finding SQL injection automatically

## 🧭 Demo Notes (quick)

- DEMO_MODE: use the `./run_demo.sh` wrapper which sets `DEMO_MODE=true` and starts the vulnerable app, API server, and dashboard.
- Key files changed for this demo branch: `server.py`, `qa_agent_v1.py`, `frontend/src/App.jsx`, `run_demo.sh`, and `security_utils.py`.
- Before running or committing: ensure local `.env` files with real API keys are NOT committed. Use `.env.example` as the template and add real keys locally.

If you're running the demo tomorrow: start `./run_demo.sh`, open `http://localhost:3000`, then click **Run Full Pipeline**. If Codespaces disconnects when killing processes, stop services gracefully by PID instead of blanket `pkill`.

---

*Generated for context handoff on November 26, 2025*
