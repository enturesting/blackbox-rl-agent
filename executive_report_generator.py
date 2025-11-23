import os
import sys
import json
from datetime import datetime
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def find_latest_qa_report():
    """Find the most recent qa_report file"""
    reports_dir = Path("qa_reports")
    if not reports_dir.exists():
        print("❌ No qa_reports directory found")
        return None
    
    reports = list(reports_dir.glob("qa_report_*.md"))
    if not reports:
        print("❌ No QA reports found")
        return None
    
    # Sort by modification time and get the latest
    latest_report = max(reports, key=lambda p: p.stat().st_mtime)
    return latest_report

def analyze_screenshots():
    """Analyze the latest screenshots to understand what vulnerabilities were found"""
    screenshots_dir = Path("qa_screenshots")
    if not screenshots_dir.exists():
        return []
    
    # Get latest run screenshots (based on timestamp)
    screenshots = list(screenshots_dir.glob("*.png"))
    if not screenshots:
        return []
    
    # Group by timestamp (last part of filename)
    latest_time = max(s.stem.split('_')[-2:] for s in screenshots)
    latest_screenshots = [s for s in screenshots if s.stem.endswith(f"{latest_time[0]}_{latest_time[1]}")]
    
    return sorted(latest_screenshots)

def generate_executive_report(qa_report_path):
    """Convert technical QA report into executive-friendly security assessment"""
    
    # Read the QA report
    with open(qa_report_path, 'r') as f:
        qa_report = f.read()
    
    # Initialize Gemini
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.3,
    )
    
    prompt = f"""
    You are a cybersecurity expert creating an executive report for C-level executives and security managers.
    
    Based on this automated security testing report, create a professional executive summary that includes:
    
    1. **Executive Summary** (2-3 sentences for C-suite)
    2. **Critical Findings** (bullet points with business impact)
    3. **Risk Assessment** (High/Medium/Low with justification)
    4. **Business Impact** (potential consequences if not addressed)
    5. **Recommended Actions** (prioritized, actionable steps)
    6. **Technical Details** (brief summary for security team)
    
    Focus on SQL injection vulnerabilities found, especially on the Users page that could expose customer data.
    
    QA Report:
    {qa_report}
    
    Key findings from the test:
    - The AI agent successfully bypassed login authentication using SQL injection
    - The agent navigated to the Users page and found SQL injection vulnerability in search
    - The vulnerability allows dumping the entire user database including passwords
    - This is a CRITICAL security issue that exposes all customer data
    
    Format the report professionally with clear sections and bullet points.
    Make it actionable and emphasize the business risks of data breach, GDPR violations, and reputation damage.
    """
    
    try:
        response = model.invoke(prompt)
        executive_report = response.content
        
        # Save the executive report
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        exec_report_path = f"qa_reports/executive_report_{timestamp}.md"
        
        with open(exec_report_path, 'w') as f:
            f.write(f"# Security Assessment Executive Report\n")
            f.write(f"**Generated**: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n")
            f.write(f"**Application**: BuggyVibe Web Application\n")
            f.write(f"**Testing Method**: Automated AI Security Testing\n\n")
            f.write("---\n\n")
            f.write(executive_report)
            f.write("\n\n---\n")
            f.write(f"*This report was automatically generated from security testing performed on {datetime.now().strftime('%Y-%m-%d')}*\n")
        
        print(f"✅ Executive report generated: {exec_report_path}")
        return exec_report_path
        
    except Exception as e:
        print(f"❌ Error generating executive report: {e}")
        return None

def main():
    """Main function to generate executive report from latest QA report"""
    print("🔍 Finding latest QA report...")
    
    latest_report = find_latest_qa_report()
    if not latest_report:
        return
    
    print(f"📄 Found report: {latest_report}")
    
    print("📊 Generating executive report...")
    exec_report = generate_executive_report(latest_report)
    
    if exec_report:
        print(f"\n✨ Executive report ready for C-level review!")
        print(f"📍 Location: {exec_report}")
        
        # Also display the report
        with open(exec_report, 'r') as f:
            print("\n" + "="*60)
            print(f.read())
            print("="*60)

if __name__ == "__main__":
    main()
