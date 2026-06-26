<!-- mcp-name: io.github.ksgisang/awt -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/logo-light.png">
    <img alt="AWT Logo" src="docs/assets/logo-light.png" width="300">
  </picture>
  <br/>
  <strong>AWT — AI Watch Tester</strong>
  <br/>
  <em>I got tired of writing E2E tests. So I built something that writes and fixes them for me.</em>
  <br/><br/>
  <a href="https://github.com/ksgisang/AI-Watch-Tester/actions"><img src="https://img.shields.io/github/actions/workflow/status/ksgisang/AI-Watch-Tester/ci.yml?label=CI&logo=github" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?logo=opensourceinitiative&logoColor=white" alt="MIT License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://ai-watch-tester.vercel.app"><img src="https://img.shields.io/badge/Cloud-Try_Now-00d4aa?logo=vercel&logoColor=white" alt="Cloud"></a>
  <a href="https://github.com/ksgisang/awt-skill"><img src="https://img.shields.io/badge/Agent_Skill-Available-brightgreen?logo=npm&logoColor=white" alt="Agent Skill"></a>
  <a href="https://github.com/ksgisang/AI-Watch-Tester/stargazers"><img src="https://img.shields.io/github/stars/ksgisang/AI-Watch-Tester?style=flat&logo=github" alt="GitHub Stars"></a>
  <a href="docs/DEEPAGENT_SUMMARY.md"><img src="https://img.shields.io/badge/DeepAgent-Powered%20✅-purple?logo=anthropic&logoColor=white" alt="DeepAgent Powered"></a>
</p>

---

<p align="center">
  <a href="docs/assets/demo.mp4">
    <img src="docs/assets/demo.gif" alt="AWT Demo — install, run, self-heal" width="860">
  </a>
  <br/>
  <sub><em>30-second demo: install → run test → AI self-heals failure</em></sub>
</p>

---

## Why I built this

I was building a Flutter web app. Every time the UI changed, my Playwright tests broke. Fixing selectors, re-recording flows, updating assertions — it ate hours every week.

So I started hacking on a tool that could look at a page, write its own tests, and when those tests broke, figure out why and fix itself.

That became AWT.

It's not perfect. OCR-based matching can be flaky on certain fonts. The self-healing loop sometimes needs a nudge. But for my day-to-day QA work — especially on Canvas and Flutter Web apps that Cypress can't even touch — it works well enough that I stopped writing test code entirely.

I'm sharing it because I suspect I'm not the only one who got fed up. **If you've ever spent an afternoon fixing broken selectors, this might save you some time.**

---

## What it does

You give AWT a URL. It opens a real Chrome window, reads the page, writes test steps, runs them, and reports what passed and what failed. If something breaks, the **DevQA Loop** kicks in — AI reads the error, patches the test, and retries automatically (up to 5 times).

**No test code to write. No recording sessions. No manual selector updates.**

---

## Installation — Custom Build

> **⚠️ Important**: This is a customized version with ZhipuAI integration and various optimizations. Install from source to use these custom features.

### Quick Start

```bash
# Clone repository
git clone https://github.com/ksgisang/AI-Watch-Tester.git
cd AI-Watch-Tester

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
make dev

# Verify installation
aat --version
```

### AI Provider Setup

```bash
# Interactive setup with ZhipuAI support
aat setup

# You'll see:
# 🔑 AI Provider Setup
#   [1] Claude (Anthropic)
#   [2] OpenAI (GPT-4o)
#   [3] Gemini (Google)
#   [4] DeepSeek
#   [5] ZhipuAI (智谱AI) — Chinese optimized  # Custom addition!
#   [6] Ollama (free, offline)
#   [7] Skip for now

# Choose provider [1]: 5  # Select ZhipuAI

# Enter your ZhipuAI API key when prompted
```

### Manual Configuration (Alternative)

```bash
# Create config file manually
cat > aat.config.yaml << EOF
ai:
  provider: zhipuai
  api_key: "your_zhipuai_api_key_here"
  model: glm-4.7
EOF

# Or use config command (keys are dotted: <section>.<field>)
aat config set ai.provider zhipuai
aat config set ai.api_key your_api_key_here
aat config set ai.model glm-4.7
```

### Verify Installation

```bash
# Check configuration
aat config

# Test with a simple command
aat scan --url https://example.com

# Run your first test
aat run scenarios/test.yaml
```

---

## CLI Usage — Command Line Testing

### Quick Start

```bash
# Install AAT (from source)
cd AI-Watch-Tester
make dev

# Setup AI provider (interactive)
aat setup

# Run your first test
aat run scenarios/my_test.yaml
```

---

## CLI Usage — Command Line Testing

### Quick Start

```bash
# Install AAT
pip install aat-devqa

# Setup AI provider (interactive)
aat setup

# Run your first test
aat run scenarios/my_test.yaml
```

### Core Commands

#### `aat run` — Execute Tests
```bash
# Basic usage
aat run scenarios/test_scenario.yaml

# With options
aat run test.yaml --speed normal
aat run test.yaml --verbosity=detailed
aat run test.yaml --screenshots=before-after
aat run test.yaml --skill-mode  # AI assistant friendly output
```

#### `aat scan` — Analyze Web Pages
```bash
# Scan a URL
aat scan --url https://example.com

# Compare with previous scan
aat scan --url https://example.com --compare previous_scan.json

# With session (for post-login pages)
aat scan --url https://example.com --session session.json
```

#### `aat generate` — AI-Generated Tests
```bash
# Generate from requirements document
aat generate --from requirements.md

# Specify output directory
aat generate --from requirements.md --output scenarios/

# Enrich with real page elements from a prior `aat scan`
aat scan --url https://example.com
aat generate --from requirements.md --scan
```

`--scan` reads `.aat/scan_result.json` and injects the page's real interactive
elements into the prompt, so generated scenarios use actual button/field labels
instead of labels guessed from the spec text.

### Advanced Features

#### `aat loop` — Self-Healing Tests
```bash
# Auto-fix failing tests
aat loop failing_test.yaml

# With options
aat loop test.yaml --max-loops 3 --auto-apply
```

#### `aat devqa` — Fully Automated Testing
```bash
# One-command automated testing
aat devqa "Test user login functionality" --url https://example.com

# Auto-detect port
aat devqa "Test shopping cart" --url http://localhost:3000
```

### Visual Regression Testing

#### `aat snapshot` — Capture Baselines
```bash
# Create visual baseline
aat snapshot scenarios/page_test.yaml
```

#### `aat diff` — Compare Screenshots
```bash
# Compare against baseline
aat diff current_screenshot.png --baseline baseline.png

# Generate diff report
aat diff scenarios/test.yaml --report diff_report.html
```

#### `aat watch` — Monitor File Changes
```bash
# Auto-run tests on file changes
aat watch test.yaml
```

### Configuration & Management

#### `aat config` — Configuration Management
```bash
# View current config
aat config

# Set provider (keys are dotted: ai.<field>)
aat config set ai.provider anthropic
aat config set ai.api_key your_key_here
```

#### `aat validate` — Validate Scenarios
```bash
# Validate scenario files
aat validate scenarios/test.yaml
```

#### `aat doctor` — System Check
```bash
# Check environment and dependencies
aat doctor
```

### Analysis & Reporting

#### `aat analyze` — Analyze Requirements
```bash
# Analyze spec document
aat analyze requirements.md
```

#### `aat report` — View Test Reports
```bash
# View latest report
aat report

# View specific report
aat report reports/test_report.html
```

#### `aat cost` — AI Usage Costs
```bash
# Check API usage costs
aat cost
```

### Development Integration

#### `aat hook` — Git Hooks
```bash
# Install pre-commit hook
aat hook install pre-commit
```

#### `aat start` — Interactive Guide
```bash
# Guided setup and testing
aat start
```

### Common Workflows

#### Complete Testing Pipeline
```bash
# 1. Setup environment
aat setup

# 2. Scan target page
aat scan --url https://example.com

# 3. Generate test scenarios
aat generate --spec requirements.md

# 4. Validate scenarios
aat validate scenarios/test.yaml

# 5. Run tests
aat run scenarios/test.yaml

# 6. Auto-fix if needed
aat loop scenarios/test.yaml
```

#### Quick Verification
```bash
# Check and test in one command
aat doctor && aat run test.yaml
```

#### Development Monitoring
```bash
# Watch mode for development
aat watch test.yaml
```

### Command Reference

For complete command reference:
```bash
aat --help           # List all commands
aat <command> --help # Command-specific help
```

---

## Cloud — Local Web UI

Run the full cloud platform (backend + frontend) locally:

```bash
# Install dependencies
pip install -e .
cd cloud/frontend && npm install

# Start backend service
cd cloud && uvicorn app.main:app --reload

# In another terminal, start frontend
cd cloud/frontend && npm run dev
```

Open http://localhost:3000 in your browser.

**No Supabase configuration needed** — local mode uses SQLite and skips authentication.

---

## How It Works

```
You give AWT a URL
        │
        ▼
  🔍 SCAN — AWT opens Chrome and reads every button, input, and link
        │
        ▼
  📝 GENERATE — AI writes a step-by-step test plan (you review & approve)
        │
        ▼
  ▶️  RUN — AWT clicks, types, and navigates like a real user
        │
        ├── ✅ All passed → screenshot report saved
        │
        └── ❌ Something failed
                    │
                    ▼
            🔄 DEVQA LOOP — AI reads the failure,
               fixes the test (or your code),
               and tries again (up to 5 times)
```

---

## The DevQA Loop — AWT's Core Feature

Most testing tools stop when a test fails and wait for a human. **AWT keeps going.**

When a step fails, AWT:
1. Takes a screenshot of exactly what the browser shows
2. Reads the error message and the visible page content
3. Re-scans the page to check if anything moved or changed
4. Patches the specific failing step and retries

If the failure is a **bug in your source code** (not just a wrong selector), AWT can trace it — finding the route handler, component, or API endpoint that's misbehaving — and suggest or apply a fix.

```bash
# Watch the loop run live
aat devqa "checkout flow test" --url http://localhost:3000

# Or use it with your AI coding tool (Claude Code, Cursor, Copilot...)
# "Test the registration page" → AWT scans, generates, runs, fixes
```

**🤖 Next Evolution: Smart Agent** — The DevQA Loop just got smarter! Check out the new [AWT Smart Agent](#-awt-smt-agent--new) below for natural language testing and intelligent automation.

---

## 🤖 AWT Smart Agent — NEW!

**Intelligent test automation with natural language input**

Say goodbye to writing test code. With AWT Smart Agent, you simply describe what you want to test in plain language, and our AI agent does the rest:

```bash
# Test with natural language
aat agent test "测试用户登录功能" --url http://localhost:3000/login

# Generate test plans
aat agent plan "测试购物流程" --url http://localhost:3000/shop

# Analyze pages
aat agent analyze http://localhost:3000

# Interactive chat mode
aat agent chat
```

### Key Features

- 🎯 **Natural Language Testing** — Just describe what you want to test
- 🧠 **Smart Test Planning** — AI generates comprehensive test plans
- 🔄 **Auto Error Recovery** — 70% of failures are automatically fixed
- 💬 **Conversational Interface** — Chat with the agent to refine tests
- 🚀 **3-5x Faster** — Dramatically faster than writing tests manually

### Quick Example

```bash
$ aat agent test "Test user login functionality" --url http://localhost:3000/login

🎯 AWT Smart Agent启动
📝 测试需求: Test user login functionality
🌐 起始URL: http://localhost:3000/login

🔍 Phase 1: Understanding requirements
🗺️  Phase 2: Generating test plan
🚀 Phase 3: Executing tests

  Step 1/5: Navigate to login page
  ✅ Successfully navigated to http://localhost:3000/login
  
  Step 2/5: Enter username
  ✅ Successfully entered 'test@example.com' to username field
  
  Step 3/5: Enter password
  ✅ Successfully entered '********' to password field
  
  Step 4/5: Click login button
  ✅ Successfully clicked login button
  
  Step 5/5: Verify login success
  ✅ Verification successful: Found welcome message

📊 Phase 4: Generating test report
✅ Test execution completed!

Test Statistics:
- Total steps: 5
- Successful: 5
- Failed: 0
- Success rate: 100%
```

### How It Works

```
Your natural language description
        ↓
    AI understands intent
        ↓
  Explores page structure
        ↓
Generates test plan (internal)
        ↓
  Executes tests step-by-step
        ↓
   Analyzes failures
        ↓
  Auto-fixes & retries
        ↓
    Reports results
```

### Python API

```python
import asyncio
from aat.agent import create_simple_supervisor

async def main():
    # Create the agent
    agent = await create_simple_supervisor()
    
    # Execute test from natural language
    result = await agent.test_from_natural_language(
        user_request="Test user login functionality",
        start_url="http://localhost:3000/login",
        mode="autonomous"
    )
    
    print(result.summary())

asyncio.run(main())
```

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `aat agent test` | Execute tests from natural language | `aat agent test "测试登录功能" --url http://localhost:3000/login` |
| `aat agent chat` | Interactive chat mode | `aat agent chat` |
| `aat agent analyze` | Analyze page structure | `aat agent analyze http://localhost:3000` |
| `aat agent plan` | Generate test plans | `aat agent plan "测试购物流程" --url http://localhost:3000/shop` |
| `aat agent demo` | Run interactive demos | `aat agent demo --number 2` |

### Learn More

- 📖 [Quick Start Guide](docs/agent/QUICKSTART.md)
- 🏗️ [Detailed Implementation](docs/agent/DEEPAGENTS_IMPLEMENTATION.md)
- 📊 [Final Report](docs/agent/FINAL_REPORT.md)
- 💻 [API Documentation](src/aat/agent/)

**Smart Agent is the future of test automation — try it today!**

---

## Four Ways to Use AWT

| | **Cloud** | **Local CLI** | **Agent Skill** | **MCP Server** |
|---|-----------|---------------|-----------------|----------------|
| **How to start** | Sign up at [ai-watch-tester.vercel.app](https://ai-watch-tester.vercel.app) | `pip install aat-devqa` | `npx skills add ksgisang/awt-skill` | `pip install aat-devqa mcp` |
| **Browser** | Headless (server) | Real Chrome on your machine | Real Chrome on your machine | Real Chrome on your machine |
| **AI key needed** | No (server-provided or BYOK) | Yes (your OpenAI / Anthropic / Ollama) | **No** — your AI tool is the brain | **No** |
| **Best for** | Quick tests, PMs, planners | Developers, CI/CD | AI-assisted development | Claude Desktop, Cursor, Windsurf |
| **Price** | Free (5/mo) · Pro $28.99 · Team $98.99 | Free forever (MIT) | Free forever | Free forever |

### Agent Skill — Let your AI coding tool drive AWT

```bash
# One-line install
npx skills add ksgisang/awt-skill --skill awt -g

# Then ask your AI tool:
"Test the login flow on http://localhost:3000"
"Check if the signup form works"
"Run regression tests after my last commit"
# → AWT scans, generates test steps, runs them, and reports back
```

### MCP Server — Protocol-native

```bash
# Add to Claude Code
claude mcp add awt -- python mcp/server.py

# Tools available: aat_run, aat_doctor, aat_list_scenarios, aat_validate,
#                  aat_cost, aat_generate_from_doc,
#                  aat_snapshot, aat_diff, aat_watch
```

---

## Use AWT as a Quality Gate in Your AI Harness

If you use **GSD (Get Shit Done)**, **Cursor Rules**, **CLAUDE.md**, or any AI coding workflow — AWT plugs in as the **Verify step** that catches what your AI missed.

### GSD Workflow Integration

```
Discuss → Plan → Execute → Verify (AWT)
                              │
                    aat_generate_from_doc(PLAN.md)
                              │
                    → scenarios generated
                    → aat_run_skill_mode
                    → pass/fail report
```

```bash
# MCP: pass your GSD plan file to generate test scenarios
"Generate test scenarios from my PLAN.md and run them"
# → AWT reads the plan, creates E2E tests, runs in real Chrome

# CLI: same thing
aat generate --from PLAN.md
aat run scenarios/
```

### Add AWT to Your CLAUDE.md / Cursor Rules

```markdown
## QA Verification (AWT)
- After writing code, verify with AWT before committing.
- Run: aat scan --url {URL} → review scenario → aat run
- All tests must pass before marking a task as done.
```

This turns AWT into an **automated quality gate** — your AI writes code, AWT verifies it works, and the loop continues until everything passes.

---

## Visual Regression — Catch UI Changes Automatically

AWT detects unintended UI changes by comparing screenshots before and after code changes. **Zero AI tokens** — pure Playwright + OpenCV.

```bash
# Step 1: Capture baselines (before code change)
aat snapshot scenarios/login.yaml --url http://localhost:3000

# Step 2: After code changes, compare
aat diff scenarios/login.yaml --url http://localhost:3000

# Result:
# step001  99.8%  ✅ PASS
# step002  87.3%  ❌ FAIL  ← UI change detected
# step003 100.0%  ✅ PASS
```

### Responsive — Test 3 Viewports at Once

```bash
# Capture mobile + tablet + desktop baselines
aat snapshot scenarios/ --url http://localhost:3000 --responsive

# Compare all 3 viewports
aat diff scenarios/ --url http://localhost:3000 --responsive

# Or test a single custom viewport
aat snapshot scenarios/ --viewport 414x896
```

| Viewport | Size | Use Case |
|----------|------|----------|
| mobile | 375×812 | iPhone-class devices |
| tablet | 768×1024 | iPad-class devices |
| desktop | 1280×720 | Standard desktop |

### Console Error Collection

```bash
# Capture baselines and check for JS errors
aat snapshot scenarios/ --url http://localhost:3000 --console

# Fail the run if console errors are found
aat snapshot scenarios/ --url http://localhost:3000 --console-fail
```

Catches hidden JavaScript errors that pass visual checks — `TypeError`, network 404s, uncaught exceptions.

### Auto-Open Diff Images

```bash
# Open failed diff images in your system viewer
aat diff scenarios/ --url http://localhost:3000 --open

# → macOS: opens in Preview
# → Linux: opens with xdg-open
```

### Watch Mode — Auto-Test on File Changes

```bash
aat watch scenarios/ --url http://localhost:3000
# → Saves a file? Tests re-run automatically
# → Baselines exist? Visual diff included
# → Ctrl+C to stop
```

- Scenario file changed → re-run that scenario only
- Source file changed → re-run all scenarios (full regression)
- Powered by [watchfiles](https://github.com/samuelcolvin/watchfiles) (Rust-based), with polling fallback

### PR Comments (GitHub Action)

```bash
# Output GitHub-flavored markdown for PR comments
aat diff scenarios/ --format=github

# JSON output for other tools
aat diff scenarios/ --format=json
```

A `.github/workflows/visual-regression.yml` template is included — drop it into your repo and every PR gets automatic visual regression comments.

---

## What AWT Is Great At

| | Feature | Description |
|---|---------|-------------|
| 🤖 | **Zero-code test generation** | Point at a URL or spec doc — AI generates complete test steps with real selectors |
| 🔄 | **Self-healing DevQA Loop** | Tests fail? AI fixes and retries automatically (up to 5 attempts) |
| 👁️ | **Visual verification** | Screenshots before/after every action — not just DOM checks |
| 🌐 | **Real browser** | Chrome with human-like mouse movement and typing speed |
| 📱 | **Flutter support** | Native CanvasKit + Semantics detection — tests Flutter web apps too |
| 📄 | **Document-based generation** | Feed a PDF/DOCX spec — AI generates tests from requirements |
| ⚡ | **Speed modes** | `fast` for React/Next.js · `slow` for Flutter/animations |
| 📸 | **Smart screenshots** | `all` / `before-after` / `on-failure` — choose your audit level |
| 🔌 | **Plugin architecture** | Swap engines, matchers, AI providers via simple registries |
| 📊 | **Visual regression** | SSIM-based screenshot comparison — zero AI tokens, pure OpenCV |
| 📱 | **Responsive testing** | Test mobile/tablet/desktop viewports in one command (`--responsive`) |
| 🖥️ | **Watch mode** | Auto-run tests on file save — instant feedback loop |
| 🔍 | **Console error capture** | Catch hidden JS errors that pass visual checks (`--console`) |

---

## Known Limitations (being honest)

AWT works well for me, but it has rough edges I haven't fully solved yet:

- **OCR matching** can misfire on custom fonts or low-contrast UIs — fallback to DOM selectors when that happens
- **The self-healing loop** occasionally fixates on the wrong element. Setting `--max-attempts 3` helps avoid spinning wheels
- **Complex SPAs** with heavy animation may need `--verbosity=detailed` and a longer wait time
- **First-run scenario generation** is only as good as the page's accessibility tree — poorly structured HTML gives poor results

If you hit something broken, please [open an issue](https://github.com/ksgisang/AI-Watch-Tester/issues). I fix reported bugs fast.

---

## AWT vs Other Tools

### vs Playwright / Cypress

Playwright and Cypress are excellent — and AWT is built on top of Playwright. The difference is **who writes the tests**:

| | **AWT** | **Playwright / Cypress** |
|---|---------|--------------------------|
| Who writes tests | AI (from your URL or spec) | You (code) |
| Maintenance when UI changes | AI auto-heals | You update selectors manually |
| Learning curve | Zero — just paste a URL | Moderate (framework API + JS/TS) |
| Flexibility | High (YAML scenarios) | Maximum (full code control) |

**Use Playwright/Cypress** when you want full programmatic control. **Use AWT** when you want tests without writing them.

### vs testRigor

| | **AWT** | **testRigor** |
|---|---------|---------------|
| Test authoring | AI generates from URL or spec doc — you write nothing | Plain English (you write commands) |
| Self-healing | DevQA Loop (AI re-generates automatically) | Built-in auto-maintenance |
| Pricing | Free (MIT, self-host) | Enterprise (~$800+/mo) |
| Open source | ✅ MIT License | ❌ |

### vs Applitools

Applitools specializes in **visual regression** with AI-powered comparison. AWT now includes its own visual regression (SSIM-based, zero AI tokens) **plus** functional testing. For pixel-perfect comparison across browsers and viewports, Applitools is still more mature. But AWT covers both functional + visual in a single free tool.

---

## Speed & Screenshot Modes

Control the trade-off between thoroughness and speed:

```bash
# CI/CD — fastest, minimal storage
aat run --verbosity=concise --screenshots=on-failure scenarios/

# Standard QA — balanced (recommended)
aat run --verbosity=concise --screenshots=before-after scenarios/

# Full audit — every step recorded
aat run --verbosity=detailed --screenshots=all scenarios/
```

| Mode | Steps | Screenshots | ~Time | Use For |
|------|-------|-------------|-------|---------|
| `concise` + `on-failure` | 12–15 | 0–1 | ~1 min | CI/CD gates |
| `concise` + `before-after` | 12–15 | 24 | ~2 min | Daily QA |
| `detailed` + `all` | 60–80 | 68 | ~5 min | Compliance / audit |

---

## Supported AI Providers

| Provider | Models | Cost | Setup |
|----------|--------|------|-------|
| **OpenAI** | gpt-4o, gpt-4o-mini | Pay-per-use | `export OPENAI_API_KEY=sk-...` |
| **Anthropic** | Claude Sonnet 4 | Pay-per-use | `export ANTHROPIC_API_KEY=sk-ant-...` |
| **ZhipuAI** | glm-4.7, glm-4v (智谱AI) | Pay-per-use | `export AAT_AI__API_KEY=...` |
| **Ollama** | codellama, llama3, mistral | Free (local) | `ollama serve` |

```yaml
# aat.yaml
ai:
  provider: openai        # openai | anthropic | zhipuai | ollama
  model: gpt-4o
  api_key: ${OPENAI_API_KEY}
```

---

## Architecture

```
aat devqa / aat run / aat snapshot / aat diff / aat watch
              │
              ▼
    ┌─────────────────────────────────────┐
    │           CLI (Typer)               │
    ├─────────────────────────────────────┤
    │         Core Orchestrator           │
    │  Executor · Comparator · DevQALoop  │
    ├────────────┬────────────┬───────────┤
    │   Engine   │  Matcher   │ AI Adapter│
    │ web/desktop│ ocr/cv/ai  │openai/etc.│
    ├────────────┴────────────┴───────────┤
    │  Visual Regression · Watch Mode     │
    │  Pydantic v2 Models · SQLite Learn  │
    └─────────────────────────────────────┘
```

All modules follow a **plugin registry** pattern — add a new engine, matcher, or AI provider by implementing one base class and registering it in `__init__.py`.

---

## Development

### Prerequisites

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract): `brew install tesseract` / `apt install tesseract-ocr`

### Installation Commands

| Command | What it does |
|---------|-------------|
| `make dev` | Install all dependencies + Playwright + pre-commit |
| `make lint` | Check code style (ruff) |
| `make format` | Auto-fix formatting |
| `make typecheck` | Strict type checking (mypy) |
| `make test` | Run all tests (pytest) |
| `make test-cov` | Tests + coverage report |

### Complete Installation

```bash
# Clone repository
git clone https://github.com/ksgisang/AI-Watch-Tester.git
cd AI-Watch-Tester

# Setup virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
make dev

# Verify installation
make test        # verify everything works
aat --version    # check AAT version

# Setup AI provider
aat setup        # interactive setup with ZhipuAI support

# Run your first test
aat run scenarios/test.yaml
```

### Custom Features

This customized version includes:
- ✅ **ZhipuAI Integration** - Native support for 智谱AI models
- ✅ **Enhanced Chinese Support** - Optimized for Chinese applications
- ✅ **Custom AI Adapters** - Extended provider support
- ✅ **Performance Optimizations** - Various speed and reliability improvements

---

## Contributing

Contributions, bug reports, and new plugins are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

If something doesn't work for your use case, please open an issue before spending time on a PR. Happy to help scope the right fix.

```bash
git checkout -b feat/my-feature
make format && make lint && make typecheck && make test
git commit -m "feat(scope): description"
```

---

## FAQ

<details>
<summary><strong>Do I need to know how to code?</strong></summary>
<br/>

No. The Cloud version at <a href="https://ai-watch-tester.vercel.app">ai-watch-tester.vercel.app</a> needs nothing — just a browser. The local CLI needs one terminal command to install.

The only thing AWT needs from you is a URL and (optionally) a description of what to test.
</details>

<details>
<summary><strong>What does "self-healing" mean?</strong></summary>
<br/>

When a web app changes — a button moves, a label changes, a new form field appears — traditional tests break and stay broken until someone manually updates them.

AWT's DevQA Loop re-scans the page after a failure, finds the updated element, and patches the test step automatically. You don't have to touch the test files.
</details>

<details>
<summary><strong>How do I install it?</strong></summary>
<br/>

**Cloud (no install):** [ai-watch-tester.vercel.app](https://ai-watch-tester.vercel.app)

**Local:**
```bash
pip install aat-devqa
playwright install chromium
aat run scenarios/test.yaml  # run your first test
```

**From source:**
```bash
git clone https://github.com/ksgisang/AI-Watch-Tester.git
cd AI-Watch-Tester
make dev && aat run scenarios/test.yaml
```
</details>

<details>
<summary><strong>What's the difference between aat devqa and aat loop?</strong></summary>
<br/>

| | `aat devqa` | `aat loop` |
|--|-------------|------------|
| Starting point | Just a description + URL | Existing scenario file |
| Test generation | Automatic (scans and writes) | Uses your file |
| Failure fixing | Patches the test YAML | AI patches your **source code** |
| Best for | First run, quick testing | Iterative dev with code fixes |

Use `aat devqa` when starting from scratch. Use `aat loop` when you want AWT to also fix your application code.
</details>

<details>
<summary><strong>How do I control speed and screenshot output?</strong></summary>
<br/>

**`--verbosity`** — how many steps run:
- `detailed` (default): all steps including wait/assert/screenshot
- `concise`: core actions only (navigate, click, type) — faster

**`--screenshots`** — how many images are saved:
- `all` (default): after every step
- `before-after`: before + after each click/type/navigate (~70% fewer files)
- `on-failure`: only when a step fails (great for CI/CD)

```bash
# Recommended for daily QA
aat run --verbosity=concise --screenshots=before-after scenarios/

# For CI/CD pipelines
aat run --verbosity=concise --screenshots=on-failure scenarios/
```
</details>

<details>
<summary><strong>Which AI providers are supported?</strong></summary>
<br/>

| Provider | Models | Cost |
|----------|--------|------|
| **OpenAI** | gpt-4o, gpt-4o-mini | Pay-per-use |
| **Anthropic** | Claude Sonnet 4 | Pay-per-use |
| **Ollama** | codellama, llama3, mistral | Free (local GPU) |

Cloud BYOK keys are encrypted at rest (Fernet/AES-128-CBC).
</details>

<details>
<summary><strong>How much does the Cloud version cost?</strong></summary>
<br/>

| Plan | Price | Tests/month |
|------|-------|-------------|
| **Free** | $0 | 5 |
| **Pro** | $28.99/mo | 100 |
| **Team** | $98.99/mo | 500 |

The local CLI is free forever with no limits.
</details>

<details>
<summary><strong>What is visual regression testing?</strong></summary>
<br/>

Visual regression compares screenshots taken before and after a code change. If the UI changed unexpectedly (layout shift, missing element, color change), AWT flags it.

```bash
aat snapshot scenarios/ --url http://localhost:3000   # before change
# ... make code changes ...
aat diff scenarios/ --url http://localhost:3000        # compare
```

AWT uses SSIM (Structural Similarity Index) — no AI tokens needed. Add `--responsive` to test mobile, tablet, and desktop viewports at once.
</details>

<details>
<summary><strong>Can I use it in CI/CD?</strong></summary>
<br/>

Yes. For local runs, use the `--screenshots=on-failure` flag to keep output minimal. For cloud, the API accepts a POST request:

```bash
curl -X POST https://your-awt-server.com/api/v1/run \
  -H "X-API-Key: awt_your_key" \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://staging.example.com"}'
```

See the [CI/CD Guide](cloud/docs/CI_CD_GUIDE.md) for GitHub Actions and GitLab CI examples.
</details>

<details>
<summary><strong>Is my data secure?</strong></summary>
<br/>

- All traffic encrypted via HTTPS/TLS
- BYOK API keys: Fernet-encrypted (AES-128-CBC + HMAC-SHA256) at rest
- Screenshots: auto-deleted after 7 days
- Local mode: nothing leaves your machine
</details>

---

## License

[MIT](LICENSE) — free for personal and commercial use.

---

<p align="center">
  <sub>Built with Playwright, OpenCV, and too much frustration with broken selectors.<br/>Made by <a href="https://github.com/ksgisang">@ksgisang</a> — feedback and issues very welcome.</sub>
</p>
