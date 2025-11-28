"""
AI Security Testing Suite - Backend Server
FastAPI server for the dashboard UI with full pipeline support
"""
import os
import json
import asyncio
import shutil
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import glob
import time
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="AI Security Testing Suite",
    description="Backend API for AI-powered penetration testing dashboard",
    version="1.0.0"
)

# Enable CORS for React dev server
# Dashboard runs on 3000, buggy-vibe target runs on 5173
# Also allow GitHub Codespaces URLs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Codespace compatibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log file path
LOG_FILE = "agent_logs.jsonl"

# Pipeline state tracking
pipeline_state = {
    "current_phase": None,
    "phases_completed": [],
    "is_running": False,
    "start_time": None,
    "target_url": os.getenv("TARGET_URL", "http://localhost:5173")
}


def clear_logs():
    """Clear the log file"""
    with open(LOG_FILE, "w") as f:
        f.write("")


def append_log(log_type: str, message: str, script: str = "system", phase: str = None):
    """Append a log entry to the log file"""
    with open(LOG_FILE, "a", buffering=1) as f:  # line-buffered
        entry = {
            "type": log_type,
            "script": script,
            "message": message,
            "timestamp": time.time(),
        }
        if phase:
            entry["phase"] = phase
        f.write(json.dumps(entry) + "\n")
        f.flush()
        os.fsync(f.fileno())  # flush OS buffers


@app.get("/api/logs")
async def get_logs(since: float = 0):
    """Get logs since a given timestamp"""
    logs = []

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        log = json.loads(line)
                        if log.get("timestamp", 0) > since:
                            logs.append(log)
                    except Exception:
                        pass

    return {"logs": logs}


@app.get("/api/pipeline/status")
async def get_pipeline_status():
    """Get the current pipeline status"""
    return pipeline_state


async def run_script_with_logs(script_name: str, phase: str, *args):
    """Run a Python script and stream its output to the log file"""
    append_log("status", "starting", script_name, phase)
    
    env = os.environ.copy()
    env["TARGET_URL"] = pipeline_state["target_url"]
    env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output
    
    process = await asyncio.create_subprocess_exec(
        "python", "-u", script_name, *args,  # -u for unbuffered
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env
    )
    
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        message = line.decode().strip()
        if message:
            append_log("log", message, script_name, phase)
    
    await process.wait()
    
    status = "completed" if process.returncode == 0 else "failed"
    append_log("status", status, script_name, phase)
    
    return process.returncode


@app.post("/api/run/full-pipeline")
async def run_full_pipeline(target_url: str = None, demo_mode: bool = False):
    """Run the complete security testing pipeline"""
    global pipeline_state
    
    if pipeline_state["is_running"]:
        return {"error": "Pipeline already running", "status": "busy"}
    
    # Update target URL if provided
    if target_url:
        pipeline_state["target_url"] = target_url
    
    # Set demo mode environment variable for child processes
    if demo_mode or os.getenv("DEMO_MODE", "false").lower() == "true":
        os.environ["DEMO_MODE"] = "true"
        append_log("status", "🎬 DEMO MODE enabled - optimized for reliable demonstration", "pipeline", "init")
    
    pipeline_state["is_running"] = True
    pipeline_state["phases_completed"] = []
    pipeline_state["start_time"] = time.time()
    
    clear_logs()
    append_log("status", f"🚀 Starting full pipeline against {pipeline_state['target_url']}", "pipeline", "init")
    
    phases = [
        ("recon", "qa_agent_v1.py", "🔍 Reconnaissance - Scanning target for vulnerabilities"),
        ("plan", "exploit_planner.py", "🎯 Planning - Generating exploit strategies"),
        ("attack", "attack.py", "⚔️ Attack - Executing exploits"),
        ("analyze", "gemini_coderabbit_analyzer.py", "🔬 Analysis - Deep code analysis"),
        ("report", "executive_report_generator.py", "📊 Reporting - Generating executive summary"),
    ]
    
    results = {}
    
    for phase_name, script, description in phases:
        pipeline_state["current_phase"] = phase_name
        append_log("phase", description, "pipeline", phase_name)
        
        # Check if script exists
        if not os.path.exists(script):
            append_log("warning", f"⚠️ Script {script} not found, skipping", "pipeline", phase_name)
            results[phase_name] = "skipped"
            continue
        
        # Check prerequisites
        if phase_name == "plan" and not os.path.exists("rl_training_data.json"):
            append_log("warning", "⚠️ No training data found, skipping exploit planning", "pipeline", phase_name)
            results[phase_name] = "skipped"
            continue
            
        if phase_name == "attack" and not os.path.exists("final_exploit_plan.json"):
            append_log("warning", "⚠️ No exploit plan found, skipping attack phase", "pipeline", phase_name)
            results[phase_name] = "skipped"
            continue
        
        returncode = await run_script_with_logs(script, phase_name)
        
        if returncode == 0:
            pipeline_state["phases_completed"].append(phase_name)
            results[phase_name] = "completed"
        else:
            results[phase_name] = "failed"
            append_log("error", f"❌ Phase {phase_name} failed with code {returncode}", "pipeline", phase_name)
            # Continue to next phase even if one fails
    
    pipeline_state["is_running"] = False
    pipeline_state["current_phase"] = None
    
    duration = time.time() - pipeline_state["start_time"]
    append_log("status", f"✅ Pipeline completed in {duration:.1f}s", "pipeline", "complete")
    
    return {
        "status": "completed",
        "results": results,
        "duration": duration,
        "phases_completed": pipeline_state["phases_completed"]
    }


@app.post("/api/run/recon")
async def run_recon(target_url: str = None):
    """Run the QA Agent (Reconnaissance phase)"""
    global pipeline_state
    
    if target_url:
        pipeline_state["target_url"] = target_url
    
    clear_logs()
    append_log("phase", f"🔍 Starting reconnaissance against {pipeline_state['target_url']}", "pipeline", "recon")
    
    returncode = await run_script_with_logs("qa_agent_v1.py", "recon")
    
    return {"status": "completed" if returncode == 0 else "failed"}


@app.post("/api/run/plan")
async def run_plan():
    """Run the Exploit Planner"""
    if not os.path.exists("rl_training_data.json"):
        return {"error": "No training data found. Run recon first.", "status": "failed"}
    
    append_log("phase", "🎯 Starting exploit planning", "pipeline", "plan")
    returncode = await run_script_with_logs("exploit_planner.py", "plan")
    
    return {"status": "completed" if returncode == 0 else "failed"}


@app.post("/api/run/attack")
async def run_attack():
    """Run the Attack Execution"""
    if not os.path.exists("final_exploit_plan.json"):
        return {"error": "No exploit plan found. Run plan first.", "status": "failed"}
    
    append_log("phase", "⚔️ Starting attack execution", "pipeline", "attack")
    returncode = await run_script_with_logs("attack.py", "attack")
    
    return {"status": "completed" if returncode == 0 else "failed"}


@app.post("/api/run/analyze")
async def run_analyze():
    """Run the Gemini/CodeRabbit Analyzer"""
    append_log("phase", "🔬 Starting code analysis", "pipeline", "analyze")
    returncode = await run_script_with_logs("gemini_coderabbit_analyzer.py", "analyze")
    
    return {"status": "completed" if returncode == 0 else "failed"}


@app.post("/api/run/report")
async def run_report():
    """Run the Executive Report Generator"""
    append_log("phase", "📊 Generating executive report", "pipeline", "report")
    returncode = await run_script_with_logs("executive_report_generator.py", "report")
    
    return {"status": "completed" if returncode == 0 else "failed"}


@app.get("/api/vulnerabilities")
async def get_vulnerabilities():
    """Get the list of found vulnerabilities from rl_training_data.json"""
    try:
        if os.path.exists("rl_training_data.json"):
            with open("rl_training_data.json", "r") as f:
                data = json.load(f)
                # Filter for high-reward items (likely vulnerabilities)
                vulns = [item for item in data if item.get("reward", 0) >= 0.5]
                return {"vulnerabilities": vulns, "total": len(vulns)}
        return {"vulnerabilities": [], "total": 0}
    except Exception as e:
        return {"error": str(e), "vulnerabilities": [], "total": 0}


@app.get("/api/exploits")
async def get_exploits():
    """Get the generated exploit plans"""
    try:
        if os.path.exists("final_exploit_plan.json"):
            with open("final_exploit_plan.json", "r") as f:
                data = json.load(f)
                exploits = data.get("exploits", [])
                return {"exploits": exploits, "total": len(exploits)}
        return {"exploits": [], "total": 0}
    except Exception as e:
        return {"error": str(e), "exploits": [], "total": 0}


@app.get("/api/report")
async def get_report():
    """Get the latest executive report"""
    try:
        reports_dir = "qa_reports"
        if os.path.exists(reports_dir):
            reports = glob.glob(f"{reports_dir}/executive_report_*.md")
            if reports:
                latest = max(reports, key=os.path.getmtime)
                with open(latest, "r") as f:
                    return {
                        "report": f.read(),
                        "filename": os.path.basename(latest),
                        "generated_at": os.path.getmtime(latest)
                    }
        return {"report": None, "message": "No executive report found"}
    except Exception as e:
        return {"error": str(e), "report": None}


@app.get("/api/evidence")
async def get_evidence():
    """Get attack evidence (screenshots and videos)"""
    evidence = {
        "screenshots": [],
        "qa_screenshots": [],
        "videos": []
    }
    
    # Get QA screenshots
    if os.path.exists("qa_screenshots"):
        screenshots = glob.glob("qa_screenshots/*.png")
        evidence["qa_screenshots"] = sorted([os.path.basename(s) for s in screenshots])
    
    # Get attack evidence screenshots
    if os.path.exists("attack_evidence"):
        screenshots = glob.glob("attack_evidence/*.png")
        evidence["screenshots"] = [os.path.basename(s) for s in screenshots]
    
    # Get videos
    if os.path.exists("attack_videos"):
        videos = glob.glob("attack_videos/*.webm")
        evidence["videos"] = [os.path.basename(v) for v in videos]
    
    return evidence


@app.get("/api/evidence/screenshot/{folder}/{filename}")
async def get_screenshot(folder: str, filename: str):
    """Serve a specific screenshot"""
    # Sanitize folder to prevent directory traversal
    if folder not in ["qa_screenshots", "attack_evidence"]:
        return {"error": "Invalid folder"}
    
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "File not found"}


@app.get("/api/stats")
async def get_stats():
    """Get overall statistics"""
    stats = {
        "total_vulnerabilities": 0,
        "total_exploits": 0,
        "success_rate": 0,
        "target_url": pipeline_state["target_url"],
        "is_running": pipeline_state["is_running"],
        "current_phase": pipeline_state["current_phase"],
        "phases_completed": pipeline_state["phases_completed"],
    }
    
    # Count vulnerabilities
    if os.path.exists("rl_training_data.json"):
        try:
            with open("rl_training_data.json", "r") as f:
                data = json.load(f)
                stats["total_vulnerabilities"] = len([item for item in data if item.get("reward", 0) >= 0.5])
                stats["total_actions"] = len(data)
        except:
            pass
    
    # Count exploits
    if os.path.exists("final_exploit_plan.json"):
        try:
            with open("final_exploit_plan.json", "r") as f:
                data = json.load(f)
                stats["total_exploits"] = len(data.get("exploits", []))
        except:
            pass
    
    # Check for executive report
    if os.path.exists("qa_reports"):
        reports = glob.glob("qa_reports/executive_report_*.md")
        stats["has_report"] = len(reports) > 0
    else:
        stats["has_report"] = False
    
    return stats


@app.post("/api/reset")
async def reset_artifacts():
    """Clear all generated artifacts for a fresh run"""
    global pipeline_state
    
    if pipeline_state["is_running"]:
        return {"error": "Cannot reset while pipeline is running", "status": "busy"}
    
    files_to_remove = [
        "final_exploit_plan.json",
        "rl_training_data.json",
        "qa_report.md",
        "mission_log.md",
        "agent_logs.jsonl",
    ]
    
    dirs_to_remove = [
        "attack_evidence",
        "attack_videos",
        "qa_screenshots",
        "qa_reports",
    ]
    
    removed = []
    
    # Remove files
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            removed.append(file)
    
    # Remove directories
    for dir_path in dirs_to_remove:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            removed.append(dir_path)
    
    # Reset pipeline state
    pipeline_state["phases_completed"] = []
    pipeline_state["current_phase"] = None
    pipeline_state["start_time"] = None
    
    append_log("status", f"🗑️ Reset complete. Removed: {', '.join(removed)}", "system", "reset")
    
    return {"status": "success", "removed": removed}


@app.post("/api/config/target")
async def set_target_url(target_url: str):
    """Set the target URL for testing"""
    global pipeline_state
    pipeline_state["target_url"] = target_url
    return {"status": "success", "target_url": target_url}


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "target_url": pipeline_state["target_url"],
        "api_keys_loaded": len([k for k in os.environ.keys() if k.startswith("GOOGLE_API_KEY")]),
    }


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


# =============================================================================
# ORCHESTRATOR ENDPOINTS
# =============================================================================

@app.get("/api/orchestrator/state")
async def get_orchestrator_state():
    """Get the current orchestrator state (CEO/CTO coordination)"""
    state_file = "orchestrator_state.json"
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return {"status": "not_started", "message": "Orchestrator not running"}


@app.get("/api/orchestrator/events")
async def get_orchestrator_events(since: int = 0):
    """Get orchestrator events for live updates"""
    events_file = "orchestrator_events.json"
    if os.path.exists(events_file):
        with open(events_file, "r") as f:
            events = json.load(f)
            # Filter to events after 'since' index
            return {"events": events[since:], "total": len(events)}
    return {"events": [], "total": 0}


@app.post("/api/orchestrator/start")
async def start_orchestrator(target_url: str = None, max_iterations: int = 10):
    """Start the CEO/CTO orchestrator loop"""
    global pipeline_state
    
    if pipeline_state["is_running"]:
        return {"error": "Pipeline already running", "status": "busy"}
    
    # Update target URL if provided
    if target_url:
        pipeline_state["target_url"] = target_url
        os.environ["TARGET_URL"] = target_url
    
    append_log("status", "🎭 Starting CEO/CTO Orchestrator", "orchestrator", "init")
    
    # Run orchestrator in background
    env = os.environ.copy()
    env["TARGET_URL"] = pipeline_state["target_url"]
    env["PYTHONUNBUFFERED"] = "1"
    
    process = await asyncio.create_subprocess_exec(
        "python", "-u", "orchestrator.py",
        "--non-interactive",
        f"--max-iterations={max_iterations}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env
    )
    
    # Stream output to logs
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        message = line.decode().strip()
        if message:
            append_log("orchestrator", message, "orchestrator", "running")
    
    await process.wait()
    
    return {"status": "completed", "returncode": process.returncode}


@app.post("/api/orchestrator/feedback")
async def submit_human_feedback(feedback: str):
    """Submit human feedback to the orchestrator"""
    state_file = "orchestrator_state.json"
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            state = json.load(f)
        state["human_feedback"] = feedback
        state["last_updated"] = datetime.now().isoformat()
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        return {"status": "success", "feedback": feedback}
    return {"error": "Orchestrator not running"}


@app.post("/api/orchestrator/approve")
async def approve_demo():
    """Human approves the demo as ready"""
    state_file = "orchestrator_state.json"
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            state = json.load(f)
        state["human_approved"] = True
        state["pitch_ready"] = True
        state["status"] = "pitch_ready"
        state["last_updated"] = datetime.now().isoformat()
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        return {"status": "success", "message": "Demo approved!"}
    return {"error": "Orchestrator not running"}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Security Testing Suite API Server")
    print(f"📍 Target URL: {pipeline_state['target_url']}")
    print("📡 API available at http://localhost:8000")
    print("📊 Dashboard should connect from http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
