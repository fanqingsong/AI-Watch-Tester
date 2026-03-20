# AWT MCP Server

AWT를 [Model Context Protocol (MCP)](https://modelcontextprotocol.io) 서버로 사용하면,
Claude Code, Claude Desktop, Cursor, Windsurf 등 MCP 지원 도구에서 AWT를 직접 호출할 수 있습니다.

## 사전 요구사항

```bash
# AWT 설치 (아직 안 했다면)
pip install aat-devqa
playwright install chromium

# MCP SDK 설치
pip install mcp[cli]
```

## 제공 도구 (Tools)

| Tool | 설명 |
|------|------|
| `aat_run` | 시나리오 파일 실행 (결과 반환) |
| `aat_run_skill_mode` | 스킬 모드 실행 (구조화된 실패 진단 포함, AI 자동 루프용) |
| `aat_doctor` | 환경 진단 (Python, Playwright, Tesseract, AI 연결) |
| `aat_list_scenarios` | 현재 디렉토리의 시나리오 파일 목록 |
| `aat_validate` | YAML 시나리오 스키마 검증 |
| `aat_cost` | AI API 비용 조회 |

## 설치 방법

### Claude Code

```bash
claude mcp add awt -- python /path/to/AI-Watch-Tester/mcp/server.py
```

확인:
```bash
claude mcp list
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) 또는
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

프로젝트 루트에 `.cursor/mcp.json` 생성:

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

> `/path/to/AI-Watch-Tester`를 실제 경로로 변경하세요.

## 사용 예시

MCP 등록 후 AI 도구에서:

```
"시나리오 목록 보여줘"           → aat_list_scenarios 호출
"login 시나리오 실행해줘"        → aat_run("scenarios/login.yaml")
"환경 진단해줘"                 → aat_doctor 호출
"비용 얼마 썼어?"               → aat_cost 호출
"스킬 모드로 테스트 돌려줘"      → aat_run_skill_mode("scenarios/login.yaml")
```

### DevQA Loop (스킬 모드)

`aat_run_skill_mode`는 실패 시 구조화된 블록을 반환합니다:

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

AI 도구가 이 블록을 파싱해서 시나리오를 수정하고 재실행하는 자동 루프를 수행합니다.

## 직접 테스트

```bash
# MCP Inspector로 서버 테스트
mcp dev mcp/server.py

# 또는 직접 실행 (stdio 모드)
python mcp/server.py
```
