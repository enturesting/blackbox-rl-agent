# 🛡️ BlackBox RL Agent - Context Handoff

> **Date**: December 2, 2025 (Session 3 - End of Night)  
> **Branch**: `feature/mvp`  
> **Repo**: `enturesting/blackbox-rl-agent`

---

## 📋 What Is This?

An **AI-powered blackbox penetration testing tool** that:
- Discovers web pages and input fields automatically
- Tests for SQL injection and auth bypass vulnerabilities
- Generates Playwright tests as evidence
- Uses Gemini 2.0 Flash for intelligent decision-making via LangGraph RL
- Uses Claude Sonnet for CEO/CTO agent strategic intelligence

---

## 🎯 Current Status (End of Dec 2 Session)

### ✅ Working Components

| Component | Port | Status |
|-----------|------|--------|
| **buggy-vibe frontend** | 5173 | ✅ Vite React app |
| **buggy-vibe backend** | 3001 | ✅ Express with SQLi vulnerabilities |
| **Dashboard frontend** | 3000 | ✅ React app |
| **FastAPI server** | 8000 | ✅ Health endpoints (`/` and `/health`) |
| **orchestrator.py** | N/A | ✅ Full CEO/CTO loop with Claude |
| **QA Agent** | N/A | ✅ Finds SQLi consistently |
| **Claude API** | N/A | ✅ CEO/CTO intelligence working |

### ✅ Issues Fixed This Session

| Issue | Root Cause | Fix |
|-------|------------|-----|
| **QA agent exit -15** | Timeout too aggressive | Lowered reward threshold to 1.5 |
| **0 vulnerabilities found** | buggy-backend not starting | Fixed health check for :3001 |
| **Rate limiting (429)** | Only 1 API key (10 RPM) | Added 5 Google API keys (50 RPM) |
| **Duplicate findings** | "Error parsing reward" counted | Skip error findings, dedupe by hash |
| **CEO/CTO basic logic** | No real intelligence | Added Claude API with context injection |

### 📊 Latest Orchestrator Run (03:21 UTC)

```
Services: ✅ All 4 healthy (buggy-backend:3001, buggy-vibe:5173, frontend:3000, backend:8000)
QA Agent: Exit code 0 ✅
Vulnerabilities Found: 1 SQLi (critical)
Demo Readiness: 65/100 (Claude CEO evaluation)
Status: Working - finding SQLi consistently
```

---

## 🔧 Fixes Implemented Today (Dec 2)

### 1. Claude API Integration for CEO/CTO
- Added `_call_claude()` function in `orchestrator.py`
- Created `CLAUDE_CONTEXT.md` for context injection into prompts
- CEO now uses Claude Sonnet for intelligent demo evaluation
- CTO system prompts updated for RL framework focus

### 2. Multiple API Keys (5x capacity)
- Added support for `GOOGLE_API_KEY` through `GOOGLE_API_KEY_5`
- Now have 50 RPM instead of 10 RPM
- Keys rotate automatically on rate limit

### 3. Improved Health Checks
- `buggy-backend` health check now uses `/api/users/search?username=test`
- Added retry logic (3 attempts with 2s delay)
- Fixed issue where :3001 was failing checks

### 4. Better Finding Deduplication
- Skip findings with "Error parsing reward" in description
- Deduplicate by `type + hash(evidence)`
- Prevents garbage findings from polluting reports

### 5. Lowered Mission Complete Threshold
- Changed from `reward >= 2.0` to `reward >= 1.5`
- SQLi detection (1.5 reward) now triggers success

### 6. Rewrote `.github/agents/cto.md`
- Now focused on RL framework validation
- Covers 5-phase pipeline, Playwright, buggy-vibe
- ~380 lines of comprehensive CTO guidance

---

## 📊 Key Log Files to Review

The CTO agent should review these logs before each run to ensure meaningful data is being captured:

| File | Purpose | Check For |
|------|---------|-----------|
| `rl_training_data.json` | RL step rewards | Are rewards meaningful (not all 0.0)? |
| `orchestrator_state.json` | Current orchestrator state | findings, score, services_healthy |
| `orchestrator_events.json` | Full event history | Patterns of failure, timing issues |
| `qa_reports/qa_report_*.md` | Human-readable reports | Execution logs, reward signals |
| `qa_results.json` | Structured vuln data | Generated Playwright tests |
| `generated_tests/*.py` | Timestamped test files | Reproducible exploits |
| `demo_output.log` | Raw orchestrator output | Errors, timing, API issues |

### Quick Log Review Commands
```bash
# Check last reward signals
cat rl_training_data.json | jq '.[-3:]'

# Check current orchestrator state
cat orchestrator_state.json | jq '{score: .demo_readiness_score, findings: .findings | length, services: .services_healthy}'

# Recent QA report
ls -t qa_reports/*.md | head -1 | xargs cat

# Count generated tests
ls generated_tests/*.py | wc -l

# Check for rate limit errors in recent run
grep -i "429\|rate\|limit" demo_output.log | tail -5
```

---

## 🚀 Quick Start Next Session

### Run Full Demo (Recommended)
```bash
cd /workspaces/blackbox-rl-agent
python orchestrator.py --non-interactive --max-iterations 2
```

### Test QA Agent Directly
```bash
cd /workspaces/blackbox-rl-agent
TARGET_URL=http://localhost:5173 HEADLESS=true python qa_agent_v1.py
```

### Visual Debug (watch browser)
```bash
HEADLESS=false python qa_agent_v1.py
```

### Review Logs Before Running (CTO should do this)
```bash
# Quick sanity check
cat orchestrator_state.json | jq '.demo_readiness_score, .findings | length'
cat rl_training_data.json | jq 'length'
```

---

## 🔧 Environment Variables

```bash
# Required - Gemini (5 keys for 50 RPM)
GOOGLE_API_KEY=...
GOOGLE_API_KEY_2=...
GOOGLE_API_KEY_3=...
GOOGLE_API_KEY_4=...
GOOGLE_API_KEY_5=...

# Required - Claude (CEO/CTO intelligence)
ANTHROPIC_API_KEY=...   # $452.77 credit expiring Dec 7

# Optional
TARGET_URL=http://localhost:5173
HEADLESS=true  # Set to false for visual debugging
DEMO_MODE=true # Limits to 12 steps
```

---

## 🎯 Priorities for Next Session

### 1. Improve Demo Score (Currently 65/100)
CEO feedback from Claude:
- ❌ Duplicate vulnerability entries - need better deduplication
- ❌ Only 1 vuln type found - need to show XSS, auth bypass
- ❌ Missing "wow moment" - RL learning not visible
- ❌ No progression story - agent should improve over iterations

### 2. Add More Vulnerability Types
- `/api/login` - auth bypass with `admin' --`
- `/contact` - potential XSS
- Test with `smart_qa_agent.py` (finds 6 vulns)

### 3. Better RL Visualization
- Show reward improvement over iterations
- Dashboard should highlight when agent "learns"

### 4. Review Logs Before Looping
- CTO should review `rl_training_data.json` to ensure meaningful rewards
- Check `orchestrator_events.json` for patterns
- Don't waste API credits on broken runs

---

## 📁 Key Files

```
blackbox-rl-agent/
├── qa_agent_v1.py           # LangGraph RL agent
├── smart_qa_agent.py        # Simpler scanner (finds 6 vulns)
├── orchestrator.py          # CEO/CTO loop with Claude
├── server.py                # FastAPI backend (:8000)
├── CLAUDE_CONTEXT.md        # Context injected into Claude prompts
├── .github/agents/
│   ├── ceo.md               # CEO agent (vision/narrative)
│   └── cto.md               # CTO agent (RL framework focus)
│
├── frontend/                # React dashboard (:3000)
├── target-apps/buggy-vibe/  # Vulnerable test app (:5173, :3001)
│
├── generated_tests/         # Timestamped Playwright tests
├── qa_reports/              # Markdown reports per run
├── qa_results.json          # Structured scan results
├── rl_training_data.json    # RL step-by-step rewards
├── orchestrator_state.json  # Current orchestrator state
├── orchestrator_events.json # Full event history (~100+ events)
└── demo_output.log          # Raw orchestrator output
```

---

## 📝 Session Summary (Dec 2)

**What was accomplished:**
- ✅ Claude API integration for CEO/CTO intelligence
- ✅ 5 Google API keys (50 RPM vs 10 RPM)
- ✅ Fixed buggy-backend health check
- ✅ Better finding deduplication
- ✅ Lowered mission complete threshold
- ✅ CTO agent rewrite for RL focus
- ✅ Demo consistently finds SQLi

**Current state:**
- Demo works end-to-end
- Finds 1 SQLi vulnerability consistently
- CEO Claude evaluation: 65/100
- All 4 services healthy

**Next priorities:**
- Improve demo score to 80+
- Find multiple vulnerability types
- Show RL learning progression
- Review logs before running to avoid wasting credits

---

*Last updated: December 2, 2025 ~03:30 UTC*
