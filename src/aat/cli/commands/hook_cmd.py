"""
════════════════════════════════════════════════════════════════════════════════
                   🪝 Git Hook Management Module
════════════════════════════════════════════════════════════════════════════════

📋 MODULE PURPOSE
───────────────────────────────────────────────────────────────────────────────
Manages Git post-commit hooks for automatic page scanning when UI files change.
Enables continuous visual regression detection by automatically running aat scan
after commits containing UI-related file modifications.

🎯 USE CASE EXAMPLE
───────────────────────────────────────────────────────────────────────────────
```bash
# Install post-commit hook
aat hook install

# Remove AWT hook
aat hook uninstall

# Manual hook execution (for testing)
.git/hooks/post-commit
```

⚙️  GIT HOOK ARCHITECTURE
───────────────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│                  Auto-Scan Git Hook System                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Hook Installation                                         │  │
│  │    → Create .git/hooks/post-commit                           │  │
│  │    → Add executable permission (chmod +x)                     │  │
│  │    → Preserve existing hooks (append mode)                    │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 2. Post-Commit Trigger                                        │  │
│  │    → Runs automatically after each git commit                  │  │
│  │    → Checks for UI file changes (*.dart, *.tsx, *.vue)       │  │
│  │    → Triggers: git diff --name-only HEAD~1 HEAD               │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 3. UI File Detection                                         │  │
│  │    → Pattern matching: *.dart, *.tsx, *.jsx, *.vue, *.html │  │
│  │    → Grep for changed files matching patterns                 │  │
│  │    → Exit if no UI files changed                              │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 4. Auto-Scan Execution                                       │  │
│  │    → Read URL from existing .aat/scan_result.json              │  │
│  │    → Run: aat scan --url $URL --compare $PREV_SCAN             │  │
│  │    → Show element additions, removals, movements                │  │
│  │    → Non-failing (errors don't block commit)                  │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │ 5. Result Reporting                                         │  │
│  │    → Display scan diff in commit output                       │  │
│  │    → Show changed element counts                             │  │
│  │    → Suggest manual scan if baseline missing                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

📦 CORE FUNCTIONALITY
───────────────────────────────────────────────────────────────────────────────
- **hook installation**: Create and configure post-commit hooks
- **UI file detection**: Pattern matching for frontend file types
- **auto-scan triggering**: Automatic page scanning on UI changes
- **comparison mode**: Diff against previous scan for change detection
- **non-blocking**: Hook failures don't prevent git commits
- **hook management**: Install and remove AWT hooks cleanly

⚠️  LIMITATIONS & NOTES
───────────────────────────────────────────────────────────────────────────────
- Requires git repository with .git/hooks directory
- Only works with local git commits (not CI/CD systems)
- Depends on existing .aat/scan_result.json for URL
- Hook execution adds time to git commit process
- May not work with all git configurations or hooks

💡 BEST PRACTICES
───────────────────────────────────────────────────────────────────────────────
- Install hook in project root for proper git integration
- Review scan diff in commit output for UI change awareness
- Ensure aat scan has been run at least once for URL reference
- Remove hook if it interferes with workflow or slows commits
- Use with aat watch for comprehensive change monitoring
- Combine with visual regression testing for complete coverage

🎯 WHEN TO USE
───────────────────────────────────────────────────────────────────────────────
✅ Continuous monitoring of UI changes during development
✅ Automatic visual regression detection on commits
✅ Teams working on UI-heavy applications
✅ Projects requiring frequent visual consistency checks
❌ Not needed for CI/CD pipelines (use aat diff instead)
❌ Not suitable for projects without UI components

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from pathlib import Path

import typer

hook_app = typer.Typer(help="Git hook management for auto-scan.")

_HOOK_SCRIPT = """\
#!/bin/sh
# AWT post-commit hook — auto-scan on UI file changes
# Installed by: aat hook install
# Remove with:  aat hook uninstall

# Check for UI-related file changes in the last commit
UI_PATTERNS="*.dart *.tsx *.jsx *.vue *.svelte *.html *.css *.scss"
CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null \\
  | grep -E '\\.(dart|tsx|jsx|vue|svelte|html|css|scss)$')

if [ -n "$CHANGED" ]; then
    echo "[AWT] UI files changed — running scan diff..."

    # Find scan_result.json
    SCAN_FILE=".aat/scan_result.json"
    if [ -f "$SCAN_FILE" ]; then
        # Read URL from existing scan
        URL=$(python3 -c "import json; print(json.load(open('$SCAN_FILE'))['url'])" 2>/dev/null)
        if [ -n "$URL" ]; then
            aat scan --url "$URL" --compare "$SCAN_FILE" 2>/dev/null || true
        fi
    else
        echo "[AWT] No previous scan found. Run: aat scan --url <your-app-url>"
    fi
fi
"""


@hook_app.command(name="install")
def install_hook() -> None:
    """Install post-commit git hook for auto-scan."""
    hooks_dir = Path.cwd() / ".git" / "hooks"
    if not hooks_dir.exists():
        typer.echo("Not a git repository. Run from project root.")
        raise typer.Exit(1)

    hook_path = hooks_dir / "post-commit"

    # Don't overwrite existing hook — append
    if hook_path.exists():
        content = hook_path.read_text(encoding="utf-8")
        if "AWT post-commit" in content:
            typer.echo("[AWT] Hook already installed.")
            return
        # Append to existing hook
        with open(hook_path, "a", encoding="utf-8") as f:
            f.write("\n" + _HOOK_SCRIPT)
    else:
        hook_path.write_text(_HOOK_SCRIPT, encoding="utf-8")

    hook_path.chmod(0o755)
    typer.echo("[AWT] Post-commit hook installed.")
    typer.echo(f"  Location: {hook_path}")
    typer.echo("  Triggers: on commits with UI file changes (.dart/.tsx/.vue/...)")


@hook_app.command(name="uninstall")
def uninstall_hook() -> None:
    """Remove AWT post-commit hook."""
    hook_path = Path.cwd() / ".git" / "hooks" / "post-commit"
    if not hook_path.exists():
        typer.echo("[AWT] No post-commit hook found.")
        return

    content = hook_path.read_text(encoding="utf-8")
    if "AWT post-commit" not in content:
        typer.echo("[AWT] No AWT hook found in post-commit.")
        return

    # Remove AWT section
    lines = content.split("\n")
    new_lines: list[str] = []
    skip = False
    for line in lines:
        if "AWT post-commit hook" in line:
            skip = True
            continue
        if skip and line.startswith("fi"):
            skip = False
            continue
        if not skip:
            new_lines.append(line)

    remaining = "\n".join(new_lines).strip()
    if remaining and remaining != "#!/bin/sh":
        hook_path.write_text(remaining + "\n", encoding="utf-8")
        typer.echo("[AWT] AWT hook removed (other hooks preserved).")
    else:
        hook_path.unlink()
        typer.echo("[AWT] Post-commit hook removed.")
