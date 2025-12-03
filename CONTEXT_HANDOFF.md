# 🛡️ BlackBox RL Agent - Context Handoff

> **Date**: December 3, 2025 (Session 4 - End of Night)  
> **Branch**: `feature/mvp`  
> **Repo**: `enturesting/blackbox-rl-agent`

---

## 📋 What Is This?

An **AI-powered blackbox penetration testing tool** that:
- Discovers web pages and input fields automatically
- Tests for SQL injection, auth bypass, and other vulnerabilities
- Uses **hybrid API + browser testing** for fast, comprehensive coverage
- Generates Playwright tests as evidence
- Uses Gemini 2.0 Flash for intelligent decision-making via LangGraph RL
- Uses Claude Sonnet for CEO/CTO agent strategic intelligence

---

## 🎯 Current Status (End of Dec 3 Session)

### ✅ Working Components

| Component | Port | Status |
|-----------|------|--------|
| **buggy-vibe frontend** | 5173 | ✅ Vite React app |
| **buggy-vibe backend** | 3001 | ✅ Express with SQLi vulnerabilities |
| **Dashboard frontend** | 3000 | ✅ React app |
| **FastAPI server** | 8000 | ✅ Health endpoints (`/` and `/health`) |
| **agent_orchestrator.py** | N/A | ✅ Full CEO/CTO loop with Claude |
| **QA Agent (Hybrid)** | N/A | ✅ **Now finds 6+ vulnerabilities** via API + browser |
| **Claude API** | N/A | ✅ CEO/CTO intelligence working |

### ✅ Issues Fixed This Session (Dec 3)

| Issue | Root Cause | Fix |
|-------|------------|-----|
| **Only finding 2 vulns** | Browser tests unreliable | Added **hybrid API testing** - direct HTTP tests first |
| **Orchestrator name confusion** | Old name `orchestrator.py` | Renamed to `agent_orchestrator.py` |
| **DEMO_MODE hardcoded** | Was always `true` in orchestrator | Removed hardcoding, uses env var |
| **Missing vulnerabilities** | Limited test coverage | Expanded to 6 tests: SQLi, auth bypass, UNION, cleartext passwords, API keys, XSS |
| **Findings lost on crash** | Saved only at end | Added **crash protection** - saves API findings immediately |

### 📊 Latest API Test Results

```
🔍 [API Test 1/6] SQL Injection on /api/users/search - ✅ Got 6 users (database dump)
🔍 [API Test 2/6] Cleartext Passwords - ✅ Found 6 unhashed passwords
🔍 [API Test 3/6] API Key Exposure - ✅ Found 2 API keys exposed
🔍 [API Test 4/6] Session Token Exposure - ✅ Found 1 active session token
🔍 [API Test 5/6] Auth Bypass on /api/login - ✅ Authentication bypassed
🔍 [API Test 6/6] Stored XSS on /contacts - ✅ XSS payload stored unescaped

Total: 6+ vulnerabilities found via direct API tests (no LLM calls needed!)
```

---

## 🔧 Fixes Implemented Today (Dec 3)

### 1. Hybrid API + Browser Testing Architecture
- Added `run_direct_api_tests()` function in `qa_agent_v1.py`
- **Phase 0**: Direct HTTP tests against API endpoints (fast, reliable)
- **Phase 1**: Browser-based tests for UI-specific vulnerabilities
- Uses `aiohttp` for async HTTP client (added to requirements.txt)

### 2. Expanded Vulnerability Coverage (6 tests)
| Test | Vulnerability | CWE |
|------|--------------|-----|
| SQLi User Search | Database dump via SQL injection | CWE-89 |
| Cleartext Passwords | Unhashed passwords in database | CWE-256 |
| API Key Exposure | API keys leaked via SQLi | CWE-200 |
| Session Token Exposure | Active sessions leaked | CWE-200 |
| UNION SELECT | Schema disclosure attack | CWE-89 |
| Auth Bypass | Login bypass via SQLi | CWE-287 |
| Stored XSS | Contact form accepts scripts | CWE-79 |

### 3. Renamed Orchestrator
- `orchestrator.py` → `agent_orchestrator.py`
- Better reflects purpose as multi-agent coordinator
- Updated all references in documentation

### 4. Removed DEMO_MODE Hardcoding
- Orchestrator no longer forces `DEMO_MODE=true`
- Now respects environment variable setting
- Allows full exploration when needed

### 5. Crash Protection
- API findings saved immediately after tests complete
- Browser crash no longer loses discovered vulnerabilities
- `qa_results.json` updated incrementally

### 6. Reduced Screenshot Frequency
- Only captures screenshots on significant actions
- Reduces noise, improves performance

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
python agent_orchestrator.py --non-interactive --max-iterations 2
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
ANTHROPIC_API_KEY=...   # ~$384 credit expiring Dec 6-7 (use it!)

# Optional
TARGET_URL=http://localhost:5173
HEADLESS=true  # Set to false for visual debugging
DEMO_MODE=false # Set true to limit to 12 steps
```

---

## 🎯 Priorities for Next Session (Dec 4)

### 1. ✅ DONE: More Vulnerability Types
- ✅ SQLi on `/api/users/search` - database dump
- ✅ Auth bypass on `/api/login`
- ✅ Cleartext password detection
- ✅ API key exposure
- ✅ Session token leakage
- ✅ Stored XSS on `/contacts`

### 2. TODO: Switch Final Analysis to Claude
- Use Claude's 200K context window for comprehensive analysis
- Consolidate from 20+ Gemini calls to 2 Claude calls
- **Use the $384 credits before they expire Dec 6-7!**

### 3. TODO: Simplify Pipeline
- Current: 5 phases with many LLM calls
- Target: 2 phases (Discovery + Analysis)
- Phase 1: Rule-based API tests (no LLM) ← **implemented**
- Phase 2: 1 Claude call for comprehensive analysis ← **next**

### 4. TODO: Better RL Visualization
- Show reward improvement over iterations
- Dashboard should highlight when agent "learns"
- Track which payloads succeed vs fail

---

## 📁 Key Files

```
blackbox-rl-agent/
├── qa_agent_v1.py           # LangGraph RL agent
├── smart_qa_agent.py        # Simpler scanner (finds 6 vulns)
├── agent_orchestrator.py    # CEO/CTO loop with Claude
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

## 📝 Session Summary (Dec 3)

**What was accomplished:**
- ✅ Hybrid API + browser testing architecture
- ✅ Expanded from 2 to 6+ vulnerability tests
- ✅ Added cleartext password detection (CWE-256)
- ✅ Added API key exposure detection (CWE-200)
- ✅ Added session token leakage detection (CWE-200)
- ✅ Added UNION SELECT schema disclosure test
- ✅ Added stored XSS detection (CWE-79)
- ✅ Renamed orchestrator.py → agent_orchestrator.py
- ✅ Removed DEMO_MODE hardcoding
- ✅ Added crash protection for API findings
- ✅ Reduced screenshot frequency

**Current state:**
- API tests find 6+ vulnerabilities without any LLM calls
- Browser tests available for UI-specific vulnerabilities
- All 4 services healthy
- Ready for final Claude-based analysis integration

**Key insight:**
> The "intelligence" in finding vulnerabilities came from **hardcoded API tests**, not from Gemini RL. The LLM is better used for *analysis and reporting* rather than *discovery*.

**Next priorities:**
- Switch final analysis to Claude (use the $384 expiring credits!)
- Consolidate pipeline from 5 phases to 2
- Add RL visualization in dashboard

---

*Last updated: December 3, 2025 ~EOD*
