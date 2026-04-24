# StudyPilot Phase 3

This repository contains the phase 3 vertical integration baseline for StudyPilot: a FastAPI backend with real parsing, chunking, retrieval, workflow orchestration, scoring, a Next.js frontend shell wired to the contract, and automated verification that covers the full onboarding-to-checkpoint loop.

## Structure

- `apps/api`: FastAPI app, SQLAlchemy models, Alembic migrations, and OpenAPI export script
- `apps/web`: Next.js App Router shell with TanStack Query and generated API types
- `packages/contracts`: exported OpenAPI snapshot used as the single contract source for the frontend
- `tests/api`: backend contract and integration verification
- `tests/e2e`: browser-based phase 3 happy path and fallback path verification
- `storage`: local file storage roots for uploaded source files and parsed artifacts

## Quick start

1. Copy `.env.example` to `.env`
2. Install backend dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .\apps\api[dev]
```

3. Install frontend dependencies:

```powershell
npm install
```

4. Install the Playwright browser used by the E2E suite:

```powershell
npx playwright install chromium
```

5. Export the backend contract and generate frontend API types:

```powershell
npm run contracts:sync
```

6. Run database migrations:

```powershell
python -m alembic -c apps/api/alembic.ini upgrade head
```

7. Start the apps:

```powershell
npm run dev:web
python -m uvicorn app.main:app --reload --app-dir apps/api
```

## Verification

- Backend tests: `pytest tests/api`
- Frontend tests: `npm run test:web`
- Frontend typecheck: `npm run typecheck:web`
- Browser E2E: `npm run test:e2e`

The E2E command starts an isolated SQLite-backed API on `127.0.0.1:8010` and a Next.js dev server on `127.0.0.1:3100`, then verifies:

- happy path: profile -> knowledge upload -> plan -> learning -> checkpoint -> evaluation -> `unit_review`
- fallback path: weak checkpoint submission -> workflow returns to `learning`

## Docker Compose

```powershell
docker compose up --build
```
