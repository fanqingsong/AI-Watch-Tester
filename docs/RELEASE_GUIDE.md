# AWT Release Guide

> Deployment guide organized to ensure consistent procedures across sessions.
> All maintainers follow this document.

## 5 Deployment Targets

| # | Target | Auto/Manual | Trigger |
|---|---|---|---|
| 1 | **GitHub Repository** | Auto | `git push origin main` |
| 2 | **PyPI** (aat-devqa) | Semi-auto | `git tag v*` → push → CI builds + uploads |
| 3 | **README.md** | Manual | Direct edit + commit when adding features |
| 4 | **Anthropic Skills PR** | Manual | PR update or new PR creation |
| 5 | **MCP Servers PR** | Manual | PR update or new PR creation |

---

## 1. GitHub Repository Deployment (after each work completion)

```bash
# 1. Verify tests pass
make lint && make typecheck && make test

# 2. Commit & push
git add <files>
git commit -m "feat(...): description"
git push origin main

# 3. Verify CI passes
gh run list --limit 1
# status should be "completed/success"
```

**Rules:**
- Limit to 10 files changed per commit
- Fix and retry if CI fails
- Work directly on main branch

---

## 2. PyPI Deployment (after major feature completion)

### Deployment Conditions
- When completing a day's work
- When completing major features (Phase level)
- After stability confirmation (CI pass + local tests complete)

### Procedure

```bash
# 1. Bump pyproject.toml version
# Check current version:
grep '^version' pyproject.toml
# version = "1.6.1"

# Version rule: major.minor.patch
# - patch: bug fixes, small improvements
# - minor: new feature additions
# - major: breaking changes

# 2. Update version
# Modify version = "X.Y.Z" in pyproject.toml

# 3. Commit
git add pyproject.toml
git commit -m "chore: bump version to X.Y.Z"
git push origin main

# 4. Verify CI passes
gh run list --limit 1
# ⚠️ No tags before CI passes!

# 5. Create & push tag (triggers CI auto-deployment)
git tag vX.Y.Z
git push origin vX.Y.Z

# 6. Verify deployment
gh run list --limit 1 --workflow publish.yml
# status should be "completed/success"

# 7. Verify on PyPI
# https://pypi.org/project/aat-devqa/
```

### Deployment CI Operation (`.github/workflows/publish.yml`)
1. Detect tag (v*) push
2. Run lint + typecheck + test
3. `python -m build` → create wheel/sdist
4. Validate tag matches pyproject.toml version
5. Upload to PyPI with twine
6. Auto-create GitHub Release (--latest)

### ⚠️ Notes
- **Tag and pyproject.toml version MUST match** (v1.7.0 ↔ version = "1.7.0")
- Use editable mode during development: `pip install -e ".[dev]"`
- For testing in other projects: `bash ~/Documents/Projects/AI_Auto_Tester/install-dev.sh`

---

## 3. README.md Update (when adding features)

### When Update is Needed
- When adding new CLI commands
- When adding new options (flags)
- When adding new MCP tools
- When changing supported platforms/tools

### Features Currently Missing from README (as of 2026-04-04)

| Feature | In README |
|---|---|
| `aat snapshot` / `aat diff` / `aat baseline` | ❌ No |
| `aat watch` | ❌ No |
| `--responsive` / `--viewport` | ❌ No |
| `--console` / `--console-fail` | ❌ No |
| `--open` | ❌ No |
| MCP tools: `aat_snapshot`, `aat_diff`, `aat_watch` | ❌ No |
| GitHub Action: visual-regression.yml | ❌ No |

### README Update Procedure

```bash
# 1. Edit README.md
# Add to "What it does" or "Features" section

# 2. Sync Korean README if applicable
# README.ko.md

# 3. Commit
git add README.md README.ko.md
git commit -m "docs(readme): add visual regression & enhancement features"
git push origin main
```

### README Structure Guide
- Add new features to the bottom of "What it does" section
- CLI usage in code blocks
- Update comparison tables (vs competitors) if applicable
- Add frequently asked questions to FAQ

---

## 4. Anthropic Skills PR Update

### Status
- Repository: `anthropics/skills`
- PR: #822
- Status: Awaiting review (as of 2026-04-04)

### When Update is Needed
- When adding new parameters to MCP tools
- When adding new MCP tools
- When changing skill descriptions/instructions

### Procedure

```bash
# 1. Edit in awt-skill repository
cd ~/Documents/Projects/awt-skill  # or respective branch

# 2. Sync tool definitions in mcp/server.py
# Keep identical to AWT main's mcp/server.py

# 3. Commit & push
git add .
git commit -m "feat: sync with AWT v1.X.X — add responsive/console/open"
git push

# 4. Comment changes on PR #822
gh pr comment 822 --repo anthropics/skills --body "Updated to match AWT v1.X.X"
```

### ⚠️ Notes
- anthropics/skills PR not yet merged
- Can use locally before merge: `~/.claude/skills/awt/`
- Consider closing and opening new PR if PR is stale

---

## 5. MCP Servers PR Update

### Status
- Repository: `modelcontextprotocol/servers`
- PR: #3766
- Status: Awaiting review (as of 2026-04-04)

### Procedure

```bash
# 1. Edit in respective fork
# Sync tool definitions in mcp/server.py

# 2. Commit & push → auto-updates PR

# 3. Comment on PR
gh pr comment 3766 --repo modelcontextprotocol/servers \
  --body "Updated: added responsive/console/open parameters"
```

---

## Deployment Checklist (copy and use)

Follow this checklist when deploying new features:

```markdown
### Deployment Checklist — [Feature Name]

- [ ] Local tests pass (make lint && make typecheck && make test)
- [ ] git commit & push
- [ ] CI pass verified (gh run list --limit 1)
- [ ] CLAUDE.md WBS updated
- [ ] README.md updated (if applicable)
- [ ] README.ko.md synced (if applicable)
- [ ] lee-to-kim summary updated (when collaborating)
- [ ] PyPI version bump + tag (when deployment conditions met)
- [ ] Anthropic Skills PR synced (when MCP changes)
- [ ] MCP Servers PR synced (when MCP changes)
```

---

## Version History

| Version | Date | Major Changes |
|---|---|---|
| 1.6.1 | Current | visual regression, watch mode, responsive/console/open |
| (Previous) | — | Phase 1~6, Post-MVP features |

> Update this document when features are added or deployment procedures change.
