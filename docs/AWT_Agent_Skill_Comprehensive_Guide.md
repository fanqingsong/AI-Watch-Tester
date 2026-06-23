# Publishing AWT as an Agent Skill — Comprehensive Guide

> Date: 2026-03-15 | AILoopLab

---

## 1. What is an Agent Skill?

### 1-1. One-line Definition

Agent Skill is a **markdown file (SKILL.md) that teaches AI coding tools specialized knowledge**.

When a developer says "test this site", AI automatically loads the AWT skill and performs testing in AWT's way. It's not installing code, it's **changing AI's behavior**.

### 1-2. Understanding through Analogy

| Analogy | Description |
|---------|-------------|
| Onboarding document for new developer | Manual telling AI "this is how our team works" |
| Cooking recipe | Step-by-step procedure AI can follow |
| USB driver | Plugging new capability into AI computer |

### 1-3. Key Features

- **Markdown-only creation** — Can be made without code, can include scripts
- **Progressive Disclosure** — Load metadata first (~100 tokens), load full content only when needed (<5K tokens)
- **Compatibility** — Following Agent Skills open standard (agentskills.io), one SKILL.md works on 11 tools

### 1-4. Compatible AI Coding Tools (as of March 2026)

| Tool | Developer | Skill Path | Execution Method |
|------|-----------|------------|------------------|
| **Claude Code** | Anthropic | `.claude/skills/` | `/skill-name` |
| **Codex CLI** | OpenAI | `.codex/skills/` | Call from prompt |
| **Gemini CLI** | Google | `.gemini/skills/` | Call from prompt |
| **Cursor** | Cursor | `.cursor/skills/` | `@skill-name` |
| **GitHub Copilot** | Microsoft | `.github/skills/` | Auto in VS Code |
| **Antigravity IDE** | Google | `.gemini/antigravity/skills/` | Agent Mode |
| **Kiro CLI/IDE** | AWS | `.kiro/skills/` | Auto load |
| **OpenCode** | Open Source | `.agents/skills/` | `opencode run @skill` |
| **Windsurf** | Codeium | `.windsurf/skills/` | Auto load |
| **Aider** | Open Source | Config path | Prompt |
| **Augment** | Augment | Config path | Auto load |

**Key: Once you create AWT skill, users of all 11 tools become potential customers.**

---

## 2. How to Create AWT Skill

### 2-1. Directory Structure

```
awt-skill/
├── SKILL.md              # Core file (required)
├── scripts/              # Executable scripts (optional)
│   ├── scan.sh           # Site scan script
│   ├── run-test.sh       # Test execution script
│   └── setup.sh          # AWT install/setup script
├── references/           # Reference docs (optional, loaded only when needed)
│   ├── YAML_SCHEMA.md    # YAML scenario format guide
│   ├── TROUBLESHOOT.md   # Common errors and solutions
│   └── EXAMPLES.md       # Scenario example collection
├── templates/            # Template files (optional)
│   └── scenario.yaml     # Default scenario template
└── LICENSE               # AGPL-3.0
```

### 2-2. SKILL.md Structure Detail

SKILL.md consists of **two parts**:

```
┌─────────────────────────────────────┐
│ 1. YAML Frontmatter (metadata)       │ ← AI judges "when to use this skill"
│    name, description etc.           │
├─────────────────────────────────────┤
│ 2. Markdown Content (instructions)   │ ← AI follows "how to do it"
│    usage, workflow, examples etc.    │
└─────────────────────────────────────┘
```

### 2-3. SKILL.md Actual Writing Example (for AWT)

```markdown
---
name: awt
description: >
  AI-powered web application testing tool. Use when asked to test a website,
  run E2E tests, generate test scenarios, or validate web app quality.
  Supports URL-based scanning, YAML scenario generation, Playwright execution,
  self-healing tests, and AI-driven fix suggestions. Use when user says
  "test this site", "run E2E tests", "check if my app works",
  "generate test scenarios", or "find bugs in my web app".
version: 1.0.0
---

# AI Watch Tester (AWT) — AI-Powered Web Testing Skill

## Overview

AWT is a tool that automatically tests web apps with just a URL.
AI automatically handles the entire QA loop:
Scan → Scenario generation → Test execution → Result analysis → Code fix suggestion

## Prerequisites

AWT CLI must be installed:
\`\`\`bash
# Check AWT installation
npx awt --version

# If not installed
npm install -g ai-watch-tester
\`\`\`

## Quick Start

\`\`\`bash
# Basic usage: Just enter URL, entire test runs automatically
npx awt test https://example.com

# Run scan only (site analysis before scenario generation)
npx awt scan https://example.com

# Run test with existing YAML scenario
npx awt run ./scenarios/login-flow.yaml
\`\`\`

## 5-Step Workflow

Execute the following steps in order according to user request:

### Step 1: Scan
Analyze DOM of target URL and understand page structure.
\`\`\`bash
npx awt scan $URL --output ./awt-scan-result.json
\`\`\`

### Step 2: Plan
Automatically generate YAML test scenario based on scan results.
\`\`\`bash
npx awt plan ./awt-scan-result.json --output ./scenarios/
\`\`\`

### Step 3: Review
Show generated scenario to user and request modification.
**Always confirm scenario with user before executing.**

### Step 4: Execute
Run test in real browser based on Playwright.
\`\`\`bash
npx awt run ./scenarios/ --headed
\`\`\`

### Step 5: Results
Analyze results and suggest fixes for failed tests.

## YAML Scenario Format

AWT defines tests declaratively in YAML. No code writing needed:

\`\`\`yaml
name: Login flow test
url: https://example.com/login
steps:
  - action: fill
    selector: "#email"
    value: "test@example.com"
  - action: fill
    selector: "#password"
    value: "password123"
  - action: click
    selector: "button[type='submit']"
  - action: assert
    selector: ".dashboard"
    condition: visible
\`\`\`

## Key Features

- **Self-Healing**: Auto recovery even if selector changes
- **Vision AI Matching**: OpenCV visual UI verification (selector-independent)
- **Pattern Learning**: Gets more accurate by remembering past failures
- **DevQA Loop**: Failure → AI analysis → PR creation → retest automation

## When NOT to use this skill

- Simple unit tests → Use Jest/Vitest
- API tests only → Use Postman/Insomnia
- Static analysis only → Use ESLint/SonarQube

## Troubleshooting

Refer to references/TROUBLESHOOT.md if problems occur.

## More Info

- GitHub: https://github.com/[your-org]/ai-watch-tester
- Docs: https://ai-watch-tester.onrender.com/docs
```

### 2-4. Core Writing Principles

| Principle | Description | AWT Application |
|-----------|-------------|-----------------|
| **description is most important** | Only criterion for AI to judge "when to use this skill" | Include trigger words like "test", "E2E", "QA", "bug" |
| **Progressive Disclosure** | Don't put everything in SKILL.md, only core content, rest in references/ | YAML schema, troubleshooting in separate files |
| **Must include examples** | AI needs examples to follow accurately | YAML scenario examples, CLI command examples |
| **Clarify boundaries** | Should write what this skill "doesn't do" | "Use Jest for unit tests" |
| **Within 5K tokens** | SKILL.md body too long wastes context | Only core workflow, detailed docs in references/ |

---

## 3. AWT Skill Distribution Strategy

### 3-1. Distribution Channel Full Map

```
                     AWT Skill Distribution Channels
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ① GitHub Direct    ② Marketplace     ③ Awesome Lists
    (self repo)        Registration       PR Submit
         │                │                │
    Create independent   SkillsMP.com      awesome-claude-skills
    repo creation        Claude plugin      awesome-agent-skills
    README cleanup       LobeHub           antigravity-awesome-skills
    npx install support  claudeskills.info
```

### 3-2. Detailed Execution by Channel

#### ① GitHub Self Repository (First thing to do)

Create AWT skill as independent GitHub repository:

```
ai-watch-tester-skill/        ← New repo name
├── .claude-plugin/
│   └── marketplace.json       ← For Claude Code plugin marketplace
├── skills/
│   └── awt/
│       ├── SKILL.md
│       ├── scripts/
│       ├── references/
│       └── templates/
├── README.md                  ← Install method, demo GIF, comparison table
├── CONTRIBUTING.md
├── LICENSE                    ← AGPL-3.0
└── package.json               ← For npx install support
```

**marketplace.json** (for Claude Code plugin registration):
```json
{
  "name": "awt-skill",
  "displayName": "AI Watch Tester",
  "description": "AI-powered web application testing with auto-healing and DevQA Loop",
  "version": "1.0.0",
  "skills": ["skills/awt"]
}
```

**Install command**:
```bash
# Install as Claude Code plugin
/plugin marketplace add [your-org]/ai-watch-tester-skill
/plugin install awt@awt-skill

# Or install directly with npx
npx skills add [your-org]/ai-watch-tester-skill --skill awt

# Or manual install
git clone https://github.com/[your-org]/ai-watch-tester-skill.git
cp -r ai-watch-tester-skill/skills/awt ~/.claude/skills/
```

#### ② Submit PR to Awesome Lists (Most effective free promotion)

Submit **Pull Request** to register AWT skill to these 3 repositories:

| Repository | GitHub Stars | Description |
|-------------|--------------|-------------|
| **sickn33/antigravity-awesome-skills** | ⭐ 22,000+ | 1,259+ skills, largest collection |
| **travisvn/awesome-claude-skills** | ⭐ 41,000+ | Claude specialized, most famous list |
| **VoltAgent/awesome-agent-skills** | Active community | High curation quality |

**PR Writing Example** (submit to awesome-claude-skills):
```markdown
## Testing & QA

- [AI Watch Tester](https://github.com/[your-org]/ai-watch-tester-skill) -
  AI-powered E2E testing with declarative YAML scenarios, self-healing tests,
  vision AI matching (OpenCV), and DevQA Loop (test failure → AI fix → auto PR → retest).
  Supports OpenAI, Claude, DeepSeek, Ollama.
```

#### ③ Skill Search Platform Registration

| Platform | URL | Features |
|----------|-----|----------|
| **SkillsMP** | skillsmp.com | 400,000+ skill search engine, category filter |
| **LobeHub** | lobehub.com/skills | Skill marketplace, includes install guide |
| **claudeskills.info** | claudeskills.info | Claude-only skill hub |

---

## 4. Promotion Strategy

### 4-1. Promotion Channel Priority

```
[High Effect / $0 Cost]
├── ① GitHub Awesome Lists PR → Auto expose to tens of thousands of developers
├── ② GeekNews post → Korean developer community core
├── ③ DEV.to / Hashnode blog → English developer community
├── ④ Reddit (r/ClaudeAI, r/coding) → Viral potential
│
[High Effect / Some Effort]
├── ⑤ Hacker News "Show HN" → Global developer maximum channel
├── ⑥ YouTube demo video → Visual persuasion
├── ⑦ Discowas → Korean startup community
│
[Long-term Effect]
├── ⑧ npm package registration (npx awt-skill) → Install convenience
└── ⑨ Product Hunt launch → Global exposure
```

### 4-2. Core Message (Use consistently across all promotion)

**One-line pitch:**
> "Skill that tests web apps with one URL and AI even fixes code when it fails"

**3-line description:**
> Existing webapp-testing skill is Playwright helper level.
> AWT skill provides declarative YAML scenarios + auto healing + vision AI + pattern learning.
> Install once, works on 11 tools including Claude Code, Cursor, Codex.

**Differentiation Comparison Table** (include in README and blog):

| Feature | webapp-testing | playwright-skill | **AWT** |
|---------|:---:|:---:|:---:|
| Playwright execution | ✅ | ✅ | ✅ |
| Code-less testing (YAML) | ❌ | ❌ | ✅ |
| Auto healing (Self-Healing) | ❌ | ❌ | ✅ |
| Vision AI matching (OpenCV) | ❌ | ❌ | ✅ |
| Pattern learning (SQLite) | ❌ | ❌ | ✅ |
| Failure → AI fix → PR | ❌ | ❌ | ✅ |
| Multi AI (OpenAI/Claude/DeepSeek) | ❌ | ❌ | ✅ |
| Bot detection bypass (Humanizer) | ❌ | ❌ | ✅ |

### 4-3. Content Strategy by Channel

#### GeekNews

**Title:** `Show GN: AWT – Open source skill that AI tests web apps and even fixes code`

**Content structure:**
1. Problem definition (Code made by AI, who verifies?)
2. How AWT solves it (5-Step workflow)
3. Differences from webapp-testing (comparison table)
4. One-line install (`npx skills add ...`)
5. GitHub link

#### DEV.to / Hashnode

**Title:** `I built an Agent Skill that tests your web app and fixes bugs automatically`

**Content:**
- Limitations of existing tools (Playwright = code writing required)
- AWT approach (YAML declarative + AI automation)
- Actual demo GIF or screenshots
- Performance metrics ($0.02~$0.05 per test)
- Installation method
- Roadmap (DevQA Loop, Cloud SaaS)

#### Reddit

**Subreddit:** r/ClaudeAI, r/ChatGPTCoding, r/webdev, r/SideProject

**Format:** "I made X" style short impactful post + technical details in comments

---

## 5. Free Skill → Paid SaaS Conversion Strategy

### 5-1. Funnel Design

```
Free skill installation (11 tools)
    │
    ├── Use basic features (local execution, YAML generation, testing)
    │       │
    │       ▼
    ├── Feel limitations (no cloud execution, no PR automation, no team sharing)
    │       │
    │       ▼
    └── Guide to AWT Cloud SaaS signup
            │
            ├── Free: $0 (5 times/month, same as skill)
            ├── Pro: $28.99/month (100 times/month, CI/CD, auto PR)
            └── Team: $98.99/month (500 times/month, team dashboard)
```

### 5-2. Free vs Paid Feature Separation

| Feature | Skill (Free) | Cloud Free | Cloud Pro | Cloud Team |
|---------|:---:|:---:|:---:|:---:|
| Site scan | ✅ | ✅ | ✅ | ✅ |
| YAML scenario generation | ✅ | ✅ | ✅ | ✅ |
| Local test execution | ✅ | ✅ | ✅ | ✅ |
| Self-Healing | ✅ | ✅ | ✅ | ✅ |
| Vision AI matching | ✅ | ✅ | ✅ | ✅ |
| Monthly test count | Unlimited(local) | 5 times | 100 times | 500 times |
| **Cloud execution** | ❌ | ❌ | ✅ | ✅ |
| **CI/CD API key** | ❌ | ❌ | ✅ | ✅ |
| **Source code analysis** | ❌ | ❌ | ✅ | ✅ |
| **AI auto fix PR** | ❌ | ❌ | ✅ | ✅ |
| **Team dashboard** | ❌ | ❌ | ❌ | ✅ |
| **Priority support** | ❌ | ❌ | ❌ | ✅ |

**Core principle:** Using locally alone is completely free, cloud/team/automation is paid.

### 5-3. Conversion Inducement Method

Naturally expose at the end of skill execution result:

```
✅ Test Results: 12 passed, 3 failed

💡 Want auto-fix PRs for failed tests?
   Try AWT Cloud Pro → https://ai-watch-tester.onrender.com/pricing
```

---

## 6. Execution Roadmap

### Phase 1: Skill Production (1-2 days)

- [ ] Write SKILL.md (based on above example)
- [ ] Organize scripts/ directory (scan.sh, run-test.sh, setup.sh)
- [ ] Organize references/ directory (YAML schema, troubleshooting, examples)
- [ ] Test locally with Claude Code
- [ ] Create GitHub repo (ai-watch-tester-skill)
- [ ] Add marketplace.json (for Claude Code plugin)
- [ ] Write README.md (demo GIF, comparison table, installation method)

### Phase 2: Distribution (1 day)

- [ ] Publish GitHub repo
- [ ] Submit PR to awesome-claude-skills
- [ ] Submit PR to awesome-agent-skills
- [ ] Submit PR to antigravity-awesome-skills
- [ ] Register on SkillsMP, LobeHub, claudeskills.info

### Phase 3: Promotion (1 week)

- [ ] Post on GeekNews
- [ ] Post on DEV.to English blog
- [ ] Post on Hashnode English blog
- [ ] Post on Reddit (r/ClaudeAI, r/webdev)
- [ ] Update on Discowas
- [ ] Monitor reaction with GitHub Actions launch monitor

### Phase 4: Feedback & Improvement (ongoing)

- [ ] Collect feedback via GitHub Issues
- [ ] Implement DevQA Loop feature (key differentiator)
- [ ] Create demo video (YouTube)
- [ ] Post on Hacker News "Show HN"
- [ ] Prepare Product Hunt launch

---

## 7. Competitive Skill Analysis

As of March 2026, web testing related skill ecosystem:

### Existing Competitive Skills

| Skill Name | Features | Weakness vs AWT |
|------------|----------|-----------------|
| **webapp-testing** (Anthropic bundle) | Playwright Python helper, blackbox script | No scenario format, no failure handling, no learning |
| **playwright-skill** (lackeyjb) | Playwright JS automation, real-time browser | No predefined scenario, no fix suggestion |
| **Playwright Skill** (testdino-hq) | 70+ guides, pattern education | Education material focus, not automation engine |
| **playwright-cli Skill** | CLI-based, token efficient | Conversational step execution, not full automation |
| **e2e-testing** (community) | Playwright E2E runner | No AWT's YAML/vision AI/learning |
| **browser-compatibility-tester** | Cross browser | BrowserStack dependent, not general testing |

### AWT Positioning

```
                    Automation Level
                      High
                       │
                   ◆ AWT
                       │    (YAML + Auto healing + Vision AI + Learning + PR)
                       │
          ─────────────┼─────────────
          Manual        │          Auto
          (code write)  │          (code unnecessary)
                       │
             ◆ playwright-skill
             ◆ webapp-testing
                       │
                      Low
```

**Conclusion: "Code-less testing + AI fixes" position is occupied only by AWT.**

---

## 8. Cautions & Tips

### Security

- Never include API keys, passwords in SKILL.md
- If scripts call external APIs, specify in README
- Clearly mark AGPL-3.0 license

### Description Writing Tips

Description within 200 characters, include as many keywords as AI searches:

```yaml
# Bad example (too vague)
description: A testing tool for web apps

# Good example (includes trigger keywords)
description: >
  AI-powered web application testing with YAML scenarios,
  self-healing, and auto-fix PRs. Use when asked to test a website,
  run E2E tests, generate test scenarios, find bugs, or validate
  web app quality.
```

### Token Efficiency

- SKILL.md body: Within 5K tokens (only core content)
- Detailed docs: Separate to references/ directory
- AI loads references/ only when needed, no context waste

### Testing Method

```bash
# Test skill in Claude Code
cd my-project
mkdir -p .claude/skills/
cp -r path/to/awt-skill .claude/skills/awt

# After running Claude Code
/awt https://my-test-site.com
```

---

## Appendix: Reference Materials

| Material | URL |
|----------|-----|
| Agent Skills official spec | agentskills.io/specification |
| Anthropic skill creation guide | support.claude.com/en/articles/12512198 |
| Claude Code skill docs | code.claude.com/docs/en/skills |
| Anthropic official skill repo | github.com/anthropics/skills |
| Awesome Claude Skills | github.com/travisvn/awesome-claude-skills |
| Awesome Agent Skills | github.com/VoltAgent/awesome-agent-skills |
| Antigravity Awesome Skills | github.com/sickn33/antigravity-awesome-skills |
| SkillsMP marketplace | skillsmp.com |
| Skill creation deep guide (PDF) | resources.anthropic.com (The Complete Guide) |
