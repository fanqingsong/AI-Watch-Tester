# AWT Cloud Backend

Cloud backend based on Supabase Auth + PostgreSQL.

## Quick Start (Local Development)

```bash
cd cloud
pip install -r requirements.txt

# Local development works with SQLite + JWT secret only
export AWT_SUPABASE_JWT_SECRET="your-dev-secret"

uvicorn app.main:app --reload
# http://127.0.0.1:8000/docs ← Swagger UI
```

---

## Supabase Project Setup Guide

### Step 1: Sign up for Supabase

1. Visit https://supabase.com
2. Click **Start your project**
3. Log in with GitHub account (or email signup)

### Step 2: Create New Project

1. Click **New Project** in dashboard
2. Enter settings:
   - **Organization**: Select default org (or create new)
   - **Project name**: `awt-cloud` (free to choose)
   - **Database Password**: Enter strong password → **Save separately**
   - **Region**: Select `Northeast Asia (Seoul)` — `ap-northeast-2`
   - **Plan**: Free (free for up to 2 projects)
3. Click **Create new project** → Wait 1-2 minutes

### Step 3: Check API Keys

After project creation:

1. Left menu **Project Settings** (gear icon) → **API**
2. Copy these 3 values:

| Item | Location | Environment Variable |
|------|----------|---------------------|
| **Project URL** | `https://xxxx.supabase.co` | `AWT_SUPABASE_URL` |
| **anon public** | `Project API keys` section | `AWT_SUPABASE_ANON_KEY` |
| **JWT Secret** | Bottom `JWT Settings` section | `AWT_SUPABASE_JWT_SECRET` |

> **Note**: `service_role` key is not used even in backend. Never expose to frontend.

### Step 4: Authentication Setup

1. Left menu **Authentication** → **Providers**
2. Verify **Email** is enabled by default
3. (Optional) **Confirm email** toggle:
   - During development: **OFF** → Sign up without email verification
   - For production: **ON** → Email verification required

### Step 5: Database Connection Info (Production Only)

1. **Project Settings** → **Database**
2. In **Connection string** section, select **URI** tab
3. Format: `postgresql://postgres.[ref]:[password]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres`
4. Set this value to `AWT_DATABASE_URL` (change to `postgresql+asyncpg://...` for asyncpg)

> **Skip this step for local development.** Default SQLite will be used.

### Step 6: Environment Variables Setup

Create `cloud/.env` file:

```env
# Supabase
AWT_SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
AWT_SUPABASE_ANON_KEY=eyJhbGciOiJI...
AWT_SUPABASE_JWT_SECRET=your-jwt-secret-from-step-3

# Database (production only — local uses default SQLite)
# AWT_DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
```

> `.env` file is included in `.gitignore` so it won't be committed.

---

## Authentication Flow

### Sign Up

```bash
curl -X POST "https://YOUR_PROJECT.supabase.co/auth/v1/signup" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "xxxxx",
  "user": {
    "id": "uuid-here",
    "email": "user@example.com"
  }
}
```

### Sign In

```bash
curl -X POST "https://YOUR_PROJECT.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'
```

Copy `access_token` from response.

### API Call

```bash
# Create test
curl -X POST "http://localhost:8000/api/tests" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com"}'

# List tests
curl "http://localhost:8000/api/tests" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## JWT Verification Method

Supabase Auth issues standard JWTs signed with the project's **JWT Secret** (HS256).

```
Header:  {"alg": "HS256", "typ": "JWT"}
Payload: {"sub": "user-uuid", "email": "...", "role": "authenticated", "aud": "authenticated", ...}
```

Backend verifies directly with `PyJWT` library:

```python
import jwt
payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience="authenticated")
user_id = payload["sub"]
```

Performs pure JWT verification without heavy SDKs like `firebase-admin`.

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | - | Health check |
| POST | `/api/tests` | Bearer | Create test (rate limited) |
| GET | `/api/tests` | Bearer | List my tests (paginated) |
| GET | `/api/tests/{id}` | Bearer | Get test details |

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

Works without Firebase dependency, only PyJWT. Tests use SQLite in-memory + JWT mock.

---

## Environment Variables List

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWT_SUPABASE_URL` | prod | - | Supabase project URL |
| `AWT_SUPABASE_ANON_KEY` | prod | - | Supabase anon public key |
| `AWT_SUPABASE_JWT_SECRET` | **yes** | - | JWT signature verification secret |
| `AWT_DATABASE_URL` | no | `sqlite+aiosqlite:///./awt_cloud.db` | DB connection string |
| `AWT_RATE_LIMIT_FREE` | no | `5` | Free monthly limit |
| `AWT_RATE_LIMIT_PRO` | no | `-1` | Pro monthly limit (-1=unlimited) |
| `AWT_DEBUG` | no | `false` | SQLAlchemy echo etc |

---

## Directory Structure

```
cloud/
├── app/
│   ├── main.py          # FastAPI app entry point
│   ├── config.py         # pydantic-settings environment variables
│   ├── database.py       # SQLAlchemy async engine
│   ├── models.py         # ORM models (Test, User)
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── auth.py           # Supabase JWT verification + get_current_user
│   ├── middleware.py      # Rate limiting
│   └── routers/
│       └── tests.py      # /api/tests CRUD
├── tests/
│   ├── conftest.py       # Fixtures (in-memory DB, mock user)
│   ├── test_health.py
│   ├── test_tests_api.py
│   ├── test_rate_limit.py
│   └── test_auth.py      # JWT verification tests
├── requirements.txt
└── README.md
```
