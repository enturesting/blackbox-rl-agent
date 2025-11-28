# 🚚 Migration Guide: Pull from mfinch19/aie-hackathon

> **Run these commands in your `enturesting/blackbox-rl-agent` Codespace**

## Quick Migration (Copy-Paste)

```bash
# Add source, fetch, checkout as feature/mvp, push, cleanup
git remote add source https://github.com/mfinch19/aie-hackathon.git && \
git fetch source feature/qa-agentnick && \
git checkout -b feature/mvp source/feature/qa-agentnick && \
git push -u origin feature/mvp && \
git remote remove source
```

## Step-by-Step (if you prefer)

### 1. Add the source repository
```bash
git remote add source https://github.com/mfinch19/aie-hackathon.git
```

### 2. Fetch the branch with all the code
```bash
git fetch source feature/qa-agentnick
```

### 3. Create your feature/mvp branch from it
```bash
git checkout -b feature/mvp source/feature/qa-agentnick
```

### 4. Push to your repo
```bash
git push -u origin feature/mvp
```

### 5. Remove the source remote (optional cleanup)
```bash
git remote remove source
```

---

## After Migration: Environment Setup

### Create your .env file
```bash
cp .env.example .env
```

### Add your Google API key
Edit `.env` and add your Gemini API key:
```
GOOGLE_API_KEY=your-key-here
```

### Verify .env is gitignored
```bash
git status | grep ".env" && echo "WARNING: .env might be tracked!" || echo "✅ .env is safely ignored"
```

### Install dependencies
```bash
# Python
pip install -r requirements.txt
playwright install chromium

# Frontend
cd frontend && npm install && cd ..

# Target app
cd target-apps/buggy-vibe && npm install && cd ../..
```

### Run the demo
```bash
./run_demo.sh
```

Open http://localhost:3000 and click **Run Full Pipeline**

---

## What's Included

| Component | Description |
|-----------|-------------|
| `qa_agent_v1.py` | RL reconnaissance agent |
| `exploit_planner.py` | Attack planning |
| `attack.py` | Exploitation |
| `server.py` | FastAPI backend |
| `frontend/` | React dashboard |
| `target-apps/buggy-vibe/` | Vulnerable test app |
| `run_demo.sh` | One-command launcher |

## Already Rebranded

These files reference `blackbox-rl-agent` / `enturesting`:
- README.md
- CONTEXT_HANDOFF.md  
- DEMO_SCRIPT.md

---

*This file can be deleted after migration is complete.*
