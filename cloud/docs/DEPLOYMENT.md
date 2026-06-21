# Deployment Guide

Deploy AWT Cloud using **Vercel** (frontend) + **Render** (backend). The backend is fully self-contained — it uses a local SQLite database and a built-in local user, so **no external auth or database service (e.g. Supabase) is required**.

---

## Architecture

```
User Browser
  ├── Vercel (Next.js frontend) — local mode, always "logged in"
  └── Render (FastAPI backend)
        ├── SQLite (local database, persisted to disk)
        ├── Playwright (headless Chromium)
        └── OpenAI / Claude / Ollama (AI provider)
```

---

## Prerequisites

- [Render](https://render.com) account (free tier: 512MB RAM)
- [Vercel](https://vercel.com) account (free tier: hobby plan)
- AI API key: OpenAI or Anthropic (Ollama cannot run on Render)

> No Supabase or any other auth/DB account is needed.

---

## Step 1: Deploy Backend on Render

### Option A: One-Click (render.yaml)

1. Push your repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) > **New > Blueprint**
3. Connect your repo — Render reads `render.yaml` automatically
4. Set the environment variables (see table below)
5. Click **Apply**

### Option B: Manual Setup

1. Go to **New > Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Name**: `awt-api`
   - **Runtime**: Docker
   - **Dockerfile Path**: `cloud/Dockerfile`
   - **Docker Context**: `.` (project root)
4. Set environment variables (see table below)
5. Set **Health Check Path**: `/health`
6. Click **Create Web Service**

### Backend Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `AWT_DATABASE_URL` | No | `sqlite+aiosqlite:///./data/awt_cloud.db` | DB connection string. Defaults to local SQLite. Any SQLAlchemy async URL works (e.g. your own Postgres). |
| `AWT_AI_PROVIDER` | Yes | `openai` | AI provider: `openai` or `claude` |
| `AWT_AI_API_KEY` | Yes | `sk-...` | AI provider API key |
| `AWT_AI_MODEL` | No | `gpt-4o-mini` | Model override (auto-selects if empty) |
| `AWT_CORS_ORIGINS` | Yes | `https://your-app.vercel.app` | Comma-separated allowed origins |
| `AWT_PLAYWRIGHT_HEADLESS` | No | `true` | Always true for cloud (default) |
| `AWT_MAX_CONCURRENT` | No | `1` | Max concurrent tests (1 for free tier) |
| `AWT_SCREENSHOT_DIR` | No | `screenshots` | Screenshot storage path |
| `AWT_UPLOAD_DIR` | No | `uploads` | Upload storage path |
| `AWT_SENTRY_DSN` | No | `https://...@sentry.io/...` | Sentry error tracking (optional) |

### Persisting the SQLite database

SQLite stores data in a single file. On Render, attach a **Disk** to the backend service and point `AWT_DATABASE_URL` at a path on that disk so data survives deploys/restarts:

```
AWT_DATABASE_URL=sqlite+aiosqlite:///./data/awt_cloud.db
```

(If you prefer PostgreSQL, set `AWT_DATABASE_URL` to your own `postgresql+asyncpg://...` connection string — any standard Postgres host works.)

---

## Step 2: Deploy Frontend on Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard) > **Add New > Project**
2. Import your GitHub repo
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `cloud/frontend`
4. Set environment variables:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://awt-api.onrender.com` (your Render URL) |

5. Click **Deploy**

> The frontend runs in local mode (no auth). No Supabase variables are needed.

### CORS Configuration

After Vercel deploys, update the Render backend's `AWT_CORS_ORIGINS`:

```
https://your-app.vercel.app,https://your-custom-domain.com
```

---

## Step 3: Verify

1. Visit your Vercel URL — landing page should load
2. Check backend health: `curl https://awt-api.onrender.com/health`
3. Create a test with a URL (no signup/login step — local mode)
4. Verify AI generates scenarios and tests execute

---

## Free Tier Limitations

| Service | Limit | Impact |
|---------|-------|--------|
| **Render Free** | 512MB RAM, sleeps after 15min idle | First request after sleep takes 30-60s; max 1 concurrent Playwright test |
| **Vercel Hobby** | 100GB bandwidth/month | Sufficient for development and demos |

### Render Sleep Behavior

The free tier spins down after 15 minutes of inactivity. The first request after sleep takes 30-60 seconds as the container restarts. This is acceptable for development and demos but not for production use.

### AI Provider Note

**Ollama cannot run on Render** (requires GPU or significant RAM). For cloud deployment:

- Use **OpenAI** (`gpt-4o-mini` is cost-effective) or **Anthropic** (`claude-sonnet`)
- Set `AWT_AI_PROVIDER=openai` and `AWT_AI_API_KEY=sk-...`
- Or run without AI and use manual scenario input

---

## Troubleshooting

### CORS errors in browser console

Update `AWT_CORS_ORIGINS` on Render to include your exact Vercel domain (no trailing slash):

```
AWT_CORS_ORIGINS=https://your-app.vercel.app
```

### Frontend shows "Backend Unreachable" on status page

- Check that `NEXT_PUBLIC_API_URL` points to the correct Render URL
- Verify the backend is awake: `curl https://awt-api.onrender.com/health`
- Render free tier may be sleeping — first request wakes it up

### Playwright crashes with OOM on Render

Reduce `AWT_MAX_CONCURRENT` to `1`. Chromium uses ~200-300MB RAM, leaving limited headroom on the 512MB free tier.

### Database issues

- For SQLite: ensure the path in `AWT_DATABASE_URL` lives on a persistent Render Disk, or data resets on redeploy
- For Postgres: ensure `AWT_DATABASE_URL` uses the `postgresql+asyncpg://` prefix and that the password is URL-encoded if it contains special characters

### WebSocket connection fails

- Render supports WebSocket on free tier
- Ensure the frontend connects to `wss://` (not `ws://`) for HTTPS backends
- The frontend auto-converts `https://` to `wss://` in the API client
