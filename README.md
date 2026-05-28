# RunRecover MVP

RunRecover is an AI-assisted post-run recovery MVP for everyday runners. The first version focuses on one complete demo loop:

1. User enters run data, RPE, sleep, fatigue, soreness, and tomorrow's plan.
2. The API computes a transparent recovery pressure score using distance, duration, run type modifiers, recent 48-hour load, and tomorrow-plan conflict.
3. The result explains the main factors, including RPE, duration, recent load, and safety conflicts when they materially affect the score.
4. Template-backed or LLM-backed advice returns diet, hydration, sleep, relaxation, tomorrow guidance, and a 24-hour timeline, with content-level safety validation.

The repository uses a React + FastAPI + SQLite split:

- `apps/api`: FastAPI backend, scoring rules, safety guard, template recommendations, SQLite persistence, pytest tests.
- `apps/web`: Vite React TypeScript frontend with demo cases and a single-page MVP flow.
- `docs`: MVP, API, demo-case notes, and the full product user manual.

## Quick Start

### One-command local demo

Install backend and frontend dependencies once:

```bash
cd apps/api
python3 -m venv .venv
./.venv/bin/python3 -m pip install -r requirements.txt

cd ../web
npm install
```

Then start both services from the repository root:

```bash
npm run dev
```

This runs:

- FastAPI API: `http://127.0.0.1:8000`
- Vite Web: `http://127.0.0.1:5173`

You can also run the script directly:

```bash
./scripts/dev.sh
```

The script respects these optional environment variables:

- `RUNRECOVER_API_HOST`, `RUNRECOVER_API_PORT`
- `RUNRECOVER_WEB_HOST`, `RUNRECOVER_WEB_PORT`
- `VITE_API_BASE_URL`

### API

```bash
cd apps/api
python3 -m venv .venv
./.venv/bin/python3 -m pip install -r requirements.txt
./.venv/bin/python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

### Web

```bash
cd apps/web
npm install
cp .env.example .env
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

For a complete local demo guide with command explanations, API examples, and presenter notes, see `docs/user-manual.md`.

## Productization Path

RunRecover should stay lightweight while the MVP is being validated.

Recommended phases:

1. Local one-command startup for development and demos.
2. Web App / PWA deployment: host the React app behind HTTPS and deploy the FastAPI API with SQLite or a managed database.
3. Consider a WeChat Mini Program or native iOS/Android app only after user validation shows that distribution channel is worth the extra maintenance.

The current frontend already includes basic PWA metadata:

- `apps/web/public/manifest.webmanifest`
- app icons under `apps/web/public/icons`
- mobile `theme-color` and Apple web app metadata
- production-only service worker registration for install/add-to-home-screen support

For production API access, configure backend CORS with:

```bash
RUNRECOVER_ENV=production
RUNRECOVER_CORS_ORIGINS=https://your-web-domain.example
```

For production frontend builds, configure:

```bash
VITE_API_BASE_URL=https://your-api-domain.example
```

This keeps the current React + FastAPI + SQLite architecture intact while making the app easier to demo and deploy as a Web/PWA product.

## Tests

```bash
cd apps/api
./.venv/bin/python3 -m pytest

cd apps/web
npm run build
```

## MVP Scope

Included in v1:

- Recovery score from distance, duration, run type, RPE, sleep, fatigue, soreness, run time, heart rate if present, and tomorrow-plan conflict.
- Main run type plus optional modifiers such as progressive, hills, target-pace block, and interval subtypes.
- Lightweight user level calibration for beginner, regular, and advanced runners.
- Recent 48-hour training context, lightweight feedback, and the latest 7 recovery records.
- Safety override flags for concerning symptoms and high-load combinations.
- Template recommendations that keep the demo stable without external API dependencies.
- Three frontend demo cases: easy recovery run, sleep-debt steady run, long muscle-load run.
- Optional LLM-backed recommendation providers with template fallback.

Not included in v1:

- Accounts, historical trends, device sync, GPX/CSV upload, calendar reminders, commercial admin tools.
- Native iOS/Android app or WeChat Mini Program implementation.
