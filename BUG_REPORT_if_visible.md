# BUG REPORT: if_visible block detection works in reverse

## Reporter: Park (AutoPost)
## Date: 2026-03-24
## Severity: Critical

## Issue

The `if_visible` block's OCR text detection works in **exact opposite**.

| Popup | Actual State | if_visible Judgment | Result |
|------|-------------|---------------------|--------|
| "You have a draft" | **Exists** (visible on screen) | **Judged as absent** → then block skipped | Popup not closed |
| "Help" | **Absent** (not visible on screen) | **Judged as present** → then block executed | Wrong coordinates clicked |

## Reproduction Scenario

```yaml
# This block should execute but is skipped (popup is visible)
- step: 4
  action: if_visible
  target:
    text: "You have a draft"
  then:
    - action: click_at
      value: "567,436"
      description: "Click cancel button"
    - action: wait
      value: "2000"
  description: "Handle draft popup"

# This block should be skipped but executes (help panel not visible)
- step: 5
  action: if_visible
  target:
    text: "Help"
  then:
    - action: click_at
      value: "1221,40"
      description: "Click help X button"
    - action: wait
      value: "1000"
  description: "Close help panel"
```

## Screenshots

- `bug_if_visible_popup_exists.png` — "You have a draft" popup is **visible** but if_visible **cannot find it**
- `bug_if_visible_final.png` — Final state with popup not closed, title/content input failed

Path: `.aat/screenshots/`

## Additional Issue: Variable Substitution

`{{env.POST_TITLE}}` in `vars` is still not being substituted and shows as `{{title}}`.
Environment variable value is confirmed (Python launcher output):
```
Title: Academy director, manage academy and AI marketing for 30,000 won/month...
Content: 1055 chars
```

## Expected Behavior

1. `if_visible`: Execute then block if text **exists** on screen, **skip** if absent
2. `vars` + `{{env.X}}`: Substitute with environment variable value properly
