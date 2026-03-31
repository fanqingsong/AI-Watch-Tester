<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/logo-light.png">
    <img alt="AWT Logo" src="docs/assets/logo-light.png" width="300">
  </picture>
  <br/>
  <strong>AWT — AI Watch Tester</strong>
  <br/>
  <em>E2E 테스트 짜는 게 지겨워서, 직접 테스트를 만들고 고치는 도구를 만들었습니다.</em>
  <br/><br/>
  <a href="https://github.com/ksgisang/AI-Watch-Tester/actions"><img src="https://img.shields.io/github/actions/workflow/status/ksgisang/AI-Watch-Tester/ci.yml?label=CI&logo=github" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?logo=opensourceinitiative&logoColor=white" alt="MIT License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://ai-watch-tester.vercel.app"><img src="https://img.shields.io/badge/Cloud-바로_시작-00d4aa?logo=vercel&logoColor=white" alt="Cloud"></a>
  <a href="https://github.com/ksgisang/awt-skill"><img src="https://img.shields.io/badge/Agent_Skill-사용_가능-brightgreen?logo=npm&logoColor=white" alt="Agent Skill"></a>
  <a href="https://github.com/ksgisang/AI-Watch-Tester/stargazers"><img src="https://img.shields.io/github/stars/ksgisang/AI-Watch-Tester?style=flat&logo=github" alt="GitHub Stars"></a>
</p>

---

<p align="center">
  <a href="docs/assets/demo.mp4">
    <img src="docs/assets/demo.gif" alt="AWT 데모 — 설치, 실행, 자가 수복" width="860">
  </a>
  <br/>
  <sub><em>30초 데모: 설치 → 테스트 실행 → AI 자가 수복</em></sub>
</p>

---

## 왜 만들었나

Flutter 웹 앱을 개발하고 있었습니다. UI가 바뀔 때마다 Playwright 테스트가 깨졌습니다. 셀렉터 고치고, 플로우 다시 녹화하고, assert 업데이트하고 — 매주 몇 시간씩 날아갔습니다.

그래서 페이지를 보고 스스로 테스트를 만들고, 테스트가 깨지면 원인을 분석해서 혼자 고치는 도구를 만들기 시작했습니다.

그게 AWT입니다.

완벽하진 않습니다. OCR 기반 매칭은 특정 폰트에서 오작동하기도 합니다. 자가 수복 루프가 가끔 엉뚱한 곳을 건드리기도 합니다. 그래도 제 일상적인 QA 작업에서는 — 특히 Cypress도 못 건드리는 Canvas/Flutter Web 앱에서는 — 충분히 잘 동작해서, 테스트 코드를 직접 짜는 일을 완전히 그만뒀습니다.

**같은 고통을 겪고 있는 분이 있을 것 같아서 공유합니다. 셀렉터 고치는 데 오후를 통째로 날려본 적 있다면, 시간을 아낄 수 있을 겁니다.**

---

## 뭘 하는 도구인가

URL을 주면 AWT가 실제 Chrome 창을 열고, 페이지를 읽고, 테스트 스텝을 작성하고, 실행하고, 통과/실패 결과를 알려줍니다. 뭔가 깨지면 **DevQA Loop**가 작동합니다 — AI가 에러를 읽고, 테스트를 패치하고, 자동으로 재시도합니다 (최대 5회).

**테스트 코드를 직접 짤 필요 없습니다. 녹화 세션도 없습니다. UI가 바뀌어도 수동 업데이트가 없습니다.**

---

## 5분 안에 시작하기

### 방법 1 — Agent Skill (Claude Code, Cursor, Copilot 등과 함께)

```bash
# 한 줄 설치
npx skills add ksgisang/awt-skill --skill awt -g

# 그 다음 AI 도구에게:
"http://localhost:3000 로그인 플로우 테스트해줘"
"회원가입 폼 잘 작동하는지 확인해줘"
"마지막 커밋 이후 회귀 테스트 돌려줘"
# → AWT가 스캔, 스텝 생성, 실행, 리포트
```

### 방법 2 — MCP 서버 (Claude Desktop, Cursor, Windsurf)

```bash
# 설치
pip install aat-devqa

# Claude Code에 추가
claude mcp add awt -- python mcp/server.py

# 사용 가능한 도구: aat_devqa, aat_run, aat_doctor, aat_list_scenarios, aat_validate
```

> **클라우드 & 로컬 CLI** 버전은 현재 개발 중이며 별도로 공개 예정입니다.

---

## 동작 방식

```
URL을 입력하면
        │
        ▼
  🔍 SCAN — Chrome을 열고 버튼, 입력창, 링크를 모두 읽는다
        │
        ▼
  📝 GENERATE — AI가 단계별 테스트 플랜 작성 (검토 후 승인)
        │
        ▼
  ▶️  RUN — 실제 사용자처럼 클릭, 타이핑, 네비게이션
        │
        ├── ✅ 모두 통과 → 스크린샷 리포트 저장
        │
        └── ❌ 실패
                    │
                    ▼
            🔄 DEVQA LOOP — AI가 실패를 읽고,
               테스트(또는 소스 코드)를 수정하고,
               재시도 (최대 5회)
```

---

## DevQA Loop — 핵심 기능

대부분의 테스트 도구는 실패하면 멈추고 사람을 기다립니다. **AWT는 계속 진행합니다.**

스텝이 실패하면 AWT는:
1. 브라우저 화면 스크린샷 캡처
2. 에러 메시지와 화면에 보이는 콘텐츠 분석
3. 페이지 재스캔 — 요소가 이동하거나 변경됐는지 확인
4. 실패한 특정 스텝만 패치하고 재시도

실패 원인이 **셀렉터 문제가 아닌 소스 코드 버그**라면, AWT가 라우트 핸들러, 컴포넌트, API 엔드포인트까지 추적해서 수정안을 제안하거나 직접 적용할 수 있습니다.

```bash
# 루프 실행 실시간으로 보기
aat devqa "체크아웃 플로우 테스트" --url http://localhost:3000

# AI 코딩 도구와 함께 사용 (Claude Code, Cursor, Copilot...)
# "회원가입 페이지 테스트해줘" → AWT가 스캔, 생성, 실행, 수정
```

---

## 4가지 사용 방법

| | **클라우드** | **로컬 CLI** | **Agent Skill** | **MCP 서버** |
|---|-----------|---------------|-----------------|----------------|
| **시작 방법** | [ai-watch-tester.vercel.app](https://ai-watch-tester.vercel.app) 회원가입 | `pip install aat-devqa` | `npx skills add ksgisang/awt-skill` | `pip install aat-devqa mcp` |
| **브라우저** | 헤드리스 (서버) | 내 머신의 실제 Chrome | 내 머신의 실제 Chrome | 내 머신의 실제 Chrome |
| **AI 키 필요** | 불필요 (서버 제공 또는 BYOK) | 필요 (OpenAI / Anthropic / Ollama) | **불필요** — AI 도구가 두뇌 역할 | **불필요** |
| **적합한 용도** | 빠른 테스트, 기획자, PM | 개발자, CI/CD | AI 보조 개발 | Claude Desktop, Cursor, Windsurf |
| **가격** | 무료 (5회/월) · Pro $28.99 · Team $98.99 | 영구 무료 (MIT) | 영구 무료 | 영구 무료 |

### Agent Skill — AI 코딩 도구가 AWT를 직접 제어

```bash
# 한 줄 설치
npx skills add ksgisang/awt-skill --skill awt -g

# 그 다음 AI 도구에게:
"http://localhost:3000 로그인 플로우 테스트해줘"
"회원가입 폼 잘 작동하는지 확인해줘"
"마지막 커밋 이후 회귀 테스트 돌려줘"
# → AWT가 스캔, 테스트 스텝 생성, 실행, 리포트
```

### MCP 서버 — 프로토콜 네이티브

```bash
# Claude Code에 추가
claude mcp add awt -- python mcp/server.py

# 사용 가능한 도구: aat_run, aat_doctor, aat_list_scenarios, aat_validate, aat_cost
```

---

## AWT가 잘하는 것

| | 기능 | 설명 |
|---|---------|-------------|
| 🤖 | **제로 코드 테스트 생성** | URL만 입력하면 AI가 실제 셀렉터 포함 완전한 테스트 스텝 생성 |
| 🔄 | **자가 수복 DevQA Loop** | 테스트 실패? AI가 자동으로 수정하고 재시도 (최대 5회) |
| 👁️ | **시각적 검증** | 모든 액션 전후 스크린샷 — DOM 체크만이 아님 |
| 🌐 | **실제 브라우저** | 인간 같은 마우스 움직임과 타이핑 속도의 Chrome |
| 📱 | **Flutter 지원** | CanvasKit + Semantics 감지 — Flutter Web 앱도 테스트 가능 |
| 📄 | **문서 기반 생성** | PDF/DOCX 스펙을 주면 AI가 요구사항에서 테스트를 생성 |
| ⚡ | **속도 모드** | React/Next.js는 `fast` · Flutter/애니메이션은 `slow` |
| 📸 | **스마트 스크린샷** | `all` / `before-after` / `on-failure` — 필요에 맞게 선택 |
| 🔌 | **플러그인 아키텍처** | 엔진, 매처, AI 제공자를 레지스트리로 교체 가능 |

---

## 알려진 한계 (솔직하게)

저는 잘 쓰고 있지만, 아직 완전히 해결하지 못한 부분이 있습니다:

- **OCR 매칭**은 커스텀 폰트나 저대비 UI에서 오작동할 수 있습니다 — 이럴 때는 DOM 셀렉터로 대체하세요
- **자가 수복 루프**가 가끔 엉뚱한 요소에 집착하기도 합니다. `--max-attempts 3`으로 무한 루프를 방지하세요
- **애니메이션이 많은 SPA**는 `--verbosity=detailed`와 더 긴 대기 시간이 필요할 수 있습니다
- **첫 시나리오 생성** 품질은 페이지의 접근성 트리 품질에 달려 있습니다 — HTML 구조가 엉망이면 결과도 엉망입니다

뭔가 잘 안 되면 [이슈를 열어주세요](https://github.com/ksgisang/AI-Watch-Tester/issues). 빠르게 고칩니다.

---

## 다른 도구와 비교

### vs Playwright / Cypress

Playwright와 Cypress는 훌륭한 도구입니다 — AWT도 Playwright 위에 만들어졌습니다. 차이는 **누가 테스트를 작성하느냐**입니다:

| | **AWT** | **Playwright / Cypress** |
|---|---------|--------------------------|
| 테스트 작성자 | AI (URL에서 자동 생성) | 개발자 (코드 작성) |
| UI 변경 시 유지보수 | AI가 자동으로 수복 | 셀렉터를 수동으로 업데이트 |
| 러닝커브 | 없음 — URL만 붙여넣기 | 중간 (프레임워크 API + JS/TS) |
| 유연성 | 높음 (YAML 시나리오) | 최대 (완전한 코드 제어) |

**완전한 프로그래밍 제어**가 필요하면 Playwright/Cypress를 쓰세요. **테스트를 직접 짜고 싶지 않을 때** AWT를 쓰세요.

### vs testRigor

| | **AWT** | **testRigor** |
|---|---------|---------------|
| 테스트 작성 | AI가 URL에서 자동 생성 — 아무것도 안 써도 됨 | 평이한 영어로 명령 작성 |
| 자가 수복 | DevQA Loop (AI가 자동 재생성) | 내장 자동 유지보수 |
| 가격 | 무료 (MIT, 셀프 호스팅) | 엔터프라이즈 (~$800+/월) |
| 오픈소스 | ✅ MIT 라이선스 | ❌ |

---

## 속도 & 스크린샷 모드

꼼꼼함과 속도 사이의 균형을 조절하세요:

```bash
# CI/CD — 가장 빠름, 저장 최소화
aat run --verbosity=concise --screenshots=on-failure scenarios/

# 일반 QA — 균형 (권장)
aat run --verbosity=concise --screenshots=before-after scenarios/

# 전체 감사 — 모든 스텝 기록
aat run --verbosity=detailed --screenshots=all scenarios/
```

| 모드 | 스텝 수 | 스크린샷 수 | 소요 시간 | 용도 |
|------|-------|-------------|-------|---------|
| `concise` + `on-failure` | 12–15 | 0–1 | ~1분 | CI/CD 게이트 |
| `concise` + `before-after` | 12–15 | 24 | ~2분 | 일상 QA |
| `detailed` + `all` | 60–80 | 68 | ~5분 | 컴플라이언스 / 감사 |

---

## 지원하는 AI 제공자

| 제공자 | 모델 | 비용 | 설정 |
|----------|--------|------|-------|
| **OpenAI** | gpt-4o, gpt-4o-mini | 사용량 과금 | `export OPENAI_API_KEY=sk-...` |
| **Anthropic** | Claude Sonnet 4 | 사용량 과금 | `export ANTHROPIC_API_KEY=sk-ant-...` |
| **Ollama** | codellama, llama3, mistral | 무료 (로컬) | `ollama serve` |

```yaml
# aat.yaml
ai:
  provider: openai        # openai | anthropic | ollama
  model: gpt-4o
  api_key: ${OPENAI_API_KEY}
```

---

## 아키텍처

```
aat devqa / aat run / aat dashboard
              │
              ▼
    ┌─────────────────────────────────────┐
    │           CLI (Typer)               │
    ├─────────────────────────────────────┤
    │         Core Orchestrator           │
    │  Executor · Comparator · DevQALoop  │
    ├────────────┬──────────┬─────────────┤
    │   Engine   │ Matcher  │  AI Adapter │
    │ web/desktop│ocr/cv/ai │ openai/etc. │
    ├────────────┴──────────┴─────────────┤
    │  Pydantic v2 Models · SQLite Learn  │
    └─────────────────────────────────────┘
```

모든 모듈은 **플러그인 레지스트리** 패턴을 따릅니다 — 베이스 클래스 하나 구현하고 `__init__.py`에 등록하면 새 엔진, 매처, AI 제공자를 추가할 수 있습니다.

---

## 개발 환경

### 사전 요구사항

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract): `brew install tesseract` / `apt install tesseract-ocr`

### 명령어

| 명령어 | 설명 |
|---------|-------------|
| `make dev` | 전체 의존성 + Playwright + pre-commit 설치 |
| `make lint` | 코드 스타일 검사 (ruff) |
| `make format` | 자동 포매팅 |
| `make typecheck` | 엄격한 타입 검사 (mypy) |
| `make test` | 전체 테스트 실행 (pytest) |
| `make test-cov` | 테스트 + 커버리지 리포트 |

```bash
git clone https://github.com/ksgisang/AI-Watch-Tester.git
cd AI-Watch-Tester
python -m venv .venv && source .venv/bin/activate
make dev
make test        # 정상 동작 확인
aat dashboard    # http://localhost:9500 에서 실행
```

---

## 기여하기

기여, 버그 리포트, 새 플러그인 모두 환영합니다 — [CONTRIBUTING.md](CONTRIBUTING.md) 참고.

PR 전에 이슈를 먼저 열어주세요. 같이 방향을 잡는 게 더 빠릅니다.

```bash
git checkout -b feat/my-feature
make format && make lint && make typecheck && make test
git commit -m "feat(scope): description"
```

---

## FAQ

<details>
<summary><strong>코딩을 몰라도 쓸 수 있나요?</strong></summary>
<br/>

네. <a href="https://ai-watch-tester.vercel.app">ai-watch-tester.vercel.app</a> 클라우드 버전은 브라우저만 있으면 됩니다. 로컬 CLI는 터미널 명령어 한 줄로 설치할 수 있습니다.

AWT에게 필요한 건 URL과 (선택적으로) 무엇을 테스트할지 설명뿐입니다.
</details>

<details>
<summary><strong>"자가 수복"이 뭔가요?</strong></summary>
<br/>

웹 앱이 바뀌면 — 버튼 위치가 바뀌거나, 라벨이 달라지거나, 새 폼 필드가 생기거나 — 기존 테스트는 깨지고 누군가 수동으로 고치기 전까지 계속 깨진 상태입니다.

AWT의 DevQA Loop는 실패 후 페이지를 재스캔하고, 업데이트된 요소를 찾아서 테스트 스텝을 자동으로 패치합니다. 테스트 파일을 직접 건드릴 필요가 없습니다.
</details>

<details>
<summary><strong>aat devqa와 aat loop의 차이가 뭔가요?</strong></summary>
<br/>

| | `aat devqa` | `aat loop` |
|--|-------------|------------|
| 시작점 | 설명 + URL | 기존 시나리오 파일 |
| 테스트 생성 | 자동 (스캔 후 작성) | 파일 사용 |
| 실패 수정 | 테스트 YAML 패치 | **소스 코드** AI 패치 |
| 적합한 용도 | 첫 실행, 빠른 테스트 | 코드 수정 포함 반복 개발 |

처음 시작할 때는 `aat devqa`, 앱 코드도 함께 고치고 싶을 때는 `aat loop`.
</details>

<details>
<summary><strong>클라우드 버전 요금은?</strong></summary>
<br/>

| 플랜 | 가격 | 테스트/월 |
|------|-------|-------------|
| **Free** | $0 | 5회 |
| **Pro** | $28.99/월 | 100회 |
| **Team** | $98.99/월 | 500회 |

로컬 CLI는 제한 없이 영구 무료입니다.
</details>

<details>
<summary><strong>데이터는 안전한가요?</strong></summary>
<br/>

- 모든 트래픽 HTTPS/TLS 암호화
- BYOK API 키: Fernet 암호화 (AES-128-CBC + HMAC-SHA256) 저장
- 스크린샷: 7일 후 자동 삭제
- 로컬 모드: 아무것도 외부로 나가지 않음
</details>

---

## 라이선스

[MIT](LICENSE) — 개인 및 상업적 용도 모두 무료.

---

<p align="center">
  <sub>Playwright, OpenCV, 그리고 깨진 셀렉터에 대한 수많은 짜증으로 만들어졌습니다.<br/>만든 사람: <a href="https://github.com/ksgisang">@ksgisang</a> — 피드백과 이슈 언제든 환영합니다.</sub>
</p>
