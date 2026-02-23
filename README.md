<p align="center">
  <img src="docs/assets/logo.png" alt="AWT Logo" width="120">
  <br/>
  <strong>AWT — AI Watch Tester</strong>
  <br/>
  <em>Enter a URL. AI generates, executes, and heals E2E tests — automatically.</em>
  <br/><br/>
  <a href="https://github.com/ksgisang/AI-Watch-Tester/actions"><img src="https://img.shields.io/github/actions/workflow/status/ksgisang/AI-Watch-Tester/ci.yml?label=CI&logo=github" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?logo=opensourceinitiative&logoColor=white" alt="MIT License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://github.com/ksgisang/AI-Watch-Tester/stargazers"><img src="https://img.shields.io/github/stars/ksgisang/AI-Watch-Tester?style=flat&logo=github" alt="GitHub Stars"></a>
</p>

---

## Demo

<p align="center">
  <!-- Replace with actual recording: docs/assets/demo.gif -->
  <img src="https://via.placeholder.com/800x450/1a1a2e/00d4aa?text=Demo+GIF+Coming+Soon" alt="AWT Demo" width="800">
  <br/>
  <em>Enter a URL → AI scans your site → generates test scenarios → executes with live screenshots → reports results.</em>
</p>

---

## Why AWT?

Most E2E testing tools still require you to **write code** or **record flows** before you can run a single test. AWT flips that model:

1. **You provide a URL** (and optionally a spec document).
2. **AI analyzes** the page structure, forms, navigation, and auth flows.
3. **AI generates** complete YAML test scenarios with selectors, test data, and assertions.
4. **Playwright executes** the scenarios in a real browser with humanized input.
5. **If a test fails**, the DevQA Loop kicks in — AI reads the failure, fixes the scenario or source code, and re-runs.

No test code. No recording. No manual maintenance.

---

## Features

| | Feature | Description |
|---|---------|-------------|
| :robot: | **AI Scenario Generation** | Upload a URL or spec doc (PDF/DOCX/MD) — AI creates E2E test scenarios |
| :globe_with_meridians: | **Real Browser Testing** | Playwright-driven Chromium with Bezier mouse curves and variable-speed typing |
| :recycle: | **Self-Healing DevQA Loop** | AI analyzes failures, patches code or scenarios, and re-runs automatically |
| :cloud: | **Cloud + Local** | Cloud mode (no install, browser dashboard) or local mode (real browser, full control) |
| :bar_chart: | **Live Dashboard** | Real-time screenshot streaming, step-by-step progress, event log |
| :page_facing_up: | **Document-Based Generation** | Feed PDF/DOCX/Markdown specs — AI generates scenarios from requirements |
| :test_tube: | **CI/CD Ready** | One-line `curl` integration with any pipeline |
| :jigsaw: | **Plugin Architecture** | Engines, matchers, AI adapters, and reporters are all swappable via registries |

---

## Quick Start

### Option A: Cloud (No Install)

```
1. Visit https://ai-watch-tester.vercel.app
2. Enter your target URL
3. Watch AI generate and execute tests
```

### Option B: Local

```bash
# Install
pip install aat-devqa
playwright install chromium

# Launch dashboard
aat dashboard
# Open http://localhost:9500
```

### Option C: From Source

```bash
git clone https://github.com/ksgisang/AI-Watch-Tester.git
cd AI-Watch-Tester
python -m venv .venv && source .venv/bin/activate
make dev          # install deps + playwright + pre-commit
make test         # verify everything works
aat dashboard     # launch web UI
```

---

## Usage

### CLI

```bash
# Guided mode — walks you through the entire flow
aat start

# Generate scenarios from a URL
aat generate --url https://example.com --provider openai

# Run scenarios
aat run scenarios/

# DevQA Loop — auto-fix failures
aat loop scenarios/ --approval-mode auto --max-iterations 3

# Validate scenario YAML
aat validate scenarios/login.yaml
```

### CI/CD (one-line)

```bash
curl -X POST https://your-awt-server.com/api/scan \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://staging.example.com"}'
```

### Dashboard

```bash
aat dashboard                    # default: http://localhost:9500
aat dashboard --port 8080        # custom port
```

The dashboard provides a 3-step workflow: **Setup** (config + AI provider) → **Prepare** (scan + generate scenarios) → **Execute** (run tests with live screenshots).

---

## Supported AI Providers

| Provider | Models | Cost | Setup |
|----------|--------|------|-------|
| **Ollama** | codellama, llama3, mistral | Free (local GPU) | `ollama serve` |
| **OpenAI** | gpt-4o, gpt-4o-mini | Pay-per-use | `export OPENAI_API_KEY=sk-...` |
| **Anthropic** | claude-sonnet-4-20250514 | Pay-per-use | `export ANTHROPIC_API_KEY=sk-ant-...` |

Configure in `aat.yaml` or via environment variables:

```yaml
ai:
  provider: openai        # openai | anthropic | ollama
  model: gpt-4o
  api_key: ${OPENAI_API_KEY}
```

---

## How It Compares

### vs testRigor

testRigor lets you write tests in plain English and handles execution + maintenance automatically. It is a mature enterprise SaaS.

| | **AWT** | **testRigor** |
|---|---------|---------------|
| Test authoring | AI generates from URL/docs — zero input | Plain English commands (you write) |
| Self-healing | DevQA Loop (AI re-generates) | Built-in auto-maintenance |
| Pricing | Free (MIT, self-host) | Enterprise pricing (~$800+/mo) |
| Open source | Yes | No |
| Setup time | Seconds (enter URL) | Minutes (write English scripts) |

**Choose AWT** if you want fully automated test generation with no scripting at all, or need a self-hostable open-source tool. **Choose testRigor** if you prefer writing plain-English test specs with enterprise support.

### vs Applitools

Applitools is the leader in **Visual AI** testing — pixel-level visual regression, cross-browser screenshots, and layout comparison via its Eyes SDK.

| | **AWT** | **Applitools** |
|---|---------|----------------|
| Primary focus | Functional E2E test generation + execution | Visual regression + cross-browser comparison |
| AI role | Generates entire test scenarios | Compares screenshots for visual differences |
| Standalone | Yes (full pipeline) | No (requires Cypress/Playwright/Selenium) |
| Pricing | Free (MIT) | Free tier + paid plans |

**Choose AWT** for AI-driven functional testing where you need scenarios generated automatically. **Choose Applitools** when pixel-perfect visual consistency across browsers is the priority. They complement each other — AWT generates and runs tests, Applitools can validate visual output.

### vs Playwright / Cypress

These are **excellent** browser automation frameworks that AWT is built on top of. The difference is **who writes the tests**: you (Playwright/Cypress) or AI (AWT). If your team wants full programmatic control, use them directly. If you want AI to handle test creation and maintenance, AWT fills that gap.

See [docs/COMPARISON.md](docs/COMPARISON.md) for a detailed breakdown against Playwright, Cypress, Testim, Katalon, and Mabl.

---

## Architecture

```
aat start / aat dashboard
       │
       ▼
┌─────────────────────────────────────────────┐
│                   CLI (Typer)                │
├─────────────────────────────────────────────┤
│              Core Orchestrator              │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ Executor │ │Comparator│ │ DevQA Loop  │ │
│  └────┬─────┘ └────┬─────┘ └──────┬──────┘ │
├───────┼─────────────┼──────────────┼────────┤
│  ┌────▼────┐  ┌─────▼─────┐  ┌────▼─────┐  │
│  │ Engine  │  │  Matcher  │  │ Adapter  │  │
│  │Registry │  │ Registry  │  │ Registry │  │
│  └─────────┘  └───────────┘  └──────────┘  │
│  web|desktop  template|ocr   openai|claude  │
│               feature|hybrid ollama         │
├─────────────────────────────────────────────┤
│  Models (Pydantic v2)  │  Config (Settings) │
└─────────────────────────────────────────────┘
```

All modules follow **ABC + plugin registry** pattern — extend the base class, register in `__init__.py`, done.

---

## Development

### Prerequisites

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — `brew install tesseract` / `apt install tesseract-ocr`
- Git

### Make Commands

| Command | Description |
|---------|-------------|
| `make dev` | Install all deps + Playwright + pre-commit |
| `make lint` | ruff check |
| `make format` | ruff format + auto-fix |
| `make typecheck` | mypy strict |
| `make test` | pytest |
| `make test-cov` | pytest + coverage report |
| `make clean` | Remove caches and build artifacts |

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development environment setup
- Code style (ruff + mypy strict)
- Test writing guidelines
- Pull request process
- Plugin development (adding new engines, matchers, or AI adapters)

```bash
git checkout -b feat/my-feature
# make changes
make format && make lint && make typecheck && make test
git commit -m "feat(scope): description"
# open PR
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start Guide](docs/QUICK_START.md) | Install, configure, run your first test |
| [API Reference](docs/API_REFERENCE.md) | REST API + WebSocket documentation |
| [Comparison](docs/COMPARISON.md) | AWT vs Playwright, Cypress, Testim, Katalon, Mabl |
| [FAQ](docs/FAQ.md) | Common questions |
| [CI/CD Guide](cloud/docs/CI_CD_GUIDE.md) | Pipeline integration (GitHub Actions, GitLab CI) |
| [Cloud Backend](cloud/README.md) | Self-hosting the cloud backend |

---

## License

[MIT](LICENSE) — free for personal and commercial use.

---

<p align="center">
  <sub>Built with Playwright, OpenCV, and a lot of AI. Made by <a href="https://github.com/ksgisang">@ksgisang</a>.</sub>
</p>
