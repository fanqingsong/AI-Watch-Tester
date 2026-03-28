# AWT (AI Watch Tester) — AI Agent Rules

> This file is for **AI coding assistants** (Gemini, Copilot, Codex, Cursor, Claude Code, etc.).
> Follow these rules when the user asks you to use AWT for testing.

## ⛔ MANDATORY WORKFLOW — 4 Steps, No Exceptions

When the user asks you to test a web application with AWT, you **MUST** follow these 4 steps in order. **Do NOT skip, combine, or automate any step.**

### Step 1: SCAN
```bash
aat scan --url <URL>
```
Read `.aat/scan_result.json` and present a summary to the user:
- How many elements were found (inputs, buttons, links)
- Ask: *"Should I create a test scenario based on these elements?"*
- **WAIT for user response.**

### Step 2: GENERATE + PRESENT
Write a YAML scenario using data from `scan_result.json`.
Show the full scenario to the user in a readable format.
Ask: *"Should I run this test? Or do you want me to change anything?"*
- **WAIT for user approval.**
- If user requests changes → modify and show again.

### Step 3: EXECUTE (only after user says "go ahead")
```bash
aat run --skill-mode --fast <scenario_file>
```
If a step fails → **STOP immediately**. Report:
- Which step failed and why
- What the possible cause is
- Ask: *"Should I fix the scenario, or fix the source code?"*
- **WAIT for user instruction.** Do NOT auto-fix.

### Step 4: REPORT
When all steps pass, summarize the results to the user.

## ⛔ BANNED — Never Do These

| Banned | Why |
|--------|-----|
| `aat devqa` | Runs entire pipeline without user checkpoints |
| `-y` / `--auto-approve` | Bypasses user approval gate |
| Auto-fixing code without asking | User must approve all changes |
| Auto-retrying failed tests | User must decide what to fix first |
| `headless: true` | User must see the browser |
| Guessing element names | Always scan first, use real data |
