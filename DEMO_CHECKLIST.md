# Demo Readiness Checklist

This file is shared between the **CEO** and **CTO** agents to coordinate demo preparation.

---

## Current Status: 🔴 Not Ready

**Last Updated:** _Not started_  
**Updated By:** _None_

---

## CEO Responsibilities (Vision & Narrative)

- [ ] Demo script written (≤60 seconds)
- [ ] "Wow moment" clearly identified
- [ ] Value proposition is crystal clear
- [ ] Target audience defined (investors? developers? CISOs?)
- [ ] What we say during the demo documented
- [ ] Fallback talking points if something breaks

---

## CTO Responsibilities (Technical Validation)

### Infrastructure
- [ ] Target app (buggy-vibe) starts without errors
- [ ] Frontend dashboard starts without errors
- [ ] Backend server starts without errors
- [ ] All services can communicate

### Core Functionality
- [ ] QA agent runs against target app
- [ ] Agent discovers at least 1 vulnerability
- [ ] Results appear in dashboard
- [ ] No rate limit errors in happy path

### Reliability
- [ ] Demo works 3x in a row without failure
- [ ] Graceful handling if API key missing
- [ ] Graceful handling if rate limited
- [ ] Works in fresh Codespace

### Code Quality
- [ ] No secrets in committed code
- [ ] .env.example is accurate
- [ ] README has working setup instructions

---

## Shared Sign-Off

| Role | Ready? | Notes |
|------|--------|-------|
| CEO  | ⬜ | |
| CTO  | ⬜ | |

---

## Blockers & Issues

_List any blockers preventing demo readiness:_

1. _None yet_

---

## Demo Run Log

_Record each demo test run:_

| Date | Who | Result | Notes |
|------|-----|--------|-------|
| | | | |

---

## How to Use This File

1. **CEO Agent**: Update vision/narrative items, document the story
2. **CTO Agent**: Update technical items, report what works/breaks
3. **Both**: Check each other's sections, flag conflicts
4. **Human**: Review overall status, make final call

When both CEO and CTO mark "Ready", the demo is go.
