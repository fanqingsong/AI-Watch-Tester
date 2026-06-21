# AWT Cloud Frontend

Next.js web frontend for AWT Cloud — AI-powered web testing.

## Prerequisites

- Node.js 18+
- Backend running at `http://localhost:8000` (see `cloud/` directory)

## Setup

```bash
cd cloud/frontend
npm install
```

## Environment

Create `.env.local` (optional — defaults work for local dev):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> The frontend runs in **local mode**: no authentication, no Supabase. Every visitor is treated as the built-in local user.

## Run

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page with pricing |
| `/dashboard` | URL input + real-time test progress |
| `/tests` | Test history list with filter |
| `/tests/{id}` | Test detail with screenshots |
| `/status` | Backend status |
| `/settings` | Settings |

## Backend

Start the FastAPI backend first:

```bash
cd cloud
source ../.venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

CORS is configured for `localhost:3000`.
