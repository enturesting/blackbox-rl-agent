# AI Security Testing Demo Script

## Pre-Demo Setup (5 minutes before)

### 1. Start BuggyVibe Application
```bash
# Terminal 1: Start vulnerable backend
cd /Users/a_nick/Documents/AI-Hack/buggy-vibe
npm run server:vulnerable

# Terminal 2: Start frontend (will run on port 5174)
cd /Users/a_nick/Documents/AI-Hack/buggy-vibe
npm run dev
```

### 2. Verify Environment
```bash
# Terminal 3: Navigate to QA agent
cd blackbox-rl-agent
source venv/bin/activate

# Check API keys loaded
echo "API Keys configured: $(grep -c "GOOGLE_API_KEY" .env)"
```

## Demo Flow (10-15 minutes)

### Part 1: Introduction (2 minutes)
"Today we're demonstrating an AI-powered security testing agent that autonomously finds and exploits vulnerabilities in web applications."

**Key Points:**
- Uses reinforcement learning to explore web apps
- Learns from rewards/penalties to find vulnerabilities
- Generates executive-ready security reports

### Part 2: Show the Vulnerable App (1 minute)
1. Open browser to http://localhost:5174
2. Show the BuggyVibe application
3. Mention: "This app has intentional SQL injection vulnerabilities"

### Part 3: Run the AI Security Agent (5-7 minutes)

```bash
# Run the QA agent
python qa_agent_v1.py
```

**While it's running, explain:**
- "The agent is autonomously navigating the site"
- "It's trying different attack vectors"
- "Notice how it learns from rewards - SQL injection gets high rewards"
- "It's specifically targeting the Users page to dump the database"

**Expected output:**
```
🔑 Loaded 3 API keys (Effective RPM: 30)
🏎️ Starting SecGym Agent...
🚀 Initializing Security Gym Environment...
🤔 Agent Thinking... (Current Reward: 0.0)
💰 REWARD: 0.1 (Standard Valid Action)
🤔 Agent Thinking... (Current Reward: 0.1)
💰 REWARD: 1.0 (SQL injection detected!)
...
```

### Part 4: Show the Results (3-5 minutes)

#### A. Show Screenshots
```bash
# Open Finder to show screenshots
open qa_screenshots/
```
- Show progression from login → SQL injection → Users page → Database dump

#### B. Show Executive Report
```bash
# Display latest executive report
cat qa_reports/executive_report_*.md | tail -n 50
```

**Highlight:**
- Risk Assessment: HIGH
- Business Impact section
- Specific recommendations
- "This is what a CISO would receive"

### Part 5: Key Takeaways (2 minutes)

1. **Autonomous Testing**: "No manual scripting required"
2. **Learning Capability**: "Gets better at finding vulnerabilities"
3. **Business Value**: "Converts technical findings to executive insights"
4. **Scalability**: "Can test multiple applications simultaneously"

## Backup Plans

### If API Quota Exceeded:
"Due to API limits, let me show you the results from our previous run..."
- Show existing screenshots
- Show existing executive report

### If App Crashes:
"Let me show you the captured results..."
- Focus on screenshots and reports already generated

### If Time is Short:
- Skip the live run
- Show pre-captured screenshots
- Focus on executive report

## Demo Success Metrics
✅ Agent finds SQL injection vulnerability
✅ Agent reaches Users page
✅ Agent attempts database dump
✅ Executive report generated
✅ Clear business impact communicated

## Questions to Anticipate

**Q: How long does a full security test take?**
A: "Typically 10-30 minutes depending on app complexity. We're showing a shortened version."

**Q: What other vulnerabilities can it find?**
A: "XSS, authentication bypass, IDOR, file upload vulnerabilities, and more."

**Q: How does it compare to traditional security testing?**
A: "It's autonomous, learns from experience, and provides business-context reports automatically."

**Q: What's the ROI?**
A: "Reduces security testing time by 80%, finds vulnerabilities before hackers do, prevents costly breaches."

## Final Demo Command Summary
```bash
# Quick copy-paste commands for demo:

# 1. Start BuggyVibe backend
cd target-apps/buggy-vibe && npm run server:vulnerable

# 2. Start BuggyVibe frontend  
cd target-apps/buggy-vibe && npm run dev

# 3. Run QA Agent (or use ./run_demo.sh)
cd blackbox-rl-agent && source venv/bin/activate && python qa_agent_v1.py

# 4. View results
open qa_screenshots/
cat qa_reports/executive_report_* | tail -n 50
```

Good luck with your demo! 🚀
