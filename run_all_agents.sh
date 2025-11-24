#!/bin/bash

# AI Security Testing Suite Runner
# This script runs all three security testing components in sequence

echo "=================================================="
echo "🚀 AI Security Testing Suite"
echo "=================================================="
echo ""

# Change to the script directory
cd "$(dirname "$0")"

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment activated"
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

# Run Gemini CodeRabbit Analyzer
echo "=================================================="
echo "🔍 Running Gemini CodeRabbit Analyzer"
echo "=================================================="
python gemini_coderabbit_analyzer.py

if [ $? -ne 0 ]; then
    echo "❌ Gemini CodeRabbit Analyzer failed"
    exit 1
fi

echo ""
echo "✅ Gemini CodeRabbit Analyzer completed successfully"
echo ""

# Summary
echo "=================================================="
echo "📊 Summary"
echo "=================================================="
echo "✅ All security testing components completed!"
echo ""
echo "Check the following outputs:"
echo "  - QA Screenshots: qa_screenshots/"
echo "  - QA Reports: qa_reports/"
echo "  - RL Training Data: rl_training_data.json"
echo "  - Exploit Plans: (check exploit planner output)"
echo "  - Code Analysis: (check analyzer output)"
echo ""
echo "=================================================="

# Deactivate virtual environment
deactivate 2>/dev/null || true
