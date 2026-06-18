# AAT Demo Test Site

Demo Flask web application for AAT testing.

> **WARNING:** Demo only. Not for production use.
> Hardcoded secret key, in-memory storage, no input validation.

## Running

```bash
pip install flask
python test-site/app.py
# http://localhost:5001
```

## Page Structure

| Path | Function |
|------|----------|
| `/` | Main (login/register links) |
| `/register` | Registration |
| `/login` | Login |
| `/main` | Main after login |
| `/logout` | Logout |

## Scenario Directory Structure

This project has scenarios in 3 locations, each with different purposes:

| Path | Purpose | Features |
|------|---------|----------|
| `test-site/scenarios/` | For this demo app only | Concise 6 steps, direct `find_and_type` usage |
| `scenarios/` | For AAT execution (working directory) | Extended 9 steps, separated `find_and_click` + `find_and_type` |
| `scenarios/examples/` | AAT example templates | Advanced fields like `expected_result`, `screenshot_after` included |
