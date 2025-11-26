#!/bin/bash

# AI Security Testing Suite Runner
# This script runs the complete security testing pipeline in sequence:
# 1. QA Agent - Reconnaissance and vulnerability discovery
# 2. Exploit Planner - Generate exploit strategies using Gemini
# 3. Attack Execution - Execute planned exploits
# 4. Code Analysis - Deep analysis with Gemini/CodeRabbit
# 5. Executive Report - Generate C-level summary report

set -e  # Exit on first error

echo "=================================================="
echo "🚀 AI Security Testing Suite"
echo "=================================================="
echo ""

# Change to the script directory
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Set default target URL if not provided
TARGET_URL="${TARGET_URL:-http://localhost:5173}"
echo "🎯 Target URL: $TARGET_URL"
export TARGET_URL

# Try to activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
    
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "⚠️ Virtual environment activation may have failed, continuing anyway..."
    else
        echo "✅ Virtual environment activated"
    fi
else
    echo "⚠️ No virtual environment found, using system Python"
fi

echo ""

# Run QA Agent
echo "=================================================="
echo "🤖 Running QA Agent (Autonomous Security Testing)"
echo "=================================================="
python qa_agent_v1.py

if [ $? -ne 0 ]; then
    echo "❌ QA Agent failed"
    exit 1
fi

echo ""
echo "✅ QA Agent completed successfully"
echo ""

# Wait a bit between runs
sleep 2

# Run Exploit Planner
echo "=================================================="
echo "🎯 Running Exploit Planner"
echo "=================================================="
python exploit_planner.py

if [ $? -ne 0 ]; then
    echo "❌ Exploit Planner failed"
    exit 1
fi

echo ""
echo "✅ Exploit Planner completed successfully"
echo ""

# Wait a bit between runs
sleep 2

# Run Attack (optional - only if exploit plan exists)
if [ -f "final_exploit_plan.json" ]; then
    echo "=================================================="
    echo "⚔️ Running Attack Execution"
    echo "=================================================="
    python attack.py

    if [ $? -ne 0 ]; then
        echo "⚠️ Attack execution had issues (continuing anyway)"
    else
        echo ""
        echo "✅ Attack execution completed"
    fi
    echo ""
    sleep 2
fi

# Run Gemini CodeRabbit Analyzer (optional - skip if no target codebase configured)
echo "=================================================="
echo "🔍 Running Gemini CodeRabbit Analyzer"
echo "=================================================="
if python gemini_coderabbit_analyzer.py; then
    echo ""
    echo "✅ Gemini CodeRabbit Analyzer completed successfully"
else
    echo "⚠️ Gemini CodeRabbit Analyzer skipped or had issues"
fi
echo ""

# Wait a bit between runs
sleep 2

# Run Executive Report Generator
echo "=================================================="
echo "📊 Running Executive Report Generator"
echo "=================================================="
python executive_report_generator.py

if [ $? -ne 0 ]; then
    echo "⚠️ Executive Report Generator had issues"
else
    echo ""
    echo "✅ Executive Report generated successfully"
fi

echo ""

# Summary
echo "=================================================="
echo "📊 Pipeline Complete - Summary"
echo "=================================================="
echo "✅ All security testing components completed!"
echo ""
echo "Check the following outputs:"
echo "  - QA Screenshots: qa_screenshots/"
echo "  - QA Reports: qa_reports/"
echo "  - RL Training Data: rl_training_data.json"
echo "  - Exploit Plans: final_exploit_plan.json"
echo "  - Executive Report: qa_reports/executive_report_*.md"
echo ""
echo "=================================================="

# Deactivate virtual environment
deactivate 2>/dev/null || true
