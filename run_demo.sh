#!/bin/bash

# =============================================================================
# AI Security Testing Suite - Demo Runner
# =============================================================================
# This script starts everything needed for the demo:
#   1. buggy-vibe vulnerable backend (port 3001)
#   2. buggy-vibe vulnerable frontend (port 5173)
#   3. AI Security Suite API server (port 8000)
#   4. AI Security Suite Dashboard (port 3000)
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}     ${GREEN}🛡️  AI Security Testing Suite - Demo${NC}                   ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     ${YELLOW}Automated Penetration Testing with RL${NC}                  ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✓${NC} Loaded environment variables from .env"
fi

# Check for required API key
if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${RED}✗${NC} ERROR: GOOGLE_API_KEY not set!"
    echo -e "  Please create a .env file with your Google API key:"
    echo -e "  ${YELLOW}echo 'GOOGLE_API_KEY=your-key-here' > .env${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Google API key found"
echo ""

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    if check_port $1; then
        echo -e "${YELLOW}⚠${NC}  Port $1 in use, stopping existing process..."
        kill $(lsof -t -i:$1) 2>/dev/null || true
        sleep 1
    fi
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down all services...${NC}"
    
    # Kill background jobs
    jobs -p | xargs -r kill 2>/dev/null || true
    
    # Kill processes on specific ports
    kill_port 3000
    kill_port 3001
    kill_port 5173
    kill_port 8000
    
    echo -e "${GREEN}✓${NC} All services stopped"
    exit 0
}

# Set up trap to cleanup on exit
trap cleanup EXIT INT TERM

# =============================================================================
# Step 1: Install dependencies if needed
# =============================================================================
echo -e "${BLUE}━━━ Step 1: Checking Dependencies ━━━${NC}"

# Check/install buggy-vibe dependencies
if [ ! -d "target-apps/buggy-vibe/node_modules" ]; then
    echo -e "${YELLOW}Installing buggy-vibe dependencies...${NC}"
    cd target-apps/buggy-vibe
    npm install
    cd "$SCRIPT_DIR"
else
    echo -e "${GREEN}✓${NC} buggy-vibe dependencies installed"
fi

# Check/install dashboard dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Installing dashboard dependencies...${NC}"
    cd frontend
    npm install
    cd "$SCRIPT_DIR"
else
    echo -e "${GREEN}✓${NC} Dashboard dependencies installed"
fi

# Check Python dependencies
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install -r requirements.txt -q
else
    echo -e "${GREEN}✓${NC} Python dependencies installed"
fi

echo ""

# =============================================================================
# Step 2: Clear ports if needed
# =============================================================================
echo -e "${BLUE}━━━ Step 2: Preparing Ports ━━━${NC}"
kill_port 3000
kill_port 3001
kill_port 5173
kill_port 8000
echo -e "${GREEN}✓${NC} Ports 3000, 3001, 5173, 8000 are ready"
echo ""

# =============================================================================
# Step 3: Start buggy-vibe (the vulnerable target)
# =============================================================================
echo -e "${BLUE}━━━ Step 3: Starting Target Application (buggy-vibe) ━━━${NC}"

cd target-apps/buggy-vibe

# Start vulnerable backend
echo -e "${YELLOW}Starting vulnerable backend on port 3001...${NC}"
npm run server:vulnerable > /tmp/buggy-backend.log 2>&1 &
BUGGY_BACKEND_PID=$!
sleep 2

if check_port 3001; then
    echo -e "${GREEN}✓${NC} Vulnerable backend running (PID: $BUGGY_BACKEND_PID)"
else
    echo -e "${RED}✗${NC} Failed to start vulnerable backend"
    cat /tmp/buggy-backend.log
    exit 1
fi

# Start frontend
echo -e "${YELLOW}Starting buggy-vibe frontend on port 5173...${NC}"
npm run dev > /tmp/buggy-frontend.log 2>&1 &
BUGGY_FRONTEND_PID=$!
sleep 3

if check_port 5173; then
    echo -e "${GREEN}✓${NC} buggy-vibe frontend running (PID: $BUGGY_FRONTEND_PID)"
else
    echo -e "${RED}✗${NC} Failed to start buggy-vibe frontend"
    cat /tmp/buggy-frontend.log
    exit 1
fi

cd "$SCRIPT_DIR"
echo ""

# =============================================================================
# Step 4: Start AI Security Suite
# =============================================================================
echo -e "${BLUE}━━━ Step 4: Starting AI Security Suite ━━━${NC}"

# Start API server with DEMO_MODE
echo -e "${YELLOW}Starting API server on port 8000...${NC}"
export DEMO_MODE=true
export TARGET_URL=http://localhost:5173
python server.py > /tmp/api-server.log 2>&1 &
API_PID=$!
sleep 2

if check_port 8000; then
    echo -e "${GREEN}✓${NC} API server running (PID: $API_PID)"
else
    echo -e "${RED}✗${NC} Failed to start API server"
    cat /tmp/api-server.log
    exit 1
fi

# Start dashboard
echo -e "${YELLOW}Starting dashboard on port 3000...${NC}"
cd frontend
npm run dev > /tmp/dashboard.log 2>&1 &
DASHBOARD_PID=$!
cd "$SCRIPT_DIR"
sleep 3

if check_port 3000; then
    echo -e "${GREEN}✓${NC} Dashboard running (PID: $DASHBOARD_PID)"
else
    echo -e "${RED}✗${NC} Failed to start dashboard"
    cat /tmp/dashboard.log
    exit 1
fi

echo ""

# =============================================================================
# Step 5: Display Access Information
# =============================================================================
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}                    ${GREEN}🚀 All Services Running!${NC}                 ${CYAN}║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}                                                            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${YELLOW}📊 Dashboard:${NC}        http://localhost:3000               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${YELLOW}🎯 Target App:${NC}       http://localhost:5173               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${YELLOW}📡 API Server:${NC}       http://localhost:8000               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${YELLOW}🔓 Vuln Backend:${NC}     http://localhost:3001               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                            ${CYAN}║${NC}"
echo -e "${CYAN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}How to Demo:${NC}                                              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  1. Open Dashboard at http://localhost:3000               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  2. Target URL should be http://localhost:5173            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  3. Click '🚀 Run Full Pipeline'                          ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  4. Watch the AI find vulnerabilities!                    ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                                            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${RED}Press Ctrl+C to stop all services${NC}                       ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Keep script running and show logs
echo -e "${BLUE}━━━ Live Logs (API Server) ━━━${NC}"
tail -f /tmp/api-server.log
