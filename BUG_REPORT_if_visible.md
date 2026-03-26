# BUG REPORT: if_visible 블록 감지가 반대로 동작

## 보고자: 박대리 (AutoPost)
## 날짜: 2026-03-24
## 심각도: Critical

## 현상

`if_visible` 블록의 OCR 텍스트 감지가 **정반대로 동작**합니다.

| 팝업 | 실제 상태 | if_visible 판단 | 결과 |
|------|---------|---------------|------|
| "작성 중인 글이 있습니다" | **있음** (화면에 보임) | **없다고 판단** → then 블록 스킵 | 팝업 안 닫힘 |
| "도움말" | **없음** (화면에 안 보임) | **있다고 판단** → then 블록 실행 | 엉뚱한 좌표 클릭 |

## 재현 시나리오

```yaml
# 이 블록이 실행되어야 하는데 스킵됨 (팝업이 떠 있는 상태)
- step: 4
  action: if_visible
  target:
    text: "작성 중인 글이 있습니다"
  then:
    - action: click_at
      value: "567,436"
      description: "취소 버튼 클릭"
    - action: wait
      value: "2000"
  description: "작성중 글 팝업 처리"

# 이 블록이 스킵되어야 하는데 실행됨 (도움말 패널 없는 상태)
- step: 5
  action: if_visible
  target:
    text: "도움말"
  then:
    - action: click_at
      value: "1221,40"
      description: "도움말 X 버튼 클릭"
    - action: wait
      value: "1000"
  description: "도움말 패널 닫기"
```

## 스크린샷

- `bug_if_visible_popup_exists.png` — "작성 중인 글이 있습니다" 팝업이 **보이는** 상태인데 if_visible이 **못 찾음**
- `bug_if_visible_final.png` — 결국 팝업이 안 닫혀서 제목/본문 입력 실패한 최종 상태

경로: `.aat/screenshots/`

## 추가 이슈: 변수 치환

`vars`에서 `{{env.POST_TITLE}}`가 여전히 치환되지 않고 `{{title}}`로 입력됨.
환경변수에 값이 있는 것은 확인됨 (Python launcher에서 출력):
```
Title: 학원 원장님, 월 3만원으로 학원 관리와 AI 마케팅...
Content: 1055 chars
```

## 기대 동작

1. `if_visible`: 화면에 텍스트가 **있으면** then 블록 실행, **없으면** 스킵
2. `vars` + `{{env.X}}`: 환경변수 값으로 정상 치환
