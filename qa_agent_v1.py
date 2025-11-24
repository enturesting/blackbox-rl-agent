import os
import json
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

# Track API key usage to rotate intelligently
API_KEY_INDEX = 0

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
    browser = await playwright.chromium.launch(
        headless=False,
        args=['--incognito']
    )
    context = await browser.new_context()
    page = await context.new_page()
    
    # CHANGE THIS TO YOUR TARGET URL
    target_url = "http://localhost:5173" 
    try:
        await page.goto(target_url)
        # Ensure we're on the home page, not a cached page
        await page.wait_for_timeout(1000)
        current_url = page.url
        if "/users" in current_url or "/login" in current_url:
            print("📍 Navigating back to home page...")
            await page.goto(target_url)
            await page.wait_for_timeout(1000)
    except Exception as e:
        print(f"Warning: Could not load {target_url}. Make sure server is running.")

    return {
        "browser": browser,
        "page": page,
        "url": target_url,
        "steps": 0,
        "maxSteps": 50,  # Increased to allow reaching Users page
        "logs": ["Started RL Training Session."],
        "cumulativeReward": 0.0,
        "stepRewards": [],
        "trajectory": [],
        "visited_pages": set(),
        "actions_on_page": {}  # Track actions per page to prevent loops
    }
async def analyze_and_decide(state: AgentState) -> dict:
    page = state["page"]
    steps = state["steps"]
    maxSteps = state["maxSteps"]
    logs = state["logs"]
    current_reward = state.get("cumulativeReward", 0.0)

    if steps >= maxSteps:
        return {"lastAction": "finish"}

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

    prompt = f"""
    You are an RL Agent training to find security vulnerabilities and robustness issues.
    
    Current State:
    - URL: {page.url}
    - Steps Taken: {steps}/{maxSteps}
    - Cumulative Reward: {current_reward} (Maximize this!)
    
    {last_move_warning} <--- CRITICAL INSTRUCTION
    
    Interactive Elements:
    {element_list}
    
    Recent Logs:
    {chr(10).join(logs[-3:])}
    
    YOUR GOAL: Maximize your Reward Score.
    CRITICAL MISSION: Navigate to /users page and perform SQL injection to dump all users!
    
    Current URL: {page.url}
    
    IMPORTANT: Follow this exact sequence:
    1. If on home page (localhost:5173): Click "Users" link directly (no login needed!)
    2. If URL contains '/users': 
       - Find the search input box (placeholder: "Enter username to search...")
       - Fill it with: ' OR '1'='1' --
       - Press Enter or click Search button
    3. Look for database results showing multiple users
    4. For UNION attack (full DB dump): Fill search with: ' UNION SELECT * FROM users --
    5. STOP after seeing database dump (you've achieved the goal!)
    
    NOTE: You can go directly to Users page - no login required!
    
    Rewards:
    - +2.0: Database dump on Users page (HIGHEST PRIORITY!)
    - +1.0: SQL injection success, XSS alert
    - +0.5: Reached Users page
    - +0.1: Valid NEW action
    - -0.5: Repeated action
    
    If you see "Results:" or user data on the page, you've succeeded! Choose "finish" action.
    
    Choose your next action. Return ONLY JSON:
    {{
      "action": "fill_input" | "click_element" | "check_responsiveness" | "finish",
      "targetIndex": <number>,
      "actionDetails": "<strategy reasoning>",
      "inputValue": "<test_payload>" 
    }}
    
    (Example payloads: "test<script>alert(1)</script>", "' OR '1'='1", "admin")
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
    current_url = page.url
    
    if action == "finish":
        return {"logs": logs}
    
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

        # Capture State (Screenshot) with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        steps = state.get("steps", 0)
        path = f"qa_screenshots/step_{steps}_{timestamp}.png"
        await page.screenshot(path=path)

    except Exception as e:
        logs.append(f"Error: {str(e)}")
    
    # Pass these details to the next node (Reward Node)
    return {
        "steps": state.get("steps", 0) + 1,  # Increment steps here
        "logs": logs,
        "actions_on_page": actions_on_page,
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
    
    prompt = f"""
    You are a Security Reward Function. Evaluate this action result.
    
    Action: {last_action}
    Log: {logs}
    Is Repeat Action: {is_repeat}
    Current URL: {state.get('page').url if state.get('page') else 'unknown'}
    
    Assign a Reward Score (-1.0 to 2.0):
    - +2.0: Database dump achieved (multiple users with passwords shown on page) - MISSION COMPLETE!
    - +1.5: Pressed Enter after SQL injection in search box on Users page
    - +1.0: SQL injection payload entered in search box on Users page
    - +0.8: Successfully navigated to Users page (/users in URL)
    - +0.5: Clicked Users link in navbar
    - +0.2: Valid navigation action
    - +0.1: Valid action (200 OK) - ONLY IF NEW
    - -0.5: Repeated action or no state change
    - -1.0: Continuing after database dump (mission already complete)
    - 0: Invalid action or error
    
    PRIORITY: SQL injection in Users page search box is CRITICAL for demo!
    
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
    
    if state.get("browser"):
        await state["browser"].close()
        
    return {"logs": ["Training Complete."]}

# --- 4. GRAPH CONSTRUCTION ---
def should_continue(state: AgentState) -> str:
    # Get the last action from the state
    last_action_payload = state.get("actionPayload", {})
    last_action = last_action_payload.get("action", "")
    
    # Check for termination
    if last_action == "finish" or state.get("steps", 0) > 30:
        return "generateReport"
    
    # Check if mission is complete
    if state.get("mission_complete", False):
        return "generateReport"
    
    # Stop if we've done too many steps to avoid quota issues
    if state.get("steps", 0) > 15:
        print("⚠️ Stopping early to avoid quota limits")
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
    print("🏎️ Starting SecGym Agent...")
    app = create_workflow()
    config = {"recursion_limit": 100}  # Increased from default 25
    await app.ainvoke({}, config=config)
    print("✅ Session Finished. Check 'rl_training_data.json' and reports in 'qa_reports/' folder.")
    
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