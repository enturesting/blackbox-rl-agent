import os
import sys
import json
import builtins
import functools
import aiohttp
from datetime import datetime
from typing import TypedDict, Annotated, List, Dict, Any
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, Page
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
import random
import asyncio
import time

load_dotenv()

# Force unbuffered output for real-time log streaming
sys.stdout.reconfigure(line_buffering=True)
print = functools.partial(builtins.print, flush=True)

# Demo mode - stops early after finding SQL injection for reliable demos
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_MAX_STEPS = 12  # Enough to find SQLi, not enough to hit rate limits

# Get target URL from environment or use default
TARGET_URL = os.getenv("TARGET_URL", "http://localhost:5173")

# API key rotation - Add 8+ keys to get 80+ RPM (10 RPM per key)
API_KEYS = []
for i in range(1, 10):  # Check for up to 9 API keys
    key_name = f"GOOGLE_API_KEY_{i}" if i > 1 else "GOOGLE_API_KEY"
    key = os.getenv(key_name)
    if key:
        API_KEYS.append(key)
        
if len(API_KEYS) == 0:
    raise ValueError("No Google API keys found! Add GOOGLE_API_KEY to .env")
    
print(f"🔑 Loaded {len(API_KEYS)} API keys (Effective RPM: {len(API_KEYS) * 10})")
if DEMO_MODE:
    print("🎬 DEMO MODE enabled - tight step limit for reliable demos")

# Browser visibility mode
HEADLESS_MODE = os.getenv("HEADLESS", "true").lower() == "true"
if not HEADLESS_MODE:
    print("👀 HEADLESS=false - Browser will be VISIBLE for demo/debugging")


# --- DIRECT API TESTING (Hybrid Approach) ---
# These tests run directly against the backend API, bypassing Playwright
# for faster vulnerability discovery on endpoints that don't require UI interaction

async def run_direct_api_tests(base_url: str = "http://localhost:3001") -> List[Dict[str, Any]]:
    """
    Run direct HTTP tests against known vulnerable API endpoints.
    This is faster than Playwright for testing API-level vulnerabilities.
    
    Vulnerabilities tested:
    1. SQL Injection on /api/users/search (database dump)
    2. SQL Injection on /api/login (auth bypass)
    3. UNION SELECT attack (schema disclosure)
    4. Cleartext password storage (from SQLi response)
    5. API key exposure (from SQLi response)
    6. Session token exposure (from SQLi response)
    
    Returns a list of findings for discovered vulnerabilities.
    """
    findings = []
    sqli_response_data = None  # Store SQLi response for additional analysis
    
    async with aiohttp.ClientSession() as session:
        # Test 1: SQL Injection on /api/users/search
        print("🔍 [API Test 1/6] Testing /api/users/search for SQLi...")
        try:
            sqli_payload = "' OR '1'='1' --"
            async with session.get(
                f"{base_url}/api/users/search",
                params={"username": sqli_payload},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                sqli_response_data = data  # Save for further analysis
                
                # Response format: {"users": [...], "api_keys": [...], "sessions": [...]}
                users = data.get("users", data) if isinstance(data, dict) else data
                users = users if isinstance(users, list) else []
                
                # Check if we got more than expected (database dump) - SQLi returns ALL users
                if len(users) > 1:
                    print(f"✅ [API Test] SQLi VULNERABLE! Got {len(users)} users (expected 0-1)")
                    findings.append({
                        "step": "api_test",
                        "action": "api_sqli_users_search",
                        "target": {"endpoint": "/api/users/search", "param": "username"},
                        "log": f"SQL injection on /api/users/search returned {len(users)} users",
                        "reward": 2.0,
                        "severity": "CRITICAL",
                        "cwe": "CWE-89",
                        "reason": "Database dump achieved via SQL injection",
                        "evidence": json.dumps(users[:3])  # First 3 records as evidence
                    })
                else:
                    print(f"ℹ️ [API Test] /api/users/search returned {len(users)} users (may need different payload)")
        except Exception as e:
            print(f"⚠️ [API Test] /api/users/search error: {e}")
        
        # Test 2: Check for CLEARTEXT passwords in SQLi response
        print("🔍 [API Test 2/6] Analyzing SQLi response for cleartext passwords...")
        if sqli_response_data:
            users = sqli_response_data.get("users", [])
            cleartext_passwords = []
            for user in users:
                if "password" in user and isinstance(user.get("password"), str):
                    pwd = user.get("password", "")
                    # Check if it looks like plaintext (not hashed)
                    if len(pwd) < 64 and not pwd.startswith("$2") and not pwd.startswith("pbkdf2"):
                        cleartext_passwords.append({"user": user.get("username"), "password": pwd})
            
            if cleartext_passwords:
                print(f"✅ [API Test] CLEARTEXT PASSWORDS! Found {len(cleartext_passwords)} unhashed passwords")
                findings.append({
                    "step": "api_test",
                    "action": "cleartext_password_storage",
                    "target": {"endpoint": "/api/users/search", "field": "password"},
                    "log": f"Found {len(cleartext_passwords)} users with cleartext passwords",
                    "reward": 1.5,
                    "severity": "HIGH",
                    "cwe": "CWE-256",
                    "reason": "Passwords stored in cleartext without hashing",
                    "evidence": json.dumps(cleartext_passwords[:3])
                })
        
        # Test 3: Check for API key exposure in SQLi response
        print("🔍 [API Test 3/6] Analyzing SQLi response for API key exposure...")
        if sqli_response_data:
            api_keys = sqli_response_data.get("api_keys", [])
            if api_keys and len(api_keys) > 0:
                print(f"✅ [API Test] API KEYS EXPOSED! Found {len(api_keys)} API keys")
                findings.append({
                    "step": "api_test",
                    "action": "api_key_exposure",
                    "target": {"endpoint": "/api/users/search", "field": "api_keys"},
                    "log": f"SQL injection exposed {len(api_keys)} API keys",
                    "reward": 1.5,
                    "severity": "CRITICAL",
                    "cwe": "CWE-200",
                    "reason": "API keys exposed via SQL injection response",
                    "evidence": json.dumps([{"key": k.get("key", "")[:8] + "...", "owner": k.get("owner")} for k in api_keys])
                })
            
            # Check for session token exposure
            sessions = sqli_response_data.get("sessions", [])
            if sessions and len(sessions) > 0:
                print(f"✅ [API Test] SESSION TOKENS EXPOSED! Found {len(sessions)} active sessions")
                findings.append({
                    "step": "api_test",
                    "action": "session_token_exposure",
                    "target": {"endpoint": "/api/users/search", "field": "sessions"},
                    "log": f"SQL injection exposed {len(sessions)} active session tokens",
                    "reward": 1.5,
                    "severity": "CRITICAL",
                    "cwe": "CWE-200",
                    "reason": "Active session tokens exposed via SQL injection",
                    "evidence": json.dumps([{"user_id": s.get("user_id"), "token": s.get("token", "")[:20] + "..."} for s in sessions])
                })
        
        # Test 4: UNION SELECT attack for schema disclosure
        print("🔍 [API Test 4/6] Testing UNION SELECT attack for schema disclosure...")
        try:
            union_payload = "' UNION SELECT * FROM information_schema.tables --"
            async with session.get(
                f"{base_url}/api/users/search",
                params={"username": union_payload},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                # Check if schema was disclosed
                if "schema" in data or "tables" in str(data):
                    print(f"✅ [API Test] UNION ATTACK worked! Schema exposed")
                    findings.append({
                        "step": "api_test",
                        "action": "union_select_schema_disclosure",
                        "target": {"endpoint": "/api/users/search", "attack": "UNION SELECT"},
                        "log": "UNION SELECT attack exposed database schema",
                        "reward": 1.5,
                        "severity": "HIGH",
                        "cwe": "CWE-89",
                        "reason": "Database schema exposed via UNION SELECT injection",
                        "evidence": json.dumps(data.get("schema", data))[:500]
                    })
                else:
                    print(f"ℹ️ [API Test] UNION SELECT returned: {str(data)[:100]}")
        except Exception as e:
            print(f"⚠️ [API Test] UNION SELECT error: {e}")
        
        # Test 5: Auth Bypass on /api/login
        print("🔍 [API Test 5/6] Testing /api/login for auth bypass...")
        try:
            sqli_login_payload = {
                "username": "admin' OR '1'='1' --",
                "password": "anything"
            }
            async with session.post(
                f"{base_url}/api/login",
                json=sqli_login_payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
                # Check for successful auth bypass indicators
                if resp.status == 200 and ("token" in data or "success" in str(data).lower() or "admin" in str(data).lower()):
                    print(f"✅ [API Test] Auth Bypass VULNERABLE! Response: {str(data)[:100]}")
                    findings.append({
                        "step": "api_test",
                        "action": "api_auth_bypass_login",
                        "target": {"endpoint": "/api/login", "method": "POST"},
                        "log": f"Auth bypass on /api/login successful",
                        "reward": 2.0,
                        "severity": "CRITICAL",
                        "cwe": "CWE-287",
                        "reason": "Authentication bypass via SQL injection",
                        "evidence": json.dumps(data)[:500]
                    })
                else:
                    print(f"ℹ️ [API Test] /api/login status {resp.status}, response: {str(data)[:100]}")
        except Exception as e:
            print(f"⚠️ [API Test] /api/login error: {e}")
        
        # Test 6: XSS via Contact Form (Stored XSS check)
        print("🔍 [API Test 6/6] Testing /contacts for stored XSS...")
        try:
            xss_payload = {
                "name": "<script>alert('XSS')</script>",
                "email": "test@test.com",
                "message": "<img src=x onerror=alert('XSS')>"
            }
            async with session.post(
                f"{base_url}/contacts",
                json=xss_payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Check if XSS payload was stored unescaped
                    if "<script>" in str(data) or "onerror" in str(data):
                        print(f"✅ [API Test] Stored XSS VULNERABLE! Payload stored unescaped")
                        findings.append({
                            "step": "api_test",
                            "action": "stored_xss_contact",
                            "target": {"endpoint": "/contacts", "method": "POST"},
                            "log": "Contact form accepts and stores XSS payloads without sanitization",
                            "reward": 1.5,
                            "severity": "MEDIUM",
                            "cwe": "CWE-79",
                            "reason": "Stored XSS - malicious scripts stored and potentially rendered",
                            "evidence": json.dumps(data)[:500]
                        })
                    else:
                        print(f"ℹ️ [API Test] Contact form response: {str(data)[:100]}")
        except Exception as e:
            print(f"⚠️ [API Test] /contacts error: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 [API Test] Direct API tests complete: {len(findings)} vulnerabilities found")
    print(f"{'='*60}\n")
    return findings

# Track API key usage to rotate intelligently
API_KEY_INDEX = 0

# Rate limit retry helper with exponential backoff
async def call_model_with_retry(model, prompt, max_retries=3):
    """Call the model with exponential backoff on rate limit errors."""
    global API_KEY_INDEX
    
    for attempt in range(max_retries):
        try:
            return await model.ainvoke(prompt)
        except Exception as e:
            error_str = str(e).lower()
            if "429" in str(e) or "quota" in error_str or "rate" in error_str:
                wait_time = (2 ** attempt) + random.random()
                print(f"⏳ Rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait_time:.1f}s and rotating key...")
                await asyncio.sleep(wait_time)
                # Rotate to next API key
                API_KEY_INDEX = (API_KEY_INDEX + 1) % len(API_KEYS)
            else:
                raise
    raise Exception(f"Max retries ({max_retries}) exceeded due to rate limiting")

# --- 1. STATE DEFINITION (RL INFRASTRUCTURE) ---
class AgentState(TypedDict):
    browser: Browser
    page: Page
    url: str
    steps: int
    maxSteps: int
    logs: Annotated[List[str], lambda x, y: x + y]
    issues: Annotated[List[str], lambda x, y: x + y]
    screenshotRefs: Annotated[List[str], lambda x, y: x + y]
    visitedUrls: Annotated[List[str], lambda x, y: x + y]
    lastAction: str
    actionPayload: dict
    # RL SPECIFIC FIELDS
    cumulativeReward: float
    stepRewards: Annotated[List[float], lambda x, y: x + y]
    trajectory: Annotated[List[Dict[str, Any]], lambda x, y: x + y]
    # LOOP DETECTION FIELDS
    actionHistory: Annotated[List[str], lambda x, y: x + y]  # Track action signatures
    loopDetected: bool

# Helper to sanitize filenames
def sanitize(s: str) -> str:
    return ''.join(c if c.isalnum() else '_' for c in s).lower()

# --- 2. NODES ---

async def initialize_browser(state: AgentState) -> dict:
    print("🚀 Initializing Security Gym Environment...")

    if not os.path.exists("qa_screenshots"):
        os.makedirs("qa_screenshots")

    playwright = await async_playwright().start()
    # Use incognito mode to ensure clean state
    # Use headless mode for CI/Codespace environments (no display)
    headless_mode = os.getenv("HEADLESS", "true").lower() == "true"
    browser = await playwright.chromium.launch(
        headless=headless_mode,
        args=['--incognito', '--no-sandbox', '--disable-dev-shm-usage']
    )
    context = await browser.new_context()
    page = await context.new_page()
    
    # Use TARGET_URL from environment variable
    target_url = TARGET_URL
    print(f"🎯 Target URL: {target_url}")
    page_loaded = False
    for retry in range(3):
        try:
            await page.goto(target_url, timeout=10000)
            # Ensure we're on the home page, not a cached page
            await page.wait_for_timeout(1000)
            current_url = page.url
            if "/users" in current_url or "/login" in current_url:
                print("📍 Navigating back to home page...")
                await page.goto(target_url)
                await page.wait_for_timeout(1000)
            page_loaded = True
            print(f"✅ Page loaded successfully: {page.url}")
            break
        except Exception as e:
            print(f"⚠️ Retry {retry+1}/3: Could not load {target_url}. Error: {str(e)[:100]}")
            await asyncio.sleep(2)
    
    if not page_loaded:
        print(f"❌ FATAL: Could not load {target_url} after 3 retries. Is the frontend running?")
        print("💡 Tip: Start buggy-vibe with: cd target-apps/buggy-vibe && npm run dev")

    return {
        "browser": browser,
        "page": page,
        "url": target_url,
        "steps": 0,
        "maxSteps": 50,  # Increased to allow reaching Users page
        "logs": ["Started RL Training Session." if page_loaded else "FAILED: Frontend not reachable"],
        "cumulativeReward": 0.0,
        "stepRewards": [],
        "trajectory": [],
        "visited_pages": set(),
        "actions_on_page": {},  # Track actions per page to prevent loops
        "actionHistory": [],  # Track action signatures for loop detection
        "loopDetected": False,
        "page_loaded": page_loaded  # Track if page loaded successfully
    }
async def analyze_and_decide(state: AgentState) -> dict:
    page = state["page"]
    steps = state["steps"]
    maxSteps = state["maxSteps"]
    logs = state["logs"]
    current_reward = state.get("cumulativeReward", 0.0)
    action_history = state.get("actionHistory", [])

    # Skip browser exploration if page didn't load
    if not state.get("page_loaded", True):
        print("⚠️ Skipping browser exploration - page not loaded")
        return {"lastAction": "finish"}

    if steps >= maxSteps:
        return {"lastAction": "finish"}
    
    # LOOP DETECTION: Check if we're stuck repeating same actions
    if len(action_history) >= 4:
        # Check for circular pattern (e.g., A-B-A-B or A-A-A-A)
        last_4 = action_history[-4:]
        if len(set(last_4)) <= 2:  # Only 1-2 unique actions in last 4
            print(f"🔄 LOOP DETECTED: Last 4 actions were {last_4}")
            # Try to break the loop by forcing a different action
            if "/users" not in page.url:
                # Force navigation to users page
                print("🔧 Breaking loop: Forcing navigation to Users page")
                return {
                    "lastAction": "navigate_direct",
                    "actionPayload": {
                        "targetUrl": TARGET_URL + "/users",
                        "actionDetails": "Breaking loop: Direct navigation to Users page",
                        "inputValue": ""
                    },
                    "loopDetected": True
                }
            else:
                # Already on users page, finish to prevent infinite loop
                print("🛑 Breaking loop: Already on Users page, finishing")
                return {"lastAction": "finish", "loopDetected": True}

    # 1. Get Observation (Interactive Elements)
    buttons = await page.query_selector_all('button, input, a[href], [role="button"], textarea, select')
    visible_elements = []
    
    for i, el in enumerate(buttons):
        try:
            if await el.is_visible() and await el.is_enabled():
                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                eid = await el.get_attribute('id') or f"el-{i}"
                text = await el.inner_text()
                placeholder = await el.get_attribute("placeholder")
                info = text[:20] if text else (placeholder if placeholder else "")
                
                visible_elements.append(f"- Index {i}: <{tag} id='{eid}'> {info}")
        except:
            continue

    element_list = "\n".join(visible_elements[:50]) # Limit context size

    # 2. Check History for Warnings (The "Memory" logic)
    trajectory = state.get("trajectory", [])
    last_move_warning = ""
    if len(trajectory) > 0:
        last_move = trajectory[-1]
        if last_move['reward'] < 0:
            last_move_warning = f"⚠️ WARNING: Your last action '{last_move['action']}' received a NEGATIVE reward ({last_move['reward']}). DO NOT REPEAT IT."
        else:
            last_move_warning = f"NOTE: You just did '{last_move['action']}'. Try a DIFFERENT action to find new vulnerabilities."

    print(f"🤔 Agent Thinking... (Current Reward: {current_reward})")
    
    # Add small delay to avoid hitting quota too fast
    await asyncio.sleep(2)

    # 3. The Policy Model (Gemini) - Rotate API keys
    global API_KEY_INDEX
    api_key = API_KEYS[API_KEY_INDEX % len(API_KEYS)]
    API_KEY_INDEX += 1
    
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp", # Works with langchain
        api_key=api_key,
        temperature=0.1,
    )

    # Track which vulnerabilities we've already found
    vulns_found = []
    for step in trajectory:
        if step.get("reward", 0) >= 1.0:
            target = step.get("target", {})
            page_type = "users_search" if "search" in str(target.get("placeholder", "")).lower() else "login"
            vulns_found.append(page_type)
    vulns_found_str = ", ".join(vulns_found) if vulns_found else "None yet"
    
    prompt = f"""
    You are an RL Agent training to find security vulnerabilities in web applications.
    
    Current State:
    - URL: {page.url}
    - Steps Taken: {steps}/{maxSteps}
    - Cumulative Reward: {current_reward} (Maximize this!)
    - Vulnerabilities Found So Far: {vulns_found_str}
    
    {last_move_warning} <--- CRITICAL INSTRUCTION
    
    Interactive Elements:
    {element_list}
    
    Recent Logs:
    {chr(10).join(logs[-3:])}
    
    YOUR GOAL: Find MULTIPLE vulnerabilities to maximize your reward!
    
    VULNERABILITY TARGETS (in priority order):
    1. **Users Page SQLi** (CRITICAL - +2.0 reward):
       - Navigate to /users page 
       - Fill search box with: ' OR '1'='1' --
       - Press Enter to trigger database dump
       
    2. **Login Page Auth Bypass** (CRITICAL - +2.0 reward):
       - Navigate to /login page
       - Fill username with: admin' OR '1'='1' --  
       - Fill password with: anything
       - Click Login to bypass authentication
       
    3. **Contact Form XSS** (HIGH - +1.0 reward):
       - Navigate to /contact page
       - Fill name/message with: <script>alert(1)</script>
       - Submit to test for XSS
    
    STRATEGY:
    - If on home page: Go to /users first (highest value target)
    - If already exploited /users: Go to /login next
    - If both exploited: Go to /contact for XSS
    - DON'T repeat attacks on pages you've already tested!
    
    Current URL: {page.url}
    
    Rewards:
    - +2.0: Database dump OR auth bypass (HIGHEST!)
    - +1.0: SQL injection submitted, XSS triggered
    - +0.5: Reached new vulnerable page
    - +0.2: Valid navigation to new page
    - -0.5: Repeated action on same page
    
    Choose your next action. Return ONLY JSON:
    {{
      "action": "fill_input" | "click_element" | "check_responsiveness" | "finish",
      "targetIndex": <number>,
      "actionDetails": "<strategy reasoning>",
      "inputValue": "<test_payload>" 
    }}
    """

    try:
        response = await model.ainvoke(prompt)
        content = str(response.content).replace("```json", "").replace("```", "").strip()
        
        # Extract JSON
        if "{" in content:
            content = content[content.find("{"):content.rfind("}")+1]
            
        decision = json.loads(content)
        
        return {
            "lastAction": decision["action"],
            "actionPayload": {
                "targetIndex": decision.get("targetIndex"),
                "actionDetails": decision.get("actionDetails", ""),
                "inputValue": decision.get("inputValue", "")
            }
        }
    except Exception as e:
        print(f"Fallback: {e}")
        # Smart fallback based on current page
        current_url = page.url
        steps = state.get("steps", 0)
        
        if "localhost:5173" in current_url and "/" in current_url and not "/users" in current_url:
            # On home page, click Users link
            return {
                "lastAction": "click_element",
                "actionPayload": {
                    "targetIndex": 4,  # Users link is usually 5th link in navbar
                    "actionDetails": "Fallback: Navigate to Users page",
                    "inputValue": ""
                }
            }
        elif "/users" in current_url:
            # On users page, try search box
            return {
                "lastAction": "fill_input", 
                "actionPayload": {
                    "targetIndex": 0,  # search field is usually first
                    "actionDetails": "Fallback: SQL injection in search",
                    "inputValue": "' OR '1'='1' --"
                }
            }
        
        return {"lastAction": "finish"}

async def execute_action(state: AgentState) -> dict:
    page = state["page"]
    action = state["lastAction"]
    payload = state.get("actionPayload", {})
    logs = state["logs"]
    actions_on_page = state.get("actions_on_page", {})
    action_history = state.get("actionHistory", [])
    current_url = page.url
    
    if action == "finish":
        return {"logs": logs}
    
    # Handle direct navigation (loop breaker)
    if action == "navigate_direct":
        target_url = payload.get("targetUrl", "")
        if target_url:
            await page.goto(target_url)
            await page.wait_for_timeout(1000)
            logs.append(f"Action: Direct navigation to {target_url}")
            action_sig = f"navigate:{target_url}"
            return {
                "steps": state.get("steps", 0) + 1,
                "logs": logs,
                "actionHistory": action_history + [action_sig]
            }
    
    # Track actions to prevent loops
    page_key = "login" if "/login" in current_url else "users" if "/users" in current_url else "home"
    if page_key not in actions_on_page:
        actions_on_page[page_key] = []
    
    # Check if we've already done SQL injection on this page
    action_key = f"{action}:{payload.get('inputValue', '')}"
    if action_key in actions_on_page[page_key]:
        logs.append(f"BLOCKED: Already performed {action_key} on {page_key} page")
        return {"logs": logs, "actions_on_page": actions_on_page}
    
    # Special check: if we've already done SQL injection on Users page, we're done!
    if page_key == "users" and any("' OR '1'='1'" in act for act in actions_on_page[page_key]):
        logs.append("Mission Complete: SQL injection already performed on Users page")
        return {"logs": logs, "actions_on_page": actions_on_page, "mission_complete": True}
    
    actions_on_page[page_key].append(action_key)
    
    # Get interactive elements
    try:
        elements = await page.query_selector_all('button, input, a[href], [role="button"], textarea, select')
        idx = payload.get("targetIndex")
        
        # Validate Index and Capture Identity
        target_el = None
        target_element_details = {}
        
        if idx is not None and idx < len(elements):
            target_el = elements[idx]
            
            # --- CAPTURE ELEMENT IDENTITY ---
            try:
                target_element_details = {
                    "tagName": await target_el.evaluate("e => e.tagName.toLowerCase()"),
                    "id": await target_el.get_attribute("id") or "no-id",
                    "name": await target_el.get_attribute("name") or "no-name",
                    "placeholder": await target_el.get_attribute("placeholder") or "",
                    "outerHTML": await target_el.evaluate("e => e.outerHTML.substring(0, 150)") # First 150 chars
                }
            except:
                target_element_details = {"error": "could_not_capture_details"}
            # -------------------------------

        if action == "fill_input" and target_el:
            val = payload.get("inputValue", "test")
            await target_el.fill(val)
            logs.append(f"Action: Filled input index {idx} ({target_element_details.get('id')}) with '{val}'")
            
            # If this is the search box on Users page, press Enter to submit
            current_url = page.url
            placeholder_text = target_element_details.get("placeholder", "").lower()
            name_text = target_element_details.get("name", "").lower()
            
            # Debug logging
            if "/users" in current_url:
                logs.append(f"DEBUG: On Users page, placeholder='{placeholder_text}', name='{name_text}'")
            
            if "/users" in current_url and ("search" in placeholder_text or 
                                            "username" in placeholder_text or
                                            "Enter username" in placeholder_text):
                await page.wait_for_timeout(500)
                await target_el.press("Enter")
                logs.append("Action: Pressed Enter to submit search")
                await page.wait_for_timeout(2000)  # Wait for results
                
        elif action == "click_element" and target_el:
            await target_el.click()
            logs.append(f"Action: Clicked element index {idx} ({target_element_details.get('id')})")
            await page.wait_for_timeout(1000) # Wait for reaction

        elif action == "check_responsiveness":
            logs.append("Action: Checked Responsiveness")
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.wait_for_timeout(500)
            await page.set_viewport_size({"width": 1280, "height": 800})

        # Capture State (Screenshot) - only on significant actions
        # Significant = form submissions, SQL injection attempts, navigation to new pages
        should_screenshot = False
        screenshot_reason = ""
        
        if action == "fill_input" and payload.get("inputValue", ""):
            # Screenshot after filling forms with payloads (potential vuln)
            input_val = payload.get("inputValue", "").lower()
            if any(kw in input_val for kw in ["'", "or", "1=1", "script", "alert", "--", "union"]):
                should_screenshot = True
                screenshot_reason = "sqli_or_xss_payload"
        elif action == "click_element":
            # Screenshot after clicking submit/login buttons
            target_text = str(target_element_details.get("outerHTML", "")).lower()
            if any(kw in target_text for kw in ["submit", "login", "search", "send"]):
                should_screenshot = True
                screenshot_reason = "form_submission"
        elif "/login" in current_url or "/users" in current_url:
            # Always screenshot on vulnerable pages after actions
            should_screenshot = True
            screenshot_reason = "vulnerable_page"
        
        if should_screenshot:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            steps = state.get("steps", 0)
            path = f"qa_screenshots/step_{steps}_{screenshot_reason}_{timestamp}.png"
            await page.screenshot(path=path)
            logs.append(f"📸 Screenshot saved: {screenshot_reason}")

    except Exception as e:
        logs.append(f"Error: {str(e)}")
    
    # Create action signature for loop detection
    action_sig = f"{action}:{payload.get('targetIndex', 'N/A')}:{payload.get('inputValue', '')[:20]}"
    
    # Pass these details to the next node (Reward Node)
    return {
        "steps": state.get("steps", 0) + 1,  # Increment steps here
        "logs": logs,
        "actions_on_page": actions_on_page,
        "actionHistory": action_history + [action_sig],  # Track for loop detection
        # UPDATE PAYLOAD with target details so Reward Node can see them
        "actionPayload": {**payload, "targetDetails": target_element_details} 
    }

# --- 3. THE REWARD MODEL NODE (The "Stagnation Fix" Version) ---
async def evaluate_reward(state: AgentState) -> dict:
    """
    Calculates the scalar reward for the last action. 
    Includes logic to penalize repetitive actions (Stagnation Penalty).
    """
    logs = state["logs"][-1]
    last_action = state["lastAction"]
    step = state["steps"]
    
    # Retrieve the target details captured in execute_action
    last_payload = state.get("actionPayload", {})
    target_details = last_payload.get("targetDetails", {})
    
    # 1. Check for Repetition
    trajectory = state.get("trajectory", [])
    is_repeat = False
    if len(trajectory) > 0:
        prev = trajectory[-1]
        # If agent repeats the exact same high-level action type
        if prev["action"] == last_action and "finish" not in last_action:
            is_repeat = True

    # 2. Use Gemini to Judge the Outcome - Rotate API keys
    global API_KEY_INDEX
    api_key = API_KEYS[API_KEY_INDEX % len(API_KEYS)]
    API_KEY_INDEX += 1
    
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp", # Works with langchain
        api_key=api_key,
        temperature=0.0
    )
    
    current_url = state.get('page').url if state.get('page') else 'unknown'
    
    prompt = f"""
    You are a Security Reward Function evaluating penetration testing actions.
    
    Action: {last_action}
    Log: {logs}
    Is Repeat Action: {is_repeat}
    Current URL: {current_url}
    
    Assign a Reward Score (-1.0 to 2.0):
    
    **SQL INJECTION ON USERS PAGE** (Priority 1):
    - +2.0: Database dump achieved (users with passwords visible)
    - +1.5: Pressed Enter/Submit after SQL injection payload in search box
    - +1.0: SQL injection payload (' OR '1'='1') entered in search box
    - +0.8: Successfully on /users page
    
    **AUTH BYPASS ON LOGIN PAGE** (Priority 2):
    - +2.0: Auth bypass successful (admin access gained)
    - +1.5: Clicked Login after SQL injection in username field
    - +1.0: SQL injection payload (admin' OR '1'='1' --) entered in login form
    - +0.8: Successfully on /login page
    
    **XSS ON CONTACT PAGE** (Priority 3):
    - +1.5: XSS payload submitted successfully
    - +1.0: <script>alert(1)</script> entered in form field
    - +0.5: Successfully on /contact page
    
    **GENERAL ACTIONS**:
    - +0.5: Navigated to new vulnerable page
    - +0.2: Valid navigation action
    - 0.0: Neutral action
    - -0.5: Repeated same action or no progress
    - -1.0: Error or invalid action
    
    Return JSON: {{ "score": float, "reason": "brief explanation" }}
    """
    
    try:
        response = await model.ainvoke(prompt)
        content = str(response.content).replace("```json", "").replace("```", "").strip()
        if "{" in content: content = content[content.find("{"):content.rfind("}")+1]
        
        reward_data = json.loads(content)
        score = float(reward_data.get("score", 0.0))
        reason = reward_data.get("reason", "Unknown")

        # 3. Force Penalty Override
        if is_repeat and score >= 0:
            score = -0.5
            reason = "Forced Penalty: Action Stagnation (Repeated Action)"
            
    except:
        score = 0.0
        reason = "Error parsing reward"

    print(f"💰 REWARD: {score} ({reason})")
    
    # Get current step count
    current_step = state.get("steps", 0)
    
    # Save Experience Tuple (S, A, R) AND THE TARGET IDENTITY
    experience = {
        "step": current_step,
        "action": last_action,
        "target": target_details,  # <--- SAVED FOR EXPLOITER SCRIPT
        "log": logs,
        "reward": score,
        "reason": reason
    }
    
    return {
        "cumulativeReward": state.get("cumulativeReward", 0) + score,
        "stepRewards": state.get("stepRewards", []) + [score],
        "trajectory": state.get("trajectory", []) + [experience]
    }

async def generate_report(state: AgentState) -> dict:
    print("📝 Generating Training Artifacts...")
    
    # 1. Save the RL Dataset (The "Post-Training" Artifact)
    with open("rl_training_data.json", "w") as f:
        json.dump(state["trajectory"], f, indent=2)
        print("✅ Saved rl_training_data.json (Dataset)")

    # 2. Generate Human Report
    reward_chart = "\n".join([f"- Step {i}: **{r}**" for i, r in enumerate(state["stepRewards"])])
    
    report = f"""# Security Gym Training Report
**Date**: {datetime.now()}
**Total Steps**: {state['steps']}
**Cumulative Reward**: {state['cumulativeReward']}

## 📈 Reward Signal (RL Feedback)
The following reward signal was generated by the Automated Reward Model:
{reward_chart}

## 🤖 Execution Log
{chr(10).join([f"- {l}" for l in state['logs']])}

## 📸 Visual State
![Final State]({state['screenshotRefs'][-1] if state['screenshotRefs'] else ''})

*Generated by SecGym Environment*
"""
    # Create qa_reports directory if it doesn't exist
    if not os.path.exists("qa_reports"):
        os.makedirs("qa_reports")
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_filename = f"qa_reports/qa_report_{timestamp}.md"
    
    with open(report_filename, "w") as f:
        f.write(report)
    
    # 3. Generate Python test file with timestamp (in generated_tests folder)
    if not os.path.exists("generated_tests"):
        os.makedirs("generated_tests")
    
    # Extract successful exploits from trajectory
    successful_exploits = [
        step for step in state.get("trajectory", [])
        if step.get("reward", 0) >= 0.5
    ]
    
    if successful_exploits:
        test_code = f'''"""
Auto-generated security tests from QA Agent run
Generated: {datetime.now().isoformat()}
Total Steps: {state['steps']}
Cumulative Reward: {state['cumulativeReward']}
Successful Exploits Found: {len(successful_exploits)}
"""

import pytest
from playwright.sync_api import sync_playwright

TARGET_URL = "{TARGET_URL}"

class TestSecurityVulnerabilities:
    """Auto-generated security tests from successful exploits."""
    
'''
        for i, exploit in enumerate(successful_exploits):
            action = exploit.get("action", "unknown")
            target = exploit.get("target", {})
            log = exploit.get("log", "")
            reward = exploit.get("reward", 0)
            
            test_code += f'''
    def test_exploit_{i+1}_{sanitize(action)}(self):
        """
        Exploit found at step {exploit.get('step', i)}
        Action: {action}
        Reward: {reward}
        Log: {log[:100]}
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(TARGET_URL)
            # TODO: Implement exploit replay
            # Target element: {target.get('outerHTML', 'N/A')[:80]}
            browser.close()
'''
        
        tests_filename = f"generated_tests/generated_tests_{timestamp}.py"
        with open(tests_filename, "w") as f:
            f.write(test_code)
        print(f"✅ Saved {tests_filename}")
    
    if state.get("browser"):
        await state["browser"].close()
        
    return {"logs": ["Training Complete."]}

# --- 4. GRAPH CONSTRUCTION ---
def should_continue(state: AgentState) -> str:
    # Get the last action from the state
    last_action_payload = state.get("actionPayload", {})
    last_action = last_action_payload.get("action", "")
    
    # Check for termination
    if last_action == "finish":
        return "generateReport"
    
    # Check if mission is complete (SQL injection found)
    if state.get("mission_complete", False):
        print("🎯 MISSION COMPLETE: SQL injection successful!")
        return "generateReport"
    
    # Count high-reward findings (vulnerabilities discovered)
    trajectory = state.get("trajectory", [])
    high_reward_count = sum(1 for step in trajectory if step.get("reward", 0) >= 1.0)
    
    # In DEMO_MODE, stop after finding 1 vulnerability for reliability
    # Otherwise, try to find at least 2 vulnerabilities
    min_vulns_for_demo = 1 if DEMO_MODE else 2
    
    if high_reward_count >= min_vulns_for_demo:
        # Check if we've explored enough pages
        visited_vulns = set()
        for step in trajectory:
            if step.get("reward", 0) >= 1.0:
                target = step.get("target", {})
                page_type = "users" if "search" in str(target.get("placeholder", "")).lower() else "login"
                visited_vulns.add(page_type)
        
        # If we found vulns on multiple pages OR reached good count, stop
        if len(visited_vulns) >= min_vulns_for_demo or high_reward_count >= 2:
            print(f"🎯 MISSION COMPLETE: Found {high_reward_count} high-reward vulnerabilities on {len(visited_vulns)} pages!")
            return "generateReport"
    
    # DEMO MODE: Tight step limit for reliable demos
    max_steps = DEMO_MAX_STEPS if DEMO_MODE else 20
    if state.get("steps", 0) >= max_steps:
        print(f"⚠️ Stopping at {max_steps} steps {'(DEMO MODE)' if DEMO_MODE else ''}")
        return "generateReport"
    
    return "executeAction"

def create_workflow():
    workflow = StateGraph(AgentState)

    workflow.add_node("initialize", initialize_browser)
    workflow.add_node("analyze", analyze_and_decide)
    workflow.add_node("executeAction", execute_action)
    workflow.add_node("evaluateReward", evaluate_reward) # <--- REWARD NODE
    workflow.add_node("generateReport", generate_report)

    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "analyze")
    
    # THE LOOP: Analyze -> Execute -> Reward -> Analyze
    workflow.add_conditional_edges(
        "analyze",
        should_continue,
        {
            "executeAction": "executeAction",
            "generateReport": "generateReport"
        }
    )
    workflow.add_edge("executeAction", "evaluateReward")
    workflow.add_edge("evaluateReward", "analyze")
    
    workflow.add_edge("generateReport", END)

    return workflow.compile()

async def main():
    print("🏎️ Starting SecGym Agent (Hybrid Mode: API + Browser)...")
    
    # Phase 0: Run direct API tests first (fast, no browser overhead)
    print("\n" + "="*60)
    print("  PHASE 0: DIRECT API TESTING")
    print("="*60)
    api_findings = await run_direct_api_tests()
    
    # Save API findings to trajectory data
    api_trajectory = api_findings.copy()
    
    # Save API findings immediately (in case browser tests crash)
    if api_trajectory:
        print(f"\n💾 Saving {len(api_trajectory)} API findings...")
        with open("rl_training_data.json", "w") as f:
            json.dump(api_trajectory, f, indent=2)
    
    # Phase 1: Run browser-based RL exploration
    print("\n" + "="*60)
    print("  PHASE 1: BROWSER-BASED RL EXPLORATION")
    print("="*60)
    
    browser_trajectory = []
    try:
        app = create_workflow()
        config = {"recursion_limit": 100}  # Increased from default 25
        result = await app.ainvoke({}, config=config)
        
        # Load browser findings
        try:
            with open("rl_training_data.json", "r") as f:
                browser_trajectory = json.load(f)
                # Filter out API findings (already counted)
                browser_trajectory = [t for t in browser_trajectory if t.get("step") != "api_test"]
        except:
            pass
    except Exception as e:
        print(f"⚠️ Browser exploration failed: {e}")
        print("📊 API findings are still saved.")
    
    # Merge API findings with browser findings
    if api_trajectory or browser_trajectory:
        print(f"\n📊 Merging findings: {len(api_trajectory)} API + {len(browser_trajectory)} browser")
        combined_trajectory = api_trajectory + browser_trajectory
        with open("rl_training_data.json", "w") as f:
            json.dump(combined_trajectory, f, indent=2)
        print(f"✅ Combined trajectory saved: {len(combined_trajectory)} total findings")
    
    print("\n✅ Session Finished. Check 'rl_training_data.json' and reports in 'qa_reports/' folder.")
    
    # Generate executive report
    print("📊 Generating executive report...")
    try:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "executive_report_generator.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            print("✅ Executive report generated successfully!")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ Failed to generate executive report: {result.stderr}")
            if result.stdout:
                print(f"Output: {result.stdout}")
    except Exception as e:
        print(f"❌ Error generating executive report: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())