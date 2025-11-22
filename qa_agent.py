import os
import json
from datetime import datetime
from typing import TypedDict, Annotated, List
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, Page
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


# Define the state of our agent
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


# Helper to sanitize filenames
def sanitize(s: str) -> str:
    return ''.join(c if c.isalnum() else '_' for c in s).lower()


# Node: Initialize Browser
async def initialize_browser(state: AgentState) -> dict:
    print("Initializing browser...")

    # Create screenshots directory if it doesn't exist
    if not os.path.exists("qa_screenshots"):
        os.makedirs("qa_screenshots")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    await page.goto("http://localhost:3000/home")

    return {
        "browser": browser,
        "page": page,
        "url": "http://localhost:3000/home",
        "steps": 0,
        "maxSteps": 10,  # Limit steps to avoid infinite loops
        "logs": ["Started QA session."],
        "visitedUrls": ["http://localhost:3000/home"],
    }


# Node: Analyze Page & Decide Action
async def analyze_and_decide(state: AgentState) -> dict:
    page = state["page"]
    steps = state["steps"]
    maxSteps = state["maxSteps"]
    logs = state["logs"]

    if steps >= maxSteps:
        return {"lastAction": "finish"}

    # 1. Get interactive elements
    buttons = await page.query_selector_all('button, input, a[href], [role="button"], textarea, select')
    elements_info = []

    for i, el in enumerate(buttons):
        try:
            tag_name = await el.evaluate("e => e.tagName.toLowerCase()")
            text = await el.inner_text() if await el.inner_text() else ""
            placeholder = await el.get_attribute('placeholder') or ""
            is_visible = await el.is_visible()
            is_enabled = await el.is_enabled()
            element_id = await el.get_attribute('id') or f"el-{i}"
            element_type = await el.get_attribute('type') or ""

            elements_info.append({
                "index": i,
                "tagName": tag_name,
                "text": text[:30],
                "placeholder": placeholder[:30],
                "type": element_type,
                "isVisible": is_visible,
                "isEnabled": is_enabled,
                "id": element_id
            })
        except Exception as e:
            elements_info.append({
                "index": i,
                "tagName": "unknown",
                "text": "",
                "placeholder": "",
                "type": "",
                "isVisible": False,
                "isEnabled": False,
                "id": f"el-{i}"
            })

    visible_elements = [e for e in elements_info if e["isVisible"] and e["isEnabled"]]

    # 2. Check for obvious issues
    issues = []
    title = await page.title()
    if not title:
        issues.append(f"Page at {page.url} has no title.")

    print(f"Analyzing step {steps}: Found {len(visible_elements)} elements.")

    # 3. Use LLM to decide
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.1,
    )

    element_list = "\n".join([
        f"- Index {e['index']}: <{e['tagName']}>"
        + (f" type=\"{e['type']}\"" if e['type'] else "")
        + (f" text=\"{e['text']}\"" if e['text'] else "")
        + (f" placeholder=\"{e['placeholder']}\"" if e['placeholder'] else "")
        + (f" id=\"{e['id']}\"" if e['id'] and not e['id'].startswith('el-') else "")
        for e in visible_elements
    ])

    prompt = f"""
You are an intelligent QA automation agent testing a website.

Current URL: {page.url}
Page Title: {title}
Current Step: {steps} / {maxSteps}

Interactive Elements Found:
{element_list}

Recent History:
{chr(10).join(logs[-5:])}

Goal: Systematically test the website functionality.
1. First, fill out any input fields you find with realistic test data
2. Then click buttons to submit forms or navigate
3. Test different navigation paths and interactions
4. Every 5 steps, check responsiveness
5. Avoid repeating the same action twice in a row
6. After {maxSteps} steps or when you've tested the main functionality, output "finish"

Return ONLY a valid JSON object (no markdown, no extra text) with this structure:
{{
  "action": "fill_input" | "click_element" | "check_responsiveness" | "finish",
  "targetIndex": <number>,
  "actionDetails": "<brief description>",
  "inputValue": "<value for inputs only>"
}}

Examples:
- For an email input: {{"action": "fill_input", "targetIndex": 2, "actionDetails": "Fill email field", "inputValue": "test@example.com"}}
- For a submit button: {{"action": "click_element", "targetIndex": 5, "actionDetails": "Submit form"}}
- To check responsiveness: {{"action": "check_responsiveness", "targetIndex": 0, "actionDetails": "Test mobile/desktop views"}}
- When done: {{"action": "finish", "targetIndex": 0, "actionDetails": "Testing complete"}}

Return only the JSON:
"""

    try:
        response = await model.ainvoke(prompt)
        # Strip markdown code block if present
        content = str(response.content).replace("```json", "").replace("```", "").strip()

        # Try to extract JSON if there's extra text
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)

        decision = json.loads(content)

        # Validate decision structure
        if "action" not in decision:
            raise ValueError("Missing action in LLM response")

        print(f"LLM Decision: {decision['action']} on index {decision.get('targetIndex', 'N/A')}")

        return {
            "lastAction": decision["action"],
            "actionPayload": {
                "targetIndex": decision.get("targetIndex"),
                "actionDetails": decision.get("actionDetails", ""),
                "inputValue": decision.get("inputValue", "")
            }
        }
    except Exception as e:
        print(f"LLM Error: {str(e)}")
        print(f"Raw response: {e}")
        # Fallback to finish if LLM fails
        return {
            "lastAction": "finish",
            "logs": [f"Error in LLM decision at step {steps}: {str(e)}"]
        }


# Node: Execute Action
async def execute_action(state: AgentState) -> dict:
    page = state["page"]
    last_action = state["lastAction"]
    action_payload = state.get("actionPayload", {})
    steps = state["steps"]
    logs = []
    screenshot_refs = []
    issues = []

    try:
        if last_action == "fill_input":
            elements = await page.query_selector_all('button, input, a[href], [role="button"], textarea, select')
            target_index = action_payload.get("targetIndex")

            if target_index is not None and target_index < len(elements):
                el = elements[target_index]
                val = action_payload.get("inputValue") or "QA Test Input"

                # Check if it's a fillable element
                tag_name = await el.evaluate("e => e.tagName.toLowerCase()")
                if tag_name in ['input', 'textarea']:
                    await el.fill(val)
                    logs.append(f"Step {steps}: Filled {tag_name} at index {target_index} with \"{val}\".")
                else:
                    logs.append(f"Step {steps}: Element at index {target_index} is not fillable ({tag_name})")

                screenshot_path = f"qa_screenshots/step-{steps}-input.png"
                await page.screenshot(path=screenshot_path)
                screenshot_refs.append(screenshot_path)
            else:
                logs.append(f"Step {steps}: Element at index {target_index} not found for fill_input")

        elif last_action == "click_element":
            elements = await page.query_selector_all('button, input, a[href], [role="button"], textarea, select')
            target_index = action_payload.get("targetIndex")

            if target_index is not None and target_index < len(elements):
                el = elements[target_index]
                tag_name = await el.evaluate("e => e.tagName.toLowerCase()")
                logs.append(f"Step {steps}: Clicking <{tag_name}> at index {target_index} - {action_payload.get('actionDetails')}")

                # Take before screenshot
                before_path = f"qa_screenshots/step-{steps}-before-click.png"
                await page.screenshot(path=before_path)
                screenshot_refs.append(before_path)

                await el.click()
                await page.wait_for_timeout(1500)  # Wait for effect

                # Take after screenshot
                after_path = f"qa_screenshots/step-{steps}-after-click.png"
                await page.screenshot(path=after_path)
                screenshot_refs.append(after_path)
            else:
                logs.append(f"Step {steps}: Element at index {target_index} not found for click")

        elif last_action == "check_responsiveness":
            logs.append(f"Step {steps}: Checking responsiveness.")
            # Desktop
            await page.set_viewport_size({"width": 1920, "height": 1080})
            desktop_path = f"qa_screenshots/step-{steps}-desktop.png"
            await page.screenshot(path=desktop_path)
            screenshot_refs.append(desktop_path)

            # Mobile
            await page.set_viewport_size({"width": 375, "height": 667})
            mobile_path = f"qa_screenshots/step-{steps}-mobile.png"
            await page.screenshot(path=mobile_path)
            screenshot_refs.append(mobile_path)

            # Restore
            await page.set_viewport_size({"width": 1280, "height": 720})

    except Exception as error:
        logs.append(f"Step {steps}: Error - {str(error)}")
        issues.append(f"Action failed at step {steps}: {str(error)}")
        print(f"Error in executeAction: {error}")

    return {
        "steps": steps + 1,
        "logs": logs,
        "screenshotRefs": screenshot_refs,
        "issues": issues
    }


# Node: Generate Report
async def generate_report(state: AgentState) -> dict:
    print("Generating report...")
    logs = state["logs"]
    issues = state["issues"]
    screenshot_refs = state["screenshotRefs"]
    visited_urls = state["visitedUrls"]
    steps = state["steps"]

    screenshot_section = "\n".join([
        f"### Screenshot {idx + 1}\n![{s}]({s})\n"
        for idx, s in enumerate(screenshot_refs)
    ]) if screenshot_refs else "No screenshots captured."

    issues_section = "\n".join([
        f"{idx + 1}. {issue}"
        for idx, issue in enumerate(issues)
    ]) if issues else "✅ No critical issues found during testing."

    report_content = f"""# QA Automation Report

**Date**: {datetime.now().strftime('%d/%m/%Y, %I:%M:%S %p')}
**Total Steps**: {steps}
**Pages Visited**: {len(visited_urls)}

---

## 📊 Summary

- **Visited URLs**:
{chr(10).join([f"  - {url}" for url in visited_urls])}
- **Total Actions Performed**: {steps}
- **Screenshots Captured**: {len(screenshot_refs)}
- **Issues Found**: {len(issues)}

---

## 🔍 Issues Detected

{issues_section}

---

## 📝 Execution Log

{chr(10).join([f"{idx + 1}. {log}" for idx, log in enumerate(logs)])}

---

## 📸 Screenshots

{screenshot_section}

---

## 🎯 Test Coverage

- Form Inputs: {len([l for l in logs if 'Filled input' in l or 'Filled' in l])} tested
- Button Clicks: {len([l for l in logs if 'Clicking' in l])} tested
- Responsiveness Checks: {len([l for l in logs if 'responsiveness' in l])} tested

---

*Generated by QA Agent*
"""

    with open("qa_report.md", "w") as f:
        f.write(report_content)

    if state.get("browser"):
        await state["browser"].close()

    return {"logs": ["Report generated and saved to qa_report.md"]}


# Conditional Edge Logic
def should_continue(state: AgentState) -> str:
    if state.get("lastAction") == "finish":
        return "generateReport"
    return "executeAction"


# Build Graph
def create_workflow():
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("initialize", initialize_browser)
    workflow.add_node("analyze", analyze_and_decide)
    workflow.add_node("executeAction", execute_action)
    workflow.add_node("generateReport", generate_report)

    # Add edges
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "analyze")
    workflow.add_conditional_edges(
        "analyze",
        should_continue,
        {
            "executeAction": "executeAction",
            "generateReport": "generateReport"
        }
    )
    workflow.add_edge("executeAction", "analyze")
    workflow.add_edge("generateReport", END)

    return workflow.compile()


# Run if called directly
async def main():
    print("Starting QA Agent...")
    app = create_workflow()
    final_state = await app.ainvoke({})
    print("QA Agent Finished. Report saved to qa_report.md")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

