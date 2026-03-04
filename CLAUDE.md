# AAT (AI Auto Tester) — Project Guide

## Overview

AI 기반 DevQA Loop 오케스트레이터. 이미지 매칭으로 UI 테스트를 자동화하고, 실패 시 AI가 코드를 수정하고 재테스트하는 루프를 반복한다.

## Key Documents

- `PM/기획서_v1.md` — 제품 기획서 (전체 비전)
- `PM/Develop_Plan_v0.2.md` — 기술 아키텍처
- `PM/설계서_v0.2.md` — **구현 상세 설계** (이 파일이 구현의 기준)
- `PM/비즈니스_플랜_v0.2.md` — 사업 전략

## Tech Stack

- Python 3.11+, Typer (CLI), Pydantic v2, pydantic-settings
- Playwright (WebEngine), PyAutoGUI (DesktopEngine), OpenCV (이미지 매칭), pytesseract (OCR)
- anthropic SDK (Claude API), openai SDK, httpx (Ollama), Jinja2 (리포트), SQLite (학습 DB)
- Dev: ruff, mypy, pytest, pytest-asyncio, pre-commit

## Architecture Rules

- async 기본 (Playwright async 네이티브)
- ABC + @abstractmethod (Protocol 대신)
- core/models.py는 leaf 모듈 (내부 import 없음)
- 순환 의존 금지: cli → core → engine/matchers/adapters/reporters → models
- 플러그인 레지스트리: 각 __init__.py의 딕셔너리 기반

## Commands

- `make dev` — 개발 환경 설치
- `make lint` — ruff check
- `make format` — ruff format + fix
- `make typecheck` — mypy strict
- `make test` — pytest
- `make test-cov` — pytest + coverage

---

## WBS Progress Tracker

> 각 태스크 완료 시 `[ ]` → `[x]`로 변경하고 완료일 기록

### Phase 1: Foundation (Week 1, ~17h)

- [x] **AAT-001** 프로젝트 스켈레톤 (2h) — 완료 2026-02-11
  - git init, pyproject.toml, 디렉토리 구조, Makefile, pre-commit
  - 완료 기준: `make lint && make typecheck && make test` 통과
- [x] **AAT-003** Enum 정의 (1h) — 완료 2026-02-11
  - ActionType, LabelPosition, AssertType, MatchMethod, Severity, StepStatus
- [x] **AAT-002** Pydantic 모델 전체 (4h) — 완료 2026-02-11
  - Config 모델, 시나리오 모델, 결과 모델, 학습 모델 + validator
  - 완료 기준: test_models.py 통과
- [x] **AAT-007** 예외 계층 (1h) — 완료 2026-02-11
  - AATError 기반 10개 커스텀 예외
- [x] **AAT-004** Config + pydantic-settings (3h) — 완료 2026-02-11
  - YAML + env var + CLI flag 3계층 머지
- [x] **AAT-005** 5개 ABC 인터페이스 (3h) — 완료 2026-02-11
  - BaseEngine, BaseMatcher, AIAdapter, BaseParser, BaseReporter
- [x] **AAT-006** Scenario YAML 로더 (3h) — 완료 2026-02-11
  - YAML → Scenario, 디렉토리 스캔, 변수 치환

### Phase 2: Engine + Matchers (Week 2~3, ~33h)

- [x] **AAT-010** WebEngine — Playwright (6h) — 완료 2026-02-11
- [x] **AAT-011** Humanizer — Bezier 마우스, 가변 타이핑 (4h) — 완료 2026-02-11
- [x] **AAT-012** Waiter — 폴링 + 해시 안정화 (4h) — 완료 2026-02-11
- [x] **AAT-013** TemplateMatcher — cv2.matchTemplate (5h) — 완료 2026-02-11
- [x] **AAT-014** OCRMatcher — pytesseract (6h) — 완료 2026-02-11
- [x] **AAT-015** FeatureMatcher — ORB/SIFT (4h) — 완료 2026-02-11
- [x] **AAT-016** HybridMatcher — 체인 오케스트레이터 (4h) — 완료 2026-02-11

### Phase 3: Executor + CLI (Week 3~4, ~26h)

- [x] **AAT-020** StepExecutor (6h) — 완료 2026-02-11
- [x] **AAT-021** Comparator (4h) — 완료 2026-02-11
- [x] **AAT-022** CLI — init, config (4h) — 완료 2026-02-11
- [x] **AAT-023** CLI — validate (3h) — 완료 2026-02-11
- [x] **AAT-024** CLI — run (5h) — 완료 2026-02-11
- [x] **AAT-025** CLI — report, learned (4h) — 완료 2026-02-11 (stub)

### Phase 4: AI + Loop (Week 5~6, ~16h)

- [x] **AAT-030** ClaudeAdapter (4h) — 완료 2026-02-11
- [x] **AAT-031** MarkdownReporter (3h) — 완료 2026-02-11
- [x] **AAT-032** DevQALoop (6h) — 완료 2026-02-11
- [x] **AAT-033** CLI — loop (3h) — 완료 2026-02-11

### Phase 5: Analysis + Generation (Week 6~7, ~16h)

- [x] **AAT-040** MarkdownParser (3h) — 완료 2026-02-11
- [x] **AAT-041** CLI — learn (4h) — 완료 2026-02-11
- [x] **AAT-042** CLI — analyze (5h) — 완료 2026-02-11
- [x] **AAT-043** CLI — generate (4h) — 완료 2026-02-11

### Phase 6: Learning + Polish (Week 7~8, ~22h)

- [x] **AAT-050** LearnedStore — SQLite (4h) — 완료 2026-02-11
- [x] **AAT-051** LearnedMatcher (3h) — 완료 2026-02-11
- [x] **AAT-052** VisionAIMatcher — stub (2h) — 완료 2026-02-11
- [x] **AAT-053** README + CONTRIBUTING (4h) — 완료 2026-02-11
- [x] **AAT-054** 통합 테스트 (6h) — 완료 2026-02-11
- [x] **AAT-055** CI/CD + 릴리스 준비 (3h) — 완료 2026-02-11

### Post-MVP: 품질 강화 + 확장

- [x] **AAT-060** GitHub 저장소 생성 + 초기 푸시 — 완료 2026-02-11
- [x] **AAT-061** CI/CD 파이프라인 수정 (tesseract, playwright, pandas, ANSI) — 완료 2026-02-11
- [x] **AAT-062** 영문화 — 에러 메시지, README, CONTRIBUTING 영어 전환 — 완료 2026-02-11
- [x] **AAT-063** TemplateMatcher 버그 수정 — 1.0x 스케일 누락 문제 — 완료 2026-02-11
- [x] **AAT-064** OllamaAdapter — 로컬 LLM 연동 (codellama:7b) — 완료 2026-02-12
- [x] **AAT-065** OpenAIAdapter — GPT-4o Vision 지원 — 완료 2026-02-12

### Post-MVP: 가이드 모드 + UX (AAT-070~076)

- [x] **AAT-070** 이벤트/알림 시스템 — 메신저 연동 대비 EventEmitter 패턴
  - CLIHandler (터미널 출력), MessageBuffer (메신저 배치 전송), 향후 TelegramHandler/DiscordHandler 확장
- [x] **AAT-071** AI Provider 연결 테스트 — API 키 입력 후 즉시 연결 확인
  - Claude: 간단한 API 호출, OpenAI: 모델 목록 조회, Ollama: /api/tags 확인
- [x] **AAT-072** 폴더 일괄 문서 분석 — 디렉토리 지정 시 전체 파일 스캔+분석
- [x] **AAT-073** URL 접속 확인 — 테스트 대상 URL 응답 체크
- [x] **AAT-074** 테스트 중 취소 기능 — Ctrl+C로 즉시 중단 + 부분 결과 저장
- [x] **AAT-075** `aat start` 가이드 모드 — 전체 흐름을 하나의 대화형 명령으로
  - 설정→문서분석→시나리오생성→테스트→루프→리포트 일괄 진행
- [x] **AAT-076** 가이드 모드 테스트 (events, connection, start_cmd)

### Post-MVP: 엔진 + 승인 모드 (AAT-080~081)

- [x] **AAT-080** 3-Tier Approval Mode — Git 브랜치 격리 기반 승인 모드 — 완료 2026-02-12
  - ApprovalMode enum (manual/branch/auto), GitOps async subprocess 래퍼
  - DevQALoop 모드별 핸들러 (`_handle_manual/branch/auto`), `_read_source_files`
  - `--approval-mode/-a` CLI 옵션, `skip_engine_lifecycle`, start_cmd 중복 제거
  - MarkdownReporter 브랜치/커밋 정보 렌더링
- [x] **AAT-081** DesktopEngine — PyAutoGUI + Playwright 하이브리드 — 완료 2026-02-12
  - PyAutoGUI (OS-level 마우스/키보드/스크린샷) + Playwright (브라우저 네비게이션)
  - ENGINE_REGISTRY 등록, CLI 동적 엔진 선택 (`config.engine.type: web | desktop`)

### Post-MVP: 웹 대시보드 (AAT-090~091)

- [x] **AAT-090** Web Dashboard (`aat dashboard`) — 완료 2026-02-12
  - FastAPI + WebSocket 기반 실시간 대시보드
  - 5영역 UI: Scenarios | Config | Execution | Live Screenshot | Event Log
  - SubprocessManager, WebSocketEventHandler, ConnectionManager
  - REST API: config CRUD, scenario list, run/loop/stop, status, logs, screenshots
  - 실시간 스크린샷 (960x540 JPEG 60% → base64 WS), 승인 모달, 프로그레스 바
  - pyproject.toml `[web]` optional dependency (fastapi, uvicorn, websockets)
  - 다크 테마 (#1a1a2e/#16213e/#e0e0e0, 틸 #00d4aa)
- [x] **AAT-091** Dashboard UI/UX 전면 개선 — 3-step Z-패턴 레이아웃 — 완료 2026-02-13
  - 5-panel grid → 3-step Z-패턴 (Setup → Prepare → Execute)
  - 서버 제어: SubprocessManager `start_raw(cmd, cwd)` + `on_line` 콜백 + 포트 자동 추출
  - 서버 엔드포인트 4개 (start/stop/status/logs), 문서 업로드 2개 (upload/list)
  - 드래그&드롭 문서 업로드, 미니 로그 + Event Log 이중 표시
  - python-multipart 의존성 추가, 반응형 (1100px 이하 1열 스택)
- [x] **AAT-092** 시나리오 관리 기능 개선 — 완료 2026-02-13
  - 커스텀 경로 지원: `GET /api/scenarios?path=` 쿼리 파라미터
  - 시나리오 YAML 업로드: `POST /api/scenarios/upload` (.yaml/.yml 전용)
  - 선택적 실행: `scenario_ids` 파라미터로 선택된 시나리오만 run/loop
  - UI: 경로 입력+Load, Select All/Clear, 선택 카운트, 동적 버튼 라벨

---

## Branch Strategy

- **main**: 실서비스 브랜치. 직접 개발 금지. merge 또는 hotfix만.
- **dev**: 개발 브랜치. 모든 새 기능/수정은 여기서 진행.
- 작업 시작 전 반드시 `git checkout dev` 확인.
- dev에서 테스트 완료 후 main에 merge하여 배포.
- 긴급 수정 시에만 main에서 직접 hotfix 후 dev에 sync.
- Vercel: main = Production, dev = Preview (미리보기 URL 자동 생성)
- Render: main만 auto-deploy (dev push로는 배포 안 됨)

---

## Current Status

- **현재 단계**: Post-MVP 시나리오 관리 기능 개선 완료
- **완료**: Phase 1~6 (Ultra-MVP) + AAT-060~065 + AAT-070~076 + AAT-080~081 + AAT-090~092 (Post-MVP)
- **블로커**: 없음
- **Python**: 3.12.12 (.venv), `source .venv/bin/activate`
- **GitHub**: https://github.com/ksgisang/AI-Watch-Tester (private)
