import os
import json
from datetime import datetime
from typing import TypedDict, Annotated, List, Dict, Any
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, Page
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

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
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    
    target_url = "https://strandschat.com" # CHANGE THIS TO YOUR TARGET
    try:
        await page.goto(target_url)
    except Exception as e:
        print(f"Warning: Could not load {target_url}. Make sure server is running.")

    return {
        "browser": browser,
        "page": page,
        "url": target_url,
        "steps": 0,
        "maxSteps": 15, # Increased steps to allow for exploration
        "logs": ["Started RL Training Session."],
        "visitedUrls": [target_url],
        # Initialize RL State
        "cumulativeReward": 0.0,
        "stepRewards": [],
        "trajectory": []
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
                # Get placeholder or text to help the LLM identify the element
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

    # 3. The Policy Model (Gemini)
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp", # Or gemini-1.5-pro
        api_key=os.getenv("GOOGLE_API_KEY"),
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
    - +1.0: Cause Server Error (500), Crash, SQLi success, XSS Alert.
    - +0.1: Valid, NEW interaction (200 OK).
    - -0.5: STAGNATION (Repeating the same action).
    - -1.0: Failed action (Element not found).
    
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
        return {"lastAction": "finish"}

async def execute_action(state: AgentState) -> dict:
    page = state["page"]
    action = state["lastAction"]
    payload = state.get("actionPayload", {})
    steps = state["steps"]
    logs = []
    screenshot_refs = []
    
    try:
        if action == "fill_input":
            idx = payload.get("targetIndex")
            val = payload.get("inputValue", "test")
            elements = await page.query_selector_all('button, input, textarea, select')
            if idx < len(elements):
                await elements[idx].fill(val)
                logs.append(f"Action: Filled index {idx} with '{val}'")
                
        elif action == "click_element":
            idx = payload.get("targetIndex")
            elements = await page.query_selector_all('button, input, a[href], [role="button"]')
            if idx < len(elements):
                await elements[idx].click()
                logs.append(f"Action: Clicked index {idx}")
                await page.wait_for_timeout(1000) # Wait for reaction

        elif action == "check_responsiveness":
            logs.append("Action: Checked Responsiveness")
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.wait_for_timeout(500)
            await page.set_viewport_size({"width": 1280, "height": 800})

        # Capture State (Screenshot)
        path = f"qa_screenshots/step_{steps}.png"
        await page.screenshot(path=path)
        screenshot_refs.append(path)

    except Exception as e:
        logs.append(f"Error: {str(e)}")
    
    return {
        "steps": steps + 1,
        "logs": logs,
        "screenshotRefs": screenshot_refs
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
    
    # 1. Check for Repetition
    trajectory = state.get("trajectory", [])
    is_repeat = False
    if len(trajectory) > 0:
        prev = trajectory[-1]
        # If agent repeats the exact same high-level action type
        if prev["action"] == last_action and "finish" not in last_action:
            # We can also check if payload targetIndex is same for stricter checking
            is_repeat = True

    # 2. Use Gemini to Judge the Outcome
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp", 
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.0
    )
    
    prompt = f"""
    You are a Security Reward Function. Evaluate this action result.
    
    Action: {last_action}
    Log: {logs}
    Is Repeat Action: {is_repeat}
    
    Assign a Reward Score (-1.0 to 1.0):
    - 1.0: Critical Success (Found 500 Error, Crash, SQLi, XSS).
    - 0.5: Robustness Warning (404, Broken UI, Lag).
    - 0.1: Standard Valid Action (200 OK) - ONLY IF NEW.
    - -0.5: STAGNATION (Repeated action or no state change).
    - -1.0: Script Error / Failed Action.
    
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
        # Sometimes LLMs are too nice. We force the penalty if it's a repeat.
        if is_repeat and score >= 0:
            score = -0.5
            reason = "Forced Penalty: Action Stagnation (Repeated Action)"
            
    except:
        score = 0.0
        reason = "Error parsing reward"

    print(f"💰 REWARD: {score} ({reason})")
    
    # Save Experience Tuple (S, A, R)
    experience = {
        "step": step,
        "action": last_action,
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
    with open("qa_report.md", "w") as f:
        f.write(report)
    
    if state.get("browser"):
        await state["browser"].close()
        
    return {"logs": ["Training Complete."]}

# --- 4. GRAPH CONSTRUCTION ---
def should_continue(state: AgentState) -> str:
    if state.get("lastAction") == "finish":
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
    await app.ainvoke({})
    print("✅ Session Finished. Check 'rl_training_data.json' and 'qa_report.md'.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())