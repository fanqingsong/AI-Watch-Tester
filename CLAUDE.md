# AAT (AI Auto Tester) — Project Guide

## Overview

AI-powered DevQA Loop orchestrator. Automates UI testing through image matching and repeats a loop where AI fixes code and retests upon failure.

## ⛔ AWT Testing Workflow (MUST FOLLOW)

When users request testing with AWT, you **must** follow these 4 steps in **order**.

### Step 1: SCAN
```bash
aat scan --url <URL>
```
→ Read `.aat/scan_result.json` and summarize to user → **Wait for approval**

### Step 2: GENERATE + PRESENT
Write scenario YAML → show to user → **Wait for approval**

### Step 3: EXECUTE (only after approval)
```bash
aat run --skill-mode --fast <scenario>
```
→ Stop immediately on failure → report to user → **Wait for instructions**

### Step 4: REPORT
Summarize results

### PROHIBITED
- Do NOT use `aat devqa` (runs entire pipeline without user checkpoints)
- Do NOT use `-y` / `--auto-approve`
- Do NOT run tests without user approval
- Do NOT auto-fix code/scenarios without user instruction

## ⛔ AI Security Rules — Approval Bypass Prevention (Layer 4)

**This section MUST be followed by all AI agents (Claude, GPT, Copilot, etc.)**

### ABSOLUTELY PROHIBITED
1. Do NOT directly set or forge `_AAT_APPROVAL_TOKEN` environment variable
2. Do NOT create, read, or modify `.aat/.approval_token_*` files
3. Do NOT modify security logic in `approval_token.py`, `scenario_reviewer.py`, `audit.py`
4. Do NOT bypass `/dev/tty` reading or manipulate `_is_interactive()` results
5. Do NOT delete or modify `.aat/audit.log`
6. Do NOT use or implement `--auto-approve`, `-y` flags
7. Do NOT bypass approval via stdin pipe like `echo "" | aat run`

### Approval Mechanism (4-Layer Defense)
- **Layer 1**: Direct `/dev/tty` read — prevents stdin pipe bypass
- **Layer 2**: One-time encrypted token — prevents environment variable forgery
- **Layer 3**: JSONL audit log — records all execution attempts
- **Layer 4**: This rule — prohibits AI agents from attempting bypass

### Proper AI Agent Behavior
- `aat run` MUST be executed in the user's terminal
- User MUST press Enter directly to approve
- Do NOT attempt to find ways to skip the approval prompt

## Key Documents

- `PM/기획서_v1.md` — Product spec (overall vision)
- `PM/Develop_Plan_v0.2.md` — Technical architecture
- `PM/설계서_v0.2.md` — **Detailed design spec** (this is the implementation standard)
- `PM/비즈니스_플랜_v0.2.md` — Business strategy
- `docs/RELEASE_GUIDE.md` — **Release guide** (PyPI/README/PR sync procedure)

## Tech Stack

- Python 3.11+, Typer (CLI), Pydantic v2, pydantic-settings
- Playwright (WebEngine), PyAutoGUI (DesktopEngine), OpenCV (image matching), pytesseract (OCR)
- anthropic SDK (Claude API), openai SDK, httpx (Ollama), Jinja2 (reports), SQLite (learning DB)
- Dev: ruff, mypy, pytest, pytest-asyncio, pre-commit

## Architecture Rules

- async by default (Playwright async native)
- ABC + @abstractmethod (instead of Protocol)
- core/models.py is leaf module (no internal imports)
- No circular dependencies: cli → core → engine/matchers/adapters/reporters → models
- Plugin registry: dictionary-based in each __init__.py

## Work Completion Procedure

For all work that modifies code, report as "complete" only after:

1. Run local tests (if applicable)
2. `git commit` & `git push`
3. Verify GitHub Actions CI passes (`gh run list --limit 1` to check status)
4. If CI fails, fix errors and repeat from step 1
5. Report work complete only when CI shows `"completed/success"`

Commit by phase or feature. Avoid commits that change 10+ files at once.

**For deployments requiring release**, follow checklist in `docs/RELEASE_GUIDE.md`.
Specifically, don't forget to sync Anthropic Skills PR and MCP Servers PR when MCP tools change.

## Commands

- `make dev` — Install dev environment
- `make lint` — ruff check
- `make format` — ruff format + fix
- `make typecheck` — mypy strict
- `make test` — pytest
- `make test-cov` — pytest + coverage

---

## WBS Progress Tracker

> Change `[ ]` → `[x]` when task complete, record completion date

### Phase 1: Foundation (Week 1, ~17h)

- [x] **AAT-001** Project skeleton (2h) — completed 2026-02-11
  - git init, pyproject.toml, directory structure, Makefile, pre-commit
  - Complete when: `make lint && make typecheck && make test` passes
- [x] **AAT-003** Enum definitions (1h) — completed 2026-02-11
  - ActionType, LabelPosition, AssertType, MatchMethod, Severity, StepStatus
- [x] **AAT-002** All Pydantic models (4h) — completed 2026-02-11
  - Config models, scenario models, result models, learning models + validator
  - Complete when: test_models.py passes
- [x] **AAT-007** Exception hierarchy (1h) — completed 2026-02-11
  - AATError-based 10 custom exceptions
- [x] **AAT-004** Config + pydantic-settings (3h) — completed 2026-02-11
  - YAML + env var + CLI flag 3-layer merge
- [x] **AAT-005** 5 ABC interfaces (3h) — completed 2026-02-11
  - BaseEngine, BaseMatcher, AIAdapter, BaseParser, BaseReporter
- [x] **AAT-006** Scenario YAML loader (3h) — completed 2026-02-11
  - YAML → Scenario, directory scan, variable substitution

### Phase 2: Engine + Matchers (Week 2~3, ~33h)

- [x] **AAT-010** WebEngine — Playwright (6h) — completed 2026-02-11
- [x] **AAT-011** Humanizer — Bezier mouse, variable typing (4h) — completed 2026-02-11
- [x] **AAT-012** Waiter — polling + hash stabilization (4h) — completed 2026-02-11
- [x] **AAT-013** TemplateMatcher — cv2.matchTemplate (5h) — completed 2026-02-11
- [x] **AAT-014** OCRMatcher — pytesseract (6h) — completed 2026-02-11
- [x] **AAT-015** FeatureMatcher — ORB/SIFT (4h) — completed 2026-02-11
- [x] **AAT-016** HybridMatcher — chain orchestrator (4h) — completed 2026-02-11

### Phase 3: Executor + CLI (Week 3~4, ~26h)

- [x] **AAT-020** StepExecutor (6h) — completed 2026-02-11
- [x] **AAT-021** Comparator (4h) — completed 2026-02-11
- [x] **AAT-022** CLI — init, config (4h) — completed 2026-02-11
- [x] **AAT-023** CLI — validate (3h) — completed 2026-02-11
- [x] **AAT-024** CLI — run (5h) — completed 2026-02-11
- [x] **AAT-025** CLI — report, learned (4h) — completed 2026-02-11 (stub)

### Phase 4: AI + Loop (Week 5~6, ~16h)

- [x] **AAT-030** ClaudeAdapter (4h) — completed 2026-02-11
- [x] **AAT-031** MarkdownReporter (3h) — completed 2026-02-11
- [x] **AAT-032** DevQALoop (6h) — completed 2026-02-11
- [x] **AAT-033** CLI — loop (3h) — completed 2026-02-11

### Phase 5: Analysis + Generation (Week 6~7, ~16h)

- [x] **AAT-040** MarkdownParser (3h) — completed 2026-02-11
- [x] **AAT-041** CLI — learn (4h) — completed 2026-02-11
- [x] **AAT-042** CLI — analyze (5h) — completed 2026-02-11
- [x] **AAT-043** CLI — generate (4h) — completed 2026-02-11

### Phase 6: Learning + Polish (Week 7~8, ~22h)

- [x] **AAT-050** LearnedStore — SQLite (4h) — completed 2026-02-11
- [x] **AAT-051** LearnedMatcher (3h) — completed 2026-02-11
- [x] **AAT-052** VisionAIMatcher — stub (2h) — completed 2026-02-11
- [x] **AAT-053** README + CONTRIBUTING (4h) — completed 2026-02-11
- [x] **AAT-054** Integration tests (6h) — completed 2026-02-11
- [x] **AAT-055** CI/CD + release prep (3h) — completed 2026-02-11

### Post-MVP: Quality Enhancement + Expansion

- [x] **AAT-060** GitHub repo creation + initial push — completed 2026-02-11
- [x] **AAT-061** CI/CD pipeline fixes (tesseract, playwright, pandas, ANSI) — completed 2026-02-11
- [x] **AAT-062** English localization — error messages, README, CONTRIBUTING to English — completed 2026-02-11
- [x] **AAT-063** TemplateMatcher bug fix — 1.0x scale missing — completed 2026-02-11
- [x] **AAT-064** OllamaAdapter — local LLM integration (codellama:7b) — completed 2026-02-12
- [x] **AAT-065** OpenAIAdapter — GPT-4o Vision support — completed 2026-02-12

### Post-MVP: Guide Mode + UX (AAT-070~076)

- [x] **AAT-070** Event/notification system — EventEmitter pattern for messenger integration
  - CLIHandler (terminal output), MessageBuffer (messenger batch send), future TelegramHandler/DiscordHandler extension
- [x] **AAT-071** AI Provider connection test — immediate connection check after API key entry
  - Claude: simple API call, OpenAI: model list check, Ollama: /api/tags verify
- [x] **AAT-072** Folder batch document analysis — full file scan+analysis when directory specified
- [x] **AAT-073** URL connection check — test target URL response verification
- [x] **AAT-074** Test cancellation — Ctrl+C immediate stop + partial result save
- [x] **AAT-075** `aat start` guide mode — entire flow as single interactive command
  - Setup→doc analysis→scenario generation→test→loop→report all in one
- [x] **AAT-076** Guide mode testing (events, connection, start_cmd)

### Post-MVP: Engine + Approval Mode (AAT-080~081)

- [x] **AAT-080** 3-Tier Approval Mode — Git branch isolation-based approval — completed 2026-02-12
  - ApprovalMode enum (manual/branch/auto), GitOps async subprocess wrapper
  - DevQALoop mode handlers (`_handle_manual/branch/auto`), `_read_source_files`
  - `--approval-mode/-a` CLI option, `skip_engine_lifecycle`, start_cmd deduplication
  - MarkdownReporter branch/commit info rendering
- [x] **AAT-081** DesktopEngine — PyAutoGUI + Playwright hybrid — completed 2026-02-12
  - PyAutoGUI (OS-level mouse/keyboard/screenshot) + Playwright (browser navigation)
  - ENGINE_REGISTRY registration, CLI dynamic engine selection (`config.engine.type: web | desktop`)

### Post-MVP: Web Dashboard (AAT-090~091)

- [x] **AAT-090** Web Dashboard (`aat dashboard`) — completed 2026-02-12
  - FastAPI + WebSocket real-time dashboard
  - 5-area UI: Scenarios | Config | Execution | Live Screenshot | Event Log
  - SubprocessManager, WebSocketEventHandler, ConnectionManager
  - REST API: config CRUD, scenario list, run/loop/stop, status, logs, screenshots
  - Real-time screenshot (960x540 JPEG 60% → base64 WS), approval modal, progress bar
  - pyproject.toml `[web]` optional dependency (fastapi, uvicorn, websockets)
  - Dark theme (#1a1a2e/#16213e/#e0e0e0, accent #00d4aa)
- [x] **AAT-091** Dashboard UI/UX overhaul — 3-step Z-pattern layout — completed 2026-02-13
  - 5-panel grid → 3-step Z-pattern (Setup → Prepare → Execute)
  - Server control: SubprocessManager `start_raw(cmd, cwd)` + `on_line` callback + auto port extraction
  - 4 server endpoints (start/stop/status/logs), 2 doc upload (upload/list)
  - Drag&drop doc upload, mini log + Event Log dual display
  - python-multipart dependency added, responsive (1100px and below single column stack)
- [x] **AAT-092** Scenario management improvements — completed 2026-02-13
  - Custom path support: `GET /api/scenarios?path=` query parameter
  - Scenario YAML upload: `POST /api/scenarios/upload` (.yaml/.yml only)
  - Selective execution: `scenario_ids` parameter to run/loop only selected scenarios
  - UI: path input+Load, Select All/Clear, selection count, dynamic button labels

### Post-MVP: State Teardown (AAT-093~095)

- [x] **AAT-093** Dynamic variable substitution — `{{timestamp}}`, `{{datetime}}`, `{{random}}`, `{{uuid}}`, `{{env.VAR}}` — completed 2026-03-26
  - `_resolve_var()` + `_DYNAMIC_VARS` frozenset, `find_unresolved_vars()` exclusion logic
  - 16 tests pass

- [x] **AAT-094** teardown section parsing — TeardownStep model + Scenario field — completed 2026-03-26
  - TeardownStep: api_call | db_query | shell common model
  - Scenario.teardown: list[TeardownStep] = [] (backward compatible)
  - 12 tests, {{timestamp}} YAML substitution included

- [x] **AAT-095** TeardownExecutor engine + real-world verification — completed 2026-03-26
  - TeardownExecutor: api_call(httpx) / db_query(asyncpg+sqlite3) / shell(subprocess)
  - run(): failure swallow (log only) — does not affect test result
  - run_cmd.py integration + `--skip-teardown` option
  - SC-CR001_register.yaml: dynamic email(`test+{{timestamp}}@ailooplab.com`) + `{{random}}` academy name
  - scripts/cleanup_firebase_user.py: Admin SDK + REST API (no-op without credentials)
  - tests/test-teardown-loop.sh: N consecutive run script
  - Verified: 3 consecutive runs 30/30 success (no email duplicates)

### Post-MVP: Visual Regression (AAT-100~102)

- [x] **AAT-100** VisualComparator — OpenCV SSIM + diff image generation — completed 2026-04-03
  - SSIM (Wang et al. 2004): OpenCV direct implementation, no external dependencies
  - 3-panel diff image: Baseline | Current | Diff (red overlay)
  - Single diff overlay image generation

- [x] **AAT-101** BaselineStore + models — baseline save/load/manage — completed 2026-04-03
  - `.aat/baselines/{scenario_id}/` structure, meta.json included
  - StepDiffResult, VisualDiffReport, BaselineMeta Pydantic models
  - save/load/list/clear/clear_all methods

- [x] **AAT-102** CLI commands (snapshot, diff, baseline) + MCP tools — completed 2026-04-03
  - `aat snapshot <path>` — capture baseline after scenario execution
  - `aat diff <path> --threshold 0.95` — compare vs baseline + Rich table
  - `aat baseline list/clear` — baseline management
  - MCP: `aat_snapshot`, `aat_diff` tools added
  - 20 unit tests pass

- [x] **AAT-103** PR comment GitHub Action + `--format=github` — completed 2026-04-03
  - `aat diff --format=github` → markdown output for PR comments
  - `aat diff --format=json` → JSON output
  - `.github/workflows/visual-regression.yml` template
  - PR comments: auto-create/update (update existing comment, spam prevention)
  - 24 unit tests pass

- [x] **AAT-104** Watch mode — file change detection + auto test execution — completed 2026-04-03
  - `aat watch <scenarios> --url <URL>` — auto test on file change
  - watchfiles (Rust-based) + polling fallback
  - Scenario change → rerun that scenario only, source change → run all scenarios
  - Auto visual diff included if baseline exists
  - MCP: `aat_watch` tool added
  - `[watch]` optional dependency (watchfiles)
  - 18 unit tests pass

### Post-MVP: Enhancement (AAT-105~107)

- [x] **AAT-105** Responsive screenshots `--responsive` / `--viewport` — completed 2026-04-04
  - 3 viewport types: mobile (375x812), tablet (768x1024), desktop (1280x720)
  - `aat snapshot --responsive` / `aat diff --responsive` — capture/compare all 3 at once
  - `--viewport 375x812` single specification also supported
  - BaselineStore viewport suffix: `step001-mobile_after.png`
  - RESPONSIVE_VIEWPORTS constant (gstack compatible)

- [x] **AAT-106** Console error collection `--console` / `--console-fail` — completed 2026-04-04
  - Playwright `page.on('console')` / `page.on('pageerror')` based
  - JS errors trigger ⚠️ warning even if screenshot passes
  - `--console-fail`: FAIL if errors present
  - ConsoleCollector class (visual/console_collector.py)

- [x] **AAT-107** Auto-open diff results `--open` — completed 2026-04-04
  - `aat diff --open` → auto-open FAIL diff images in macOS Preview / xdg-open
  - MCP: `aat_snapshot`, `aat_diff` parameters added
  - 25 unit tests pass (test_enhancements.py)

### Post-MVP: Approval Security (AAT-108)

- [x] **AAT-108** 4-Layer Approval Security — AI agent approval bypass prevention — completed 2026-04-04
  - Layer 1: Direct `/dev/tty` read — stdin pipe bypass prevention (`scenario_reviewer.py`, `loop.py`)
  - Layer 2: One-time encrypted token — `_AAT_DEVQA_APPROVED` env var → `_AAT_APPROVAL_TOKEN` + disk file verification
  - Layer 3: JSONL audit log — record all execution attempts in `.aat/audit.log`
  - Layer 4: CLAUDE.md + MCP instructions specify AI security rules
  - `approval_token.py`: `generate_token()`, `store_token()`, `validate_and_consume()`
  - `audit.py`: `AuditEntry` Pydantic model, `log_audit()`, `read_audit()`
  - `run_cmd.py`, `devqa_cmd.py`, `watch_cmd.py` integration
  - 17 security tests pass (test_approval_security.py)

---

## Collaboration Project Integration (ClasRing + DSL)

### My Role
Main role is E2E testing code made by Kim (ClasRing) and DSL using AWT.
Deliver test results to shared directory.

### Shared Directory Paths
- Where I receive:
  - `~/Documents/Projects/shared/handoff/dsl-to-lee/`
    → Code variations from DSL come here.
      E2E test with AWT required.
  - `~/Documents/Projects/shared/handoff/kim-to-lee/`
    → Code Kim directly requests testing for comes here.

- Where I send:
  - `~/Documents/Projects/shared/handoff/lee-to-dsl/`
    → Put AWT test results (last_run.json, screenshots) here.
      DSL reflects this in scoring.
  - `~/Documents/Projects/shared/handoff/lee-to-kim/`
    → Put test results to deliver to Kim here.

### Test Result Delivery Rules
- When putting results, must follow this structure:
  ```
  lee-to-dsl/ or lee-to-kim/
  └── page-name_YYYYMMDD/       (e.g., admin-dashboard_20260327)
      ├── last_run.json          (AWT execution result)
      ├── screenshots/           (per-step screenshots)
      └── summary.md             (pass/fail summary, issues found)
  ```

---

## Branch Strategy

- **main**: Single development+deployment branch. All work directly on main.
- **dev**: Archive (no longer used). Keep synced with main.
- Before starting work, always verify `git checkout main`.
- Vercel: main = Production
- Render: main auto-deploy

---

## Current Status

- **Current phase**: 4-Layer Approval Security complete (AAT-108)
- **Completed**: Phase 1~6 (Ultra-MVP) + AAT-060~065 + AAT-070~076 + AAT-080~081 + AAT-090~092 + AAT-093~095 + AAT-100~108 (Post-MVP)
- **Blockers**: None
- **Python**: 3.12.12 (.venv), `source .venv/bin/activate`
- **GitHub**: https://github.com/ksgisang/AI-Watch-Tester (public)
