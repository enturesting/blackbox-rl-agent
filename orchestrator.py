#!/usr/bin/env python3
"""
CEO-CTO Agent Orchestrator

Coordinates the CEO (vision/narrative) and CTO (technical) agents
to iterate on the demo until it's pitch-ready.

Flow:
1. CTO validates/fixes the technical implementation
2. QA agent runs against target app
3. Results streamed to frontend
4. CEO evaluates demo readiness
5. Human checkpoint for feedback
6. Loop until CEO says "pitch-ready"
"""

import os
import sys
import json
import time
import subprocess
import signal
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


class AgentRole(Enum):
    CEO = "ceo"
    CTO = "cto"
    QA = "qa"
    HUMAN = "human"


class DemoStatus(Enum):
    NOT_STARTED = "not_started"
    CTO_WORKING = "cto_working"
    QA_RUNNING = "qa_running"
    CEO_REVIEWING = "ceo_reviewing"
    AWAITING_HUMAN = "awaiting_human"
    PITCH_READY = "pitch_ready"
    FAILED = "failed"


@dataclass
class Finding:
    """A vulnerability or bug found by the QA agent"""
    id: str
    type: str  # xss, sqli, auth_bypass, etc.
    severity: str  # critical, high, medium, low
    description: str
    evidence: str
    timestamp: str
    
    
@dataclass 
class OrchestratorState:
    """Shared state between all agents"""
    status: DemoStatus = DemoStatus.NOT_STARTED
    iteration: int = 0
    max_iterations: int = 10
    
    # CTO tracking
    cto_issues_found: List[str] = None
    cto_issues_fixed: List[str] = None
    services_healthy: Dict[str, bool] = None
    
    # QA tracking
    findings: List[Finding] = None
    qa_runs_completed: int = 0
    
    # CEO tracking
    demo_readiness_score: int = 0  # 0-100
    ceo_feedback: str = ""
    pitch_ready: bool = False
    
    # Human tracking
    human_feedback: str = ""
    human_approved: bool = False
    
    # Timestamps
    started_at: str = ""
    last_updated: str = ""
    
    def __post_init__(self):
        self.cto_issues_found = self.cto_issues_found or []
        self.cto_issues_fixed = self.cto_issues_fixed or []
        self.services_healthy = self.services_healthy or {}
        self.findings = self.findings or []
        self.started_at = datetime.now().isoformat()
        self.last_updated = self.started_at
        
    def to_dict(self) -> dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d
    
    def save(self, path: str = "orchestrator_state.json"):
        """Save state to file for frontend to read"""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        self.last_updated = datetime.now().isoformat()
        
    @classmethod
    def load(cls, path: str = "orchestrator_state.json") -> 'OrchestratorState':
        """Load state from file"""
        if not Path(path).exists():
            return cls()
        with open(path, 'r') as f:
            data = json.load(f)
        data['status'] = DemoStatus(data['status'])
        data['findings'] = [Finding(**f) for f in data.get('findings', [])]
        return cls(**data)


class Orchestrator:
    """
    Main orchestrator that coordinates CEO, CTO, and QA agents.
    """
    
    def __init__(self, interactive: bool = True):
        self.state = OrchestratorState()
        self.interactive = interactive
        self.processes: Dict[str, subprocess.Popen] = {}
        self.state_file = "orchestrator_state.json"
        
        # Paths
        self.root = Path(__file__).parent
        self.target_app = self.root / "target-apps" / "buggy-vibe"
        self.frontend = self.root / "frontend"
        
    def log(self, role: AgentRole, message: str):
        """Log with role prefix and update state file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            AgentRole.CEO: "🎯 CEO",
            AgentRole.CTO: "🔧 CTO",
            AgentRole.QA: "🔍 QA ",
            AgentRole.HUMAN: "👤 YOU",
        }[role]
        print(f"[{timestamp}] {prefix}: {message}")
        self.state.save(self.state_file)
        
    def broadcast_update(self, event_type: str, data: dict):
        """
        Broadcast update to frontend.
        In production, this would use WebSocket/SSE.
        For now, we update a JSON file the frontend can poll.
        """
        update = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "state": self.state.to_dict()
        }
        
        # Append to event log
        log_file = self.root / "orchestrator_events.json"
        events = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    events = json.load(f)
            except:
                events = []
        events.append(update)
        # Keep last 100 events
        events = events[-100:]
        with open(log_file, 'w') as f:
            json.dump(events, f, indent=2, default=str)
            
    # -------------------------------------------------------------------------
    # Service Management
    # -------------------------------------------------------------------------
    
    def start_service(self, name: str, cmd: List[str], cwd: Path) -> bool:
        """Start a background service"""
        try:
            self.log(AgentRole.CTO, f"Starting {name}...")
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            time.sleep(2)  # Give it time to start
            
            if process.poll() is not None:
                # Process already exited - something went wrong
                stderr = process.stderr.read().decode() if process.stderr else ""
                self.log(AgentRole.CTO, f"❌ {name} failed to start: {stderr[:200]}")
                self.state.services_healthy[name] = False
                return False
                
            self.processes[name] = process
            self.state.services_healthy[name] = True
            self.log(AgentRole.CTO, f"✅ {name} started (PID: {process.pid})")
            return True
            
        except Exception as e:
            self.log(AgentRole.CTO, f"❌ {name} failed: {e}")
            self.state.services_healthy[name] = False
            return False
            
    def stop_all_services(self):
        """Stop all running services"""
        for name, process in self.processes.items():
            try:
                if os.name != 'nt':
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                self.log(AgentRole.CTO, f"Stopped {name}")
            except:
                pass
        self.processes.clear()
        
    def check_service_health(self, name: str, url: str) -> bool:
        """Check if a service is responding"""
        import urllib.request
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except:
            return False
            
    # -------------------------------------------------------------------------
    # CTO Agent Functions
    # -------------------------------------------------------------------------
    
    def cto_validate_environment(self) -> bool:
        """CTO: Check that all prerequisites are met"""
        self.log(AgentRole.CTO, "Validating environment...")
        issues = []
        
        # Check API keys
        api_keys = [k for k in os.environ if k.startswith("GOOGLE_API_KEY")]
        if not api_keys:
            issues.append("No GOOGLE_API_KEY found in environment")
        else:
            self.log(AgentRole.CTO, f"✅ Found {len(api_keys)} API key(s)")
            
        # Check target app exists
        if not (self.target_app / "package.json").exists():
            issues.append(f"Target app not found at {self.target_app}")
        else:
            self.log(AgentRole.CTO, "✅ Target app (buggy-vibe) found")
            
        # Check QA agent exists
        if not (self.root / "qa_agent_v1.py").exists():
            issues.append("qa_agent_v1.py not found")
        else:
            self.log(AgentRole.CTO, "✅ QA agent found")
            
        # Check frontend exists
        if not (self.frontend / "package.json").exists():
            issues.append(f"Frontend not found at {self.frontend}")
        else:
            self.log(AgentRole.CTO, "✅ Frontend found")
            
        self.state.cto_issues_found.extend(issues)
        
        if issues:
            for issue in issues:
                self.log(AgentRole.CTO, f"❌ {issue}")
            return False
            
        return True
        
    def cto_start_services(self) -> bool:
        """CTO: Start all required services"""
        self.log(AgentRole.CTO, "Starting services...")
        self.state.status = DemoStatus.CTO_WORKING
        self.broadcast_update("cto_starting_services", {})
        
        success = True
        
        # 1. Start target app (buggy-vibe)
        if not self.start_service(
            "buggy-vibe",
            ["npm", "run", "dev"],
            self.target_app
        ):
            success = False
            
        # 2. Start frontend
        if not self.start_service(
            "frontend", 
            ["npm", "run", "dev"],
            self.frontend
        ):
            success = False
            
        # 3. Start backend server
        if not self.start_service(
            "backend",
            ["python", "server.py"],
            self.root
        ):
            success = False
            
        # Wait for services to be ready
        time.sleep(3)
        
        # Health checks
        health_checks = [
            ("buggy-vibe", "http://localhost:5173"),
            ("frontend", "http://localhost:5174"),  # Adjust port as needed
            ("backend", "http://localhost:8000"),
        ]
        
        for name, url in health_checks:
            healthy = self.check_service_health(name, url)
            self.state.services_healthy[name] = healthy
            if healthy:
                self.log(AgentRole.CTO, f"✅ {name} responding at {url}")
            else:
                self.log(AgentRole.CTO, f"⚠️ {name} not responding at {url}")
                
        self.broadcast_update("services_started", self.state.services_healthy)
        return success
        
    def cto_run_qa_agent(self) -> List[Finding]:
        """CTO: Run the QA agent against the target app"""
        self.log(AgentRole.CTO, "Running QA agent against buggy-vibe...")
        self.state.status = DemoStatus.QA_RUNNING
        self.broadcast_update("qa_started", {})
        
        findings = []
        
        try:
            # Run QA agent with timeout
            result = subprocess.run(
                ["python", "qa_agent_v1.py"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                env={**os.environ, "DEMO_MODE": "true"}
            )
            
            self.log(AgentRole.QA, f"QA agent completed with code {result.returncode}")
            
            # Parse findings from output or results file
            results_file = self.root / "qa_results.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    data = json.load(f)
                    for i, vuln in enumerate(data.get('vulnerabilities', [])):
                        finding = Finding(
                            id=f"VULN-{i+1:03d}",
                            type=vuln.get('type', 'unknown'),
                            severity=vuln.get('severity', 'medium'),
                            description=vuln.get('description', ''),
                            evidence=vuln.get('evidence', '')[:500],
                            timestamp=datetime.now().isoformat()
                        )
                        findings.append(finding)
                        
            self.state.findings.extend(findings)
            self.state.qa_runs_completed += 1
            
            self.log(AgentRole.QA, f"Found {len(findings)} vulnerabilities")
            self.broadcast_update("qa_completed", {
                "findings_count": len(findings),
                "findings": [asdict(f) for f in findings]
            })
            
        except subprocess.TimeoutExpired:
            self.log(AgentRole.QA, "⚠️ QA agent timed out")
            self.broadcast_update("qa_timeout", {})
            
        except Exception as e:
            self.log(AgentRole.QA, f"❌ QA agent error: {e}")
            self.broadcast_update("qa_error", {"error": str(e)})
            
        return findings
        
    # -------------------------------------------------------------------------
    # CEO Agent Functions
    # -------------------------------------------------------------------------
    
    def ceo_evaluate_demo(self) -> dict:
        """CEO: Evaluate if the demo is pitch-ready"""
        self.log(AgentRole.CEO, "Evaluating demo readiness...")
        self.state.status = DemoStatus.CEO_REVIEWING
        self.broadcast_update("ceo_reviewing", {})
        
        # Scoring rubric
        score = 0
        feedback = []
        
        # 1. Services running (20 points)
        healthy_services = sum(1 for v in self.state.services_healthy.values() if v)
        total_services = len(self.state.services_healthy)
        if total_services > 0:
            service_score = int((healthy_services / total_services) * 20)
            score += service_score
            if service_score < 20:
                feedback.append(f"Only {healthy_services}/{total_services} services healthy")
                
        # 2. Vulnerabilities found (30 points)
        vuln_count = len(self.state.findings)
        if vuln_count >= 3:
            score += 30
        elif vuln_count >= 1:
            score += 15
            feedback.append("Need more vulnerability findings for impact")
        else:
            feedback.append("No vulnerabilities found - demo lacks punch")
            
        # 3. Variety of findings (20 points)
        vuln_types = set(f.type for f in self.state.findings)
        if len(vuln_types) >= 3:
            score += 20
        elif len(vuln_types) >= 2:
            score += 10
            feedback.append("Need more variety in vulnerability types")
        else:
            feedback.append("Only one type of vulnerability - show breadth")
            
        # 4. Critical findings (20 points)
        critical_count = sum(1 for f in self.state.findings if f.severity in ['critical', 'high'])
        if critical_count >= 2:
            score += 20
        elif critical_count >= 1:
            score += 10
            feedback.append("Need more high-severity findings for 'wow' factor")
        else:
            feedback.append("No critical findings - less compelling")
            
        # 5. Demo stability (10 points)
        if self.state.qa_runs_completed >= 2:
            score += 10
        else:
            feedback.append("Run demo multiple times to prove stability")
            
        self.state.demo_readiness_score = score
        self.state.ceo_feedback = "; ".join(feedback) if feedback else "Looking good!"
        self.state.pitch_ready = score >= 80
        
        evaluation = {
            "score": score,
            "pitch_ready": self.state.pitch_ready,
            "feedback": feedback,
            "summary": self._ceo_generate_summary()
        }
        
        self.log(AgentRole.CEO, f"Demo readiness: {score}/100")
        if self.state.pitch_ready:
            self.log(AgentRole.CEO, "✅ PITCH READY!")
        else:
            self.log(AgentRole.CEO, f"❌ Not ready: {self.state.ceo_feedback}")
            
        self.broadcast_update("ceo_evaluation", evaluation)
        return evaluation
        
    def _ceo_generate_summary(self) -> str:
        """CEO: Generate executive summary for demo"""
        findings = self.state.findings
        
        if not findings:
            return "No security findings to report yet."
            
        summary = f"""
## BlackBox AI Security Assessment

**Automated scan completed** against target application.

### Key Findings
- **{len(findings)} vulnerabilities** discovered automatically
- **{sum(1 for f in findings if f.severity in ['critical', 'high'])} critical/high** severity issues
- **{len(set(f.type for f in findings))} vulnerability types** detected

### Top Issues
"""
        for f in sorted(findings, key=lambda x: ['critical', 'high', 'medium', 'low'].index(x.severity))[:3]:
            summary += f"- **{f.type.upper()}** ({f.severity}): {f.description[:100]}...\n"
            
        summary += """
### Why This Matters
Traditional pen testing takes weeks and costs $50K+. 
Our AI agent found these issues in **under 2 minutes**, automatically.

**Self-improving**: Each scan makes the agent smarter.
"""
        return summary
        
    # -------------------------------------------------------------------------
    # Human Checkpoint
    # -------------------------------------------------------------------------
    
    def human_checkpoint(self) -> bool:
        """Pause for human feedback"""
        if not self.interactive:
            return True
            
        self.state.status = DemoStatus.AWAITING_HUMAN
        self.broadcast_update("awaiting_human", {
            "score": self.state.demo_readiness_score,
            "ceo_feedback": self.state.ceo_feedback
        })
        
        print("\n" + "="*60)
        self.log(AgentRole.HUMAN, "CHECKPOINT - Your turn!")
        print("="*60)
        print(f"\nDemo readiness: {self.state.demo_readiness_score}/100")
        print(f"CEO says: {self.state.ceo_feedback}")
        print(f"Findings: {len(self.state.findings)}")
        print("\nOptions:")
        print("  [c] Continue iterating")
        print("  [r] Mark as ready (override)")
        print("  [f] Add feedback for next iteration")
        print("  [q] Quit")
        
        choice = input("\nYour choice: ").strip().lower()
        
        if choice == 'q':
            return False
        elif choice == 'r':
            self.state.human_approved = True
            self.state.pitch_ready = True
            self.log(AgentRole.HUMAN, "Marked as ready (human override)")
            return False  # Stop loop
        elif choice == 'f':
            feedback = input("Your feedback: ").strip()
            self.state.human_feedback = feedback
            self.log(AgentRole.HUMAN, f"Added feedback: {feedback}")
            self.broadcast_update("human_feedback", {"feedback": feedback})
            return True
        else:
            return True  # Continue
            
    # -------------------------------------------------------------------------
    # Main Orchestration Loop
    # -------------------------------------------------------------------------
    
    def run(self):
        """Main orchestration loop"""
        print("\n" + "="*60)
        print("  BlackBox AI - CEO/CTO Orchestrator")
        print("="*60 + "\n")
        
        try:
            # Phase 1: CTO validates environment
            if not self.cto_validate_environment():
                self.log(AgentRole.CTO, "Environment validation failed. Fix issues and retry.")
                self.state.status = DemoStatus.FAILED
                return
                
            # Phase 2: CTO starts services
            self.cto_start_services()
            
            # Phase 3: Iteration loop
            while self.state.iteration < self.state.max_iterations:
                self.state.iteration += 1
                self.log(AgentRole.CTO, f"--- Iteration {self.state.iteration} ---")
                self.broadcast_update("iteration_start", {"iteration": self.state.iteration})
                
                # CTO: Run QA agent
                self.cto_run_qa_agent()
                
                # CEO: Evaluate results
                evaluation = self.ceo_evaluate_demo()
                
                # Check if we're done
                if self.state.pitch_ready:
                    self.log(AgentRole.CEO, "🎉 Demo is PITCH READY!")
                    self.state.status = DemoStatus.PITCH_READY
                    break
                    
                # Human checkpoint
                if not self.human_checkpoint():
                    break
                    
                # Brief pause between iterations
                time.sleep(2)
                
            # Final summary
            self._print_final_summary()
            
        except KeyboardInterrupt:
            self.log(AgentRole.HUMAN, "Interrupted by user")
            
        finally:
            self.stop_all_services()
            self.state.save(self.state_file)
            
    def _print_final_summary(self):
        """Print final orchestration summary"""
        print("\n" + "="*60)
        print("  FINAL SUMMARY")
        print("="*60)
        print(f"\nStatus: {self.state.status.value}")
        print(f"Iterations: {self.state.iteration}")
        print(f"Demo Readiness: {self.state.demo_readiness_score}/100")
        print(f"Vulnerabilities Found: {len(self.state.findings)}")
        print(f"Pitch Ready: {'✅ YES' if self.state.pitch_ready else '❌ NO'}")
        
        if self.state.findings:
            print("\nTop Findings:")
            for f in self.state.findings[:5]:
                print(f"  - [{f.severity.upper()}] {f.type}: {f.description[:60]}...")
                
        print("\n" + "="*60)


# -----------------------------------------------------------------------------
# CLI Entry Point
# -----------------------------------------------------------------------------

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="CEO/CTO Agent Orchestrator")
    parser.add_argument("--non-interactive", action="store_true", 
                       help="Run without human checkpoints")
    parser.add_argument("--max-iterations", type=int, default=10,
                       help="Maximum iteration count")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from saved state")
    
    args = parser.parse_args()
    
    orchestrator = Orchestrator(interactive=not args.non_interactive)
    
    if args.resume:
        orchestrator.state = OrchestratorState.load()
        print(f"Resumed from iteration {orchestrator.state.iteration}")
        
    orchestrator.state.max_iterations = args.max_iterations
    orchestrator.run()


if __name__ == "__main__":
    main()
