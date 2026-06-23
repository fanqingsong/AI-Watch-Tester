# AWT (AI Watch Tester) Comprehensive Project Analysis and Business Strategy Report

**Date:** 2026-03-26
**Subject:** Identifying structural weaknesses in AWT project, analyzing performance bottleneck cases, and business/technical improvement directions for enterprise productization

---

## 1. Project Overview and Technical Architecture

AWT is an **"AI-based DevQA Loop Orchestrator"** that combines Playwright, computer vision (OpenCV, OCR), and generative AI (Claude, GPT-4o, etc.) to perform UI automated testing, and when errors occur, analyzes and fixes code itself to re-execute.

### Key Components
1. **`src/aat` (Core Engine):** Typer-based CLI and Playwright control, visual matching (hybrid) engine, etc. Acts as AWT's brain.
2. **`cloud/` (Dashboard):** FastAPI + Supabase based dashboard for real-time test progress monitoring and result verification.
3. **`mcp/` & `awt-skill/`:** Integration interfaces that allow AI coding assistants to directly execute AWT when installed as agent skills in external environments (Claude Code, Cursor, etc.).

---

## 2. Identified Critical Weaknesses

Despite powerful self-healing capabilities, AWT has fatal weaknesses in code structure that block enterprise adoption.

### A. Excessive Dependence on Visual Elements
- AWT depends on "visible images and text (OCR, Template)" rather than unique DOM attributes (`data-testid`, etc.).
- When multi-language support (i18n) is applied or themes like dark mode are changed, visibility changes and tests can completely break — **Critical maintainability limitation (Flaky Tests)**.

### B. AI Manipulation Risk and Lack of State Isolation in DevQA Loop
- **AI Manipulation Risk:** In `auto` or `branch` mode, when test fails, AI's suggested code fix overwrites local files directly and re-executes. The fix validation logic (`_validate_fix`) is very loose, posing high risk of overwriting with code that destroys business logic (including security vulnerability injection).
- **State Isolation Failure:** No database rollback or test sandbox state initialization. This guarantees no test idempotency.

### C. Blindness of Coordinate Clicking (Actionability Limitation)
- When finding elements, calculates center `(x, y)` screen coordinates and simply clicks mouse.
- Even when actually not clickable (Not Actionable) due to transparent overlays or loading spinners, test may falsely pass, or high probability of clicking wrong location.

---

## 3. Case Analysis: Signup-Dashboard "48-Minute Bottleneck" Incident

A simple signup-to-dashboard test took extreme 48 minutes because **"AI fell into infinite failure loop (Death Spiral) in non-idempotent environment"**.

1. **State Pollution Occurs:** Dashboard entry (Step 3) temporarily fails to find element, causing first failure. DevQA loop attempts fix through AI, then restarts from beginning (signup, Step 1).
2. **Logical Infinite Loop:** Previous attempt's signup loaded email to DB. Restarted Step 1 fails with "already registered ID" error, causing second failure. AWT asks AI to analyze error again and wastes effort fixing code.
3. **Excessive Tier 3 Vision AI Calls:** Continuously calls slow, expensive Claude/GPT Vision AI for every failure and step, with request time (10+ seconds per sheet) and humanization (mouse movement delay, etc.) delays accumulating for 48 minutes.

---

## 4. Re-evaluation of DOM vs Canvas (Flutter) Integration Vision and Overcoming Limitations

AWT evolved beyond general DOM-based navigation toward extreme vision dependence (OpenCV, OCR, Vision AI) because of innovative vision to create **"Universal testing tool that works identically in both DOM and Canvas (Flutter Web) environments"**.
This vision-based approach (Visual Testing) overcomes limitations where major QA tools (Cypress, etc.) are completely powerless in webassembly or canvas environments — **AWT's powerful weapon and differentiator (USP)**.

However, **"Using expensive, slow weapon (Vision) designed for hardest area (Canvas) equally on easiest area (DOM)"** became decisive cause of aforementioned 48-minute bottleneck. To break through and perfectly catch both rabbits (DOM and Canvas), hybrid strategy is:

1. **Platform Auto-Detection Router:**
   - On page entry, scan current DOM tree in 0.1 seconds to diagnose whether page is normal HTML-based or Flutter Web (presence of `<flt-glass-pane>`, `<canvas>`).
2. **DOM → Canvas Waterfall Search Strategy:**
   - If DOM environment, unconditionally prioritize fast, reliable **DOM matcher (Tier 0)** to perform native click in 0.1 seconds.
   - Only when absolutely cannot find in DOM, or diagnosed as Canvas environment in initial diagnosis, then enter camera mode (Tier 1~3: Template → OCR → Vision AI).
3. **Semantics Tree (Accessibility Tree) Hook-up:**
   - For Flutter Web, utilize Semantics Nodes rendered in background to build high-speed bypass that finds x, y coordinates of text inside Canvas in 0.1 seconds without video recognition.

---

## 5. Productization and Business Strategy (Go-to-Market Strategy)

For AWT to become trusted enterprise B2B SaaS product or core QA infrastructure, technical "restraint and safety measures" are most important.

1. **Shift from "Full Autopilot" to "Approval-based Copilot":**
   - `AUTO` mode that arbitrarily overwrites code is most undesirable element in enterprise environments.
   - On failure, must **only show error screen analysis results and code fix diff as "Pull Request (PR) draft"**. Final merge must always go through human developer (Human-in-the-Loop) approval to resolve security anxiety.
2. **Flawless Test Sandboxing (Teardown Hooks):**
   - Must trust safety measures that clean database before/after test or completely volatilize ephemeral browser context as business selling point.
3. **DOM-based Hybrid Search Mandatory:**
   - Rather than showing off fancy "eyes (Vision AI)", must prioritize stable testing enterprises want most (DOM attribute-based testing) as first matcher to break "flaky" perception.

---

## 6. Future Source Code and Operation Modification Directions (Action Items)

Specific modification directions to introduce at AWT source code level to compensate business and technical weaknesses:

- [ ] **Introduce Tier 0 Locator Engine (DOM Selector Priority)**
  - Add module to `hybrid.py` as highest priority (before Tier 1) that prioritizes HTML DOM structure like `data-testid`, `id`, `name` for fast, reliable element search.
- [ ] **Explicit State Destruction Prevention (State Teardown / Rollback)**
  - Add `teardown_query` (DB initialization script execution) or API hook (Webhook) support to YAML scenario skeleton.
  - For logic where idempotency is impossible, apply `--no-loop` flag by default to immediately terminate (Fail-fast) on failure without retry.
- [ ] **Strengthen DevQA Loop Validation and Remove Auto Mode**
  - Discard `_handle_auto` mode in `loop.py` or hide under strong warning flag.
  - Significantly strengthen `_validate_fix()` logic (dependency tree violation check, AST integrity analysis), operate system mainly on `_handle_branch`.
- [ ] **Strengthen Coordinate Clicking Logic**
  - Before `mouse.click(x, y)` in `web.py`, add prerequisite condition using Playwright's `waitForFunction` etc. to probe element visibility and interaction possibility (Actionable).
