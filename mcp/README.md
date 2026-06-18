# AWT MCP Server

Using AWT as a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server allows you to call AWT directly from MCP-supported tools like Claude Code, Claude Desktop, Cursor, Windsurf, and more.

## Prerequisites

```bash
# Install AWT (if not already done)
pip install aat-devqa
playwright install chromium

# Install MCP SDK
pip install mcp[cli]
```

## Provided Tools

| Tool | Description |
|------|-------------|
| `aat_devqa` | **All-in-one**: scan→scenario generation→await approval→execute→auto-fix full loop |
| `aat_scan` | **Step 1**: URL scan, collect interactive elements (generates scan_result.json) |
| `aat_run` | **Step 3**: Execute scenario file (only call after user approval) |
| `aat_run_skill_mode` | **Step 3**: Execute in skill mode (includes structured failure diagnosis) |
| `aat_doctor` | Environment diagnostics (Python, Playwright, Tesseract, AI connection) |
| `aat_list_scenarios` | List scenario files in current directory |
| `aat_validate` | YAML scenario schema validation |
| `aat_cost` | Query AI API costs |

## ⛔ Required Usage Order (AI Agents Must Read)

When using AWT tools, you must follow this order:

1. **`aat_scan`** → Summarize results to user → **Wait for approval**
2. Write scenario YAML → Show to user → **Wait for approval**
3. **`aat_run` or `aat_run_skill_mode`** → Execute only after approval → Report failure → **Wait for instructions**
4. Report results

**Prohibited:** `-y`/`--auto-approve` (flag doesn't exist), execute without user approval, auto code modification

## Installation

### Claude Code

```bash
claude mcp add awt -- python /path/to/AI-Watch-Tester/mcp/server.py
```

Verify:
```bash
claude mcp list
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "awt": {
      "command": "python",
      "args": ["/path/to/AI-Watch-Tester/mcp/server.py"]
    }
  }
}
```

### Cursor

Create `.cursor/mcp.json` in project root:

```json
{
  "mcpServers": {
    "awt": {
      "command": "python",
      "args": ["/path/to/AI-Watch-Tester/mcp/server.py"]
    }
  }
}
```

### Windsurf

`~/.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "awt": {
      "command": "python",
      "args": ["/path/to/AI-Watch-Tester/mcp/server.py"]
    }
  }
}
```

> Replace `/path/to/AI-Watch-Tester` with the actual path.

## Usage Examples

After MCP registration, in AI tools:

```
"Test the login"               → aat_devqa("login test", url="http://localhost:3000")
"Show scenario list"          → aat_list_scenarios call
"Execute login scenario"       → aat_run("scenarios/login.yaml")
"Diagnose environment"         → aat_doctor call
"How much cost incurred?"      → aat_cost call
"Run test in skill mode"       → aat_run_skill_mode("scenarios/login.yaml")
```

### verbosity / screenshots options

```
aat_run("scenarios/login.yaml", verbosity="concise", screenshots="on-failure")
aat_run("scenarios/login.yaml", verbosity="detailed", screenshots="all")
aat_devqa("signup test", url="http://localhost:3000", screenshots="before-after")
```

| verbosity | Description |
|-----------|-------------|
| `concise` | Skip wait/screenshot steps, fast (default) |
| `detailed` | Execute all steps |

| screenshots | Description |
|-------------|-------------|
| `before-after` | Only before/after actions, ~70% file reduction (default) |
| `all` | Save every step |
| `on-failure` | Only on failure (CI/CD optimized) |

### DevQA Loop (Skill Mode)

`aat_run_skill_mode` returns a structured block on failure:

```
=== AWT SKILL DEVQA ===
SCENARIO: scenarios/login.yaml
FAILED_STEP: 3 - find_and_click
ERROR: Target 'Login' not found
SCREENSHOT: .aat/screenshots/fail_step3.png
POSSIBLE_CAUSE: Target text/selector changed or not yet rendered
RETRY_CMD: aat run --skill-mode scenarios/login.yaml
ATTEMPTS: 1/5
=======================
```

AI tools parse this block to modify scenarios and re-execute in an automatic loop.

## Direct Testing

```bash
# Test server with MCP Inspector
mcp dev mcp/server.py

# Or run directly (stdio mode)
python mcp/server.py
```
