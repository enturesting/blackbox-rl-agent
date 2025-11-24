# AIE Hackathon - Security Testing Agent Suite

An AI-powered security testing framework that uses LangGraph and Google Gemini to automatically discover and exploit vulnerabilities in web applications.

## Features

- **Autonomous Web Navigation**: Uses Playwright to interact with web applications like a real user
- **Intelligent Vulnerability Discovery**: AI-driven approach to finding security issues
- **SQL Injection Detection**: Automatically tests for and exploits SQL injection vulnerabilities
- **Comprehensive Reporting**: Generates detailed reports with screenshots and executive summaries
- **Reinforcement Learning**: Learns from successful exploits to improve future performance

## Prerequisites

- Python 3.8+
- Node.js 16+ (for running the test target application)
- Google API Key(s) for Gemini

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd aie-hackathon
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key(s):

```
GOOGLE_API_KEY=your-api-key-here
# For higher rate limits, add multiple keys:
GOOGLE_API_KEY_2=another-api-key
GOOGLE_API_KEY_3=yet-another-key
# ... up to GOOGLE_API_KEY_9
```

**Note**: Each API key provides ~10 requests per minute. Multiple keys increase throughput.

## Testing with Buggy-Vibe (Demo Target)

### 1. Start the Target Application

First, ensure the buggy-vibe application is running:

```bash
# Terminal 1 - Frontend
cd ../buggy-vibe
npm install
npm run dev
```

```bash
# Terminal 2 - Backend (vulnerable API)
cd ../buggy-vibe
node server-vulnerable.cjs
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:3001

### 2. Run the QA Security Agent

```bash
# In the aie-hackathon directory
source venv/bin/activate
python qa_agent_v1.py
```

The agent will:
1. Open a browser window (non-headless mode)
2. Navigate through the application
3. Discover the Users search page
4. Attempt SQL injection attacks
5. Extract sensitive data (passwords, API keys, sessions)
6. Generate screenshots and logs
7. Create an executive report

### 3. View Results

Results are saved in:
- `qa_screenshots/` - Screenshots of each action
- `qa_reports/` - Detailed markdown reports
- `rl_training_data.json` - Reinforcement learning data
- `executive_report_*.html` - Executive summary (auto-generated)

## Running All Agents (Coming Soon)

For a comprehensive security assessment with multiple specialized agents:

```bash
./run_all_agents.sh
```

This will run:
- QA Agent (qa_agent_v1.py) - General vulnerability discovery
- Gemini CodeRabbit Analyzer - Code analysis
- Exploit Planner - Attack strategy generation
- Attack Agent - Automated exploitation

## Project Structure

```
aie-hackathon/
├── qa_agent_v1.py              # Main QA security testing agent
├── executive_report_generator.py # Report generation utility
├── gemini_coderabbit_analyzer.py # Code analysis agent
├── exploit_planner.py          # Attack planning agent
├── attack.py                   # Exploitation agent
├── run_all_agents.sh          # Orchestration script
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create from .env.example)
├── qa_screenshots/            # Screenshot outputs
├── qa_reports/               # Generated reports
└── rl_training_data.json     # Learning data

buggy-vibe/                    # Test target application
├── src/                       # Frontend React code
├── server-vulnerable.cjs      # Vulnerable backend
├── pw_db.json                # Mock database with sensitive data
└── package.json              # Node.js dependencies
```

## Key Components

### QA Agent (qa_agent_v1.py)

The main security testing agent that:
- Uses LangGraph for state management
- Implements reinforcement learning for improved exploitation
- Captures screenshots of all actions
- Generates detailed reports

### Executive Report Generator

Automatically creates HTML reports summarizing:
- Vulnerabilities discovered
- Successful exploits
- Extracted sensitive data
- Recommendations

## Troubleshooting

### "No Google API keys found"
- Ensure `.env` file exists and contains valid API keys
- Check that python-dotenv is installed: `pip install python-dotenv`

### "Target page, context or browser has been closed"
- This can happen if the agent navigates too quickly
- The agent has built-in retry logic
- Ensure both frontend and backend servers are running

### Rate Limiting Issues
- Add more Google API keys to increase rate limit
- The agent automatically rotates between available keys
- Built-in safeguards stop after 15 steps to prevent quota exhaustion

## Security Notice

This tool is designed for authorized security testing only. Never use it against applications you don't own or have explicit permission to test.

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Test thoroughly with the buggy-vibe application
4. Submit a pull request

## License

[Your License Here]

