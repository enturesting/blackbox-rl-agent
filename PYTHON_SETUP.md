# Python QA Agent Setup

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. **Create a virtual environment (recommended):**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Install Playwright browsers:**

```bash
playwright install chromium
```

4. **Setup environment variables:**

Make sure you have a `.env` file in the project root with:

```
GOOGLE_API_KEY=your_google_api_key_here
```

## Running the QA Agent

1. **Start your local server:**

Make sure your web app is running on `http://localhost:3000/home`

2. **Run the agent:**

```bash
python qa_agent.py
```

## How It Works

The Python QA agent works exactly like the TypeScript version:

1. 🚀 Launches a browser and navigates to your site
2. 🤖 Uses Google's Gemini LLM to intelligently decide what actions to take
3. 📝 Fills out forms with test data
4. 🖱️ Clicks buttons and navigates through the site
5. 📸 Takes screenshots before and after each action
6. 📊 Generates a detailed markdown report

## Output

- **Screenshots**: Saved in `qa_screenshots/` directory
- **Report**: Generated as `qa_report.md`

## Configuration

You can modify these settings in `qa_agent.py`:

- `maxSteps`: Maximum number of testing steps (default: 10)
- `url`: Starting URL (default: "http://localhost:3000/home")
- `headless`: Browser visibility (default: False - visible browser)

## Troubleshooting

**Error: "Playwright not installed"**
```bash
playwright install
```

**Error: "Google API Key not found"**
- Check your `.env` file
- Make sure `GOOGLE_API_KEY` is set

**Browser doesn't launch**
- Try running: `playwright install chromium --force`

**LLM errors**
- Check your Google API key is valid
- Try changing the model to `gemini-pro` if `gemini-2.0-flash-exp` is not available

