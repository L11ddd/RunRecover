# RunRecover MVP

RunRecover is an AI-assisted post-run recovery MVP for everyday runners. The first version focuses on one complete demo loop:

1. User enters run data, RPE, sleep, fatigue, soreness, and tomorrow's plan.
2. The API computes a transparent recovery pressure score.
3. The result explains the main factors, including RPE when it materially affects the score.
4. Template-backed AI advice returns diet, hydration, sleep, relaxation, tomorrow guidance, and a 24-hour timeline.

The repository uses a React + FastAPI + SQLite split:

- `apps/api`: FastAPI backend, scoring rules, safety guard, template recommendations, SQLite persistence, pytest tests.
- `apps/web`: Vite React TypeScript frontend with demo cases and a single-page MVP flow.
- `docs`: MVP, API, demo-case notes, and the full product user manual.

## Quick Start

### API

```bash
cd apps/api
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

### Web

```bash
cd apps/web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

For a complete local demo guide with command explanations, API examples, and presenter notes, see `docs/user-manual.md`.

## Tests

```bash
cd apps/api
./.venv/bin/pytest

cd apps/web
npm run build
```

## MVP Scope

Included in v1:

- Recovery score from distance, duration, run type, RPE, sleep, fatigue, soreness, run time, heart rate if present, and tomorrow-plan conflict.
- Safety override flags for concerning symptoms and high-load combinations.
- Template recommendations that keep the demo stable without external API dependencies.
- Three frontend demo cases: easy run, high-intensity night run, long high-RPE run.

Not included in v1:

- Accounts, historical trends, device sync, GPX/CSV upload, calendar reminders, commercial admin tools.
- Direct LLM API calls. The provider interface is reserved for a later integration.
