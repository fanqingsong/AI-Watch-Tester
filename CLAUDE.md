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
- Do NOT use `-y` / `--auto-approve` (these flags don't exist in codebase)
- Do NOT run tests without user approval
- Do NOT auto-fix code/scenarios without user instruction

### Note on `aat devqa`
The `aat devqa` command is **ALLOWED** when used properly with human approval at each checkpoint. It does NOT bypass approval mechanisms despite its name suggesting automation.

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

- `docs/RELEASE_GUIDE.md` — **Release guide** (PyPI/README/PR sync procedure)
- `docs/AWT_Agent_Skill_Comprehensive_Guide.md` — Complete AWT skill usage guide
- `docs/AWT_Cost_Optimization_Plan.md` — Cost analysis and optimization strategies
- `docs/AGENT_BROWSER_MULTI_TURN.md` — How `aat agent chat` drives the browser (tool-calling) and keeps browser state across multi-turn sessions
- `CLAUDE.md` — This file: project architecture, workflow, and development guidelines
- `README.md` — User-facing documentation and feature overview

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

## WBS History (Completed)

**Ultra-MVP (Phase 1-6)**: Foundation → Engine+Matchers → Executor+CLI → AI+Loop → Analysis+Generation → Learning+Polish (2026-02-11)

**Post-MVP Quality**:
- AAT-060~065: GitHub repo, CI/CD fixes, i18n, bug fixes, Ollama/OpenAI adapters (2026-02-11~12)
- AAT-070~076: Guide mode + UX (events, connection test, batch analysis, cancellation, `aat start`) (2026-02-12)
- AAT-080~081: 3-Tier Approval Mode + DesktopEngine (2026-02-12)
- AAT-090~092: Web Dashboard (FastAPI+WebSocket, Z-pattern UI, scenario management) (2026-02-12~13)
- AAT-093~095: State Teardown (dynamic variables, teardown section, TeardownExecutor) (2026-03-26)
- AAT-100~104: Visual Regression (VisualComparator, BaselineStore, snapshot/diff CLI, PR workflow, watch mode) (2026-04-03)
- AAT-105~107: Enhancements (responsive screenshots, console collection, auto-open diff) (2026-04-04)
- AAT-108: 4-Layer Approval Security (2026-04-04)

---

## Collaboration Project Integration (ClasRing + DSL)

### My Role
Main role is E2E testing code made by Kim (ClasRing) and DSL using AWT.
Deliver test results to shared directory.

### Shared Directory Paths
- Where I receive:
  - `~/Documents/Projects/shared/handoff/dsl-to-lee/`
    → Code variations from DSL come here. E2E test with AWT required.
  - `~/Documents/Projects/shared/handoff/kim-to-lee/`
    → Code Kim directly requests testing for comes here.

- Where I send:
  - `~/Documents/Projects/shared/handoff/lee-to-dsl/`
    → Put AWT test results (last_run.json, screenshots). DSL reflects this in scoring.
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

- **Phase**: Post-MVP complete, all AAT-001~108 done
- **Blockers**: None
- **Python**: 3.11+ (tested on 3.11, 3.12, 3.13), `source .venv/bin/activate`
- **GitHub**: https://github.com/ksgisang/AI-Watch-Tester (public)
