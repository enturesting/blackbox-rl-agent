# BlackBox AI - Context for Claude Agents

This file provides context for the CEO and CTO Claude agents when they're called from the orchestrator.
It's injected into prompts so they have awareness of the project state.

## Product Summary

**BlackBox RL Agent** is an AI-powered blackbox penetration testing framework that automatically discovers and exploits vulnerabilities in web applications.

**Key Differentiators:**
- Uses Reinforcement Learning to improve over time
- Browser-based (sees what users see)
- No source code access needed
- Finds real vulnerabilities, not just theoretical

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| RL Orchestration | LangGraph | State machine for agent loop |
| LLM Policy | Gemini 2.0 Flash | Decides next action |
| Browser Automation | Playwright | Navigates, clicks, fills forms |
| CEO/CTO Intelligence | Claude Sonnet | Strategic decisions |
| Backend | FastAPI | Dashboard API |
| Frontend | React + Vite | Dashboard UI |

## 5-Phase Pipeline

1. **RECON** (`qa_agent_v1.py`) - Playwright explores target, finds inputs
2. **PLAN** (`exploit_planner.py`) - Gemini generates attack strategy
3. **ATTACK** (`attack.py`) - Execute payloads
4. **ANALYZE** (`gemini_coderabbit_analyzer.py`) - Score findings
5. **REPORT** (`executive_report_generator.py`) - Executive summary

## GitHub Copilot Custom Agents

Located in `.github/agents/`:

### CEO Agent (`ceo.md`)
- **Role**: Product visionary, demo director
- **Focus**: Narrative, pitch, value proposition
- **Key Tasks**: Clarify vision, design demo flow, define MVP
- **Output**: Executive summaries, demo scripts, 60-second pitch

### CTO Agent (`cto.md`)
- **Role**: Technical co-founder, RL framework validator
- **Focus**: Playwright automation, LangGraph state machine, vulnerability discovery
- **Key Tasks**: Validate pipeline phases, debug agent behavior, fix technical issues
- **Output**: Status reports, debugging insights, code fixes

### How They Work Together
1. CTO validates environment (API keys, services, dependencies)
2. CTO runs QA agent against buggy-vibe
3. CEO evaluates demo readiness (0-100 score)
4. Loop until pitch-ready (score ≥ 80) or max iterations

## Target App: buggy-vibe

A deliberately vulnerable e-commerce site at `target-apps/buggy-vibe/`:
- **Frontend**: http://localhost:5173 (Vite React)
- **Backend**: http://localhost:3001 (Express + SQLite)

### Known Vulnerabilities (for demo)
| Endpoint | Vulnerability | Payload |
|----------|--------------|---------|
| `/api/users/search?username=X` | SQL Injection | `' OR '1'='1' --` |
| `POST /api/login` | Auth Bypass | username: `admin' OR '1'='1' --` |

### Expected Demo Flow
1. Agent navigates to http://localhost:5173
2. Agent clicks "Users" in navbar
3. Agent fills search with SQLi payload
4. Agent presses Enter
5. **Success**: Database dump with all users + passwords

## Key Log Files

CTO should review these before running iterations:

| File | Purpose |
|------|---------|
| `rl_training_data.json` | RL rewards per step (are they meaningful?) |
| `orchestrator_state.json` | Current state, findings, scores |
| `orchestrator_events.json` | Full event history (~100+ events) |
| `qa_reports/qa_report_*.md` | Human-readable execution logs |
| `generated_tests/*.py` | Timestamped Playwright test files |

## Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 0 vulnerabilities found | Agent not clicking forms | Check Playwright selectors |
| Agent stuck in loop | Same 4 actions repeating | Loop detection should break |
| Rate limit errors | Gemini 10 RPM limit | Rotate API keys (we have 5 = 50 RPM) |
| Timeout | Too many steps | Set DEMO_MODE=true |
| buggy-backend unhealthy | :3001 not responding | Check server-vulnerable.cjs started |

## Environment Variables

```bash
GOOGLE_API_KEY          # Primary Gemini key
GOOGLE_API_KEY_2..5     # Backup keys (total 50 RPM)
ANTHROPIC_API_KEY       # Claude for CEO/CTO ($452 credit, expires Dec 7)
TARGET_URL              # Default: http://localhost:5173
DEMO_MODE               # true = 12 steps max
HEADLESS                # true = no browser UI
```

## Success Criteria

**Minimum Viable Demo (Current State ✅):**
- [x] Agent navigates to /users page
- [x] Agent fills search with SQLi payload
- [x] Database dump visible in response
- [x] Screenshot captured as evidence
- [x] Report generated with findings
- [x] All 4 services healthy

**Pitch Ready (80+ score - Not Yet):**
- [ ] 3+ vulnerabilities found (currently 1)
- [ ] 2+ vulnerability types (currently 1 - SQLi)
- [ ] 1+ critical severity ✅
- [ ] Reproducible results ✅
- [ ] RL learning demonstrated across iterations
