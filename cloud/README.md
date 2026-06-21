# AWT Cloud Backend

Fully local cloud backend — FastAPI + SQLite. **No external auth or database service is required.** Everything runs from local files and a single process.

## Quick Start (Local Development)

```bash
cd cloud
pip install -r requirements.txt

uvicorn app.main:app --reload
# http://127.0.0.1:8000/docs ← Swagger UI
```

That's it. The backend uses a local SQLite database (`awt_cloud.db`) and a single built-in local user — no signup, no login, no third-party services.

---

## How authentication works (local mode)

There is no user-facing authentication. Every request is treated as coming from the built-in **local user** (`local-user` / `local@awt.dev`), which is created automatically on first use.

- `app/auth.py` → `get_current_user()` returns the local user for all requests.
- For CI/CD or scripting, you may still pass an `X-API-Key` header (API keys are managed via the `/api/keys` endpoints). If the header is absent, the local user is used.

### API Call

```bash
# Create test (no auth header needed in local mode)
curl -X POST "http://localhost:8000/api/tests" \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com"}'

# List tests
curl "http://localhost:8000/api/tests"
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | - | Health check |
| POST | `/api/tests` | local / API key | Create test (rate limited) |
| GET | `/api/tests` | local / API key | List my tests (paginated) |
| GET | `/api/tests/{id}` | local / API key | Get test details |

### Rate Limiting

| Tier | Monthly POST Limit |
|------|-------------------|
| Free | 5 |
| Pro | Unlimited |

On exceed: `429 Too Many Requests` + headers:
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 2026-03-01T00:00:00+00:00
```

---

## Running Tests

```bash
cd cloud
pip install -r requirements.txt
pytest tests/ -v
```

Tests use an in-memory SQLite database and the local user — no external services required.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWT_DATABASE_URL` | no | `sqlite+aiosqlite:///./awt_cloud.db` | DB connection string (SQLite by default; any SQLAlchemy async URL works) |
| `AWT_RATE_LIMIT_FREE` | no | `5` | Free monthly limit |
| `AWT_RATE_LIMIT_PRO` | no | `-1` | Pro monthly limit (-1 = unlimited) |
| `AWT_DEBUG` | no | `false` | SQLAlchemy echo etc |
| `AWT_AI_PROVIDER` | no | `ollama` | AI provider for scenario generation (`ollama`/`openai`/`claude`/`zhipuai`) |
| `AWT_AI_API_KEY` | no | - | AI provider API key |
| `AWT_AI_MODEL` | no | - | AI model name |

> Optional: create a `cloud/.env` file for these. `.env` is git-ignored.

### Using PostgreSQL instead of SQLite (optional)

SQLite is the default and recommended for local/single-host use. If you prefer PostgreSQL, point `AWT_DATABASE_URL` at your own instance — any standard Postgres works, no specific vendor required:

```
AWT_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

---

## Directory Structure

```
cloud/
├── app/
│   ├── main.py          # FastAPI app entry point
│   ├── config.py         # pydantic-settings environment variables
│   ├── database.py       # SQLAlchemy async engine
│   ├── models.py         # ORM models (Test, User, ApiKey, ...)
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── auth.py           # Local user + API-key authentication
│   ├── middleware.py      # Rate limiting
│   └── routers/          # /api/* route handlers
├── tests/
│   ├── conftest.py       # Fixtures (in-memory DB, local user)
│   └── ...
├── requirements.txt
└── README.md
```
