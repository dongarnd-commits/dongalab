# DATCO Phase-1 Skeleton

Minimal runtime path: Browser -> Next.js -> FastAPI -> SQLAlchemy/Psycopg -> PostgreSQL.
The first Notice Requirement review slice adds local session, controlled source files, persistent analysis jobs and human confirmation. Other business domains remain unimplemented.
Approved stack: [Decision-001](docs/11_DECISION_LOG.md). Product and module boundaries remain in [Baseline](docs/00_PROJECT_BASELINE.md) and [Architecture](docs/01_SYSTEM_ARCHITECTURE.md).

## Requirements

Verified runtime: Node 24.19.0 / npm 11.17.0, Python 3.13.15 (py -3.13 on Windows), uv 0.13.0, Docker Engine 29.8.0 / Compose v5.5.1.
Dependencies are locked in apps/web/package-lock.json and apps/api/uv.lock.
Use npm.cmd / npx.cmd in PowerShell if execution policy blocks npm.ps1.

## Local environment

Create a local root .env from .env.example only if .env does not already exist.
Preserve existing secrets. Never commit .env or print its contents.
Set POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, DATABASE_URL and WEB_ORIGIN.
The example password is blank: supply a local password and use the same URL-encoded password in DATABASE_URL.
URL shape: postgresql+psycopg://USER:PASSWORD@127.0.0.1:55432/DATABASE.

Compose exposes PostgreSQL only on 127.0.0.1:55432. API uses 127.0.0.1:8000; Web uses localhost:3000.
Optional Web server environment variable API_ORIGIN changes the API base URL and is never exposed to the browser.
CORS allows only WEB_ORIGIN (default http://localhost:3000).
Root .env is read by Compose and Backend; unrelated keys such as BIZINFO_API_KEY are ignored by Backend settings.

## Start

From repository root:

~~~powershell
docker compose up -d --wait
docker compose ps
~~~

In an API terminal:

~~~powershell
cd apps/api
uv sync --locked
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

In a Web terminal, after API starts:

~~~powershell
cd apps/web
npm.cmd ci
npm.cmd run api:types
npm.cmd run dev
~~~

Open http://localhost:3000. API and Database status come from real uncached FastAPI health requests with bounded timeouts.
Web READY means the current Next.js page rendered; it does not imply downstream services are available.
Refresh to check again. API endpoints: http://127.0.0.1:8000/health, /health/db, /openapi.json and /docs.
DB failure returns HTTP 503 with a generic not_ready response without credentials or driver errors.

## Checks

With PostgreSQL running:

~~~powershell
cd apps/api
uv run pytest
uv run pytest -m integration
uv run alembic current
uv run alembic heads
uv run alembic check
~~~

Run uv run alembic upgrade head before tests or the API. The first migration contains only Notice review, session, file metadata, analysis/job and audit records. Alembic check checks schema drift.

With API and PostgreSQL running:

~~~powershell
cd apps/web
npm.cmd run api:types
npm.cmd run lint
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e
~~~

api:types consumes the running FastAPI /openapi.json and writes src/generated/api.d.ts.
Do not hand-edit generated types. Regenerate after API contract changes.
Playwright starts Next.js dev if needed and uses Chromium.
Smoke checks actual API/DB status and refresh. No SQLite or mock DB replaces integration checks.

For API outage Browser validation, stop the local API with Ctrl+C and run:

~~~powershell
$env:SKELETON_TEST_UNAVAILABLE = "1"
npm.cmd run test:e2e -- --grep "unavailable"
Remove-Item Env:SKELETON_TEST_UNAVAILABLE
~~~

Restart API before normal smoke. Production Web preview: npm.cmd run build, then npm.cmd run start.

## Stop

Use Ctrl+C in Web/API terminals. From root, docker compose stop retains container and volume.
Docker compose down removes this project's container/network and retains its database volume.
Do not use down -v or reset data without explicit approval.
Other Docker projects are outside this skeleton's scope.

## Validation notes (2026-10-12)

PostgreSQL image: official postgres:17, observed PostgreSQL 17.11.
Observed image digest: postgres@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3.
The major tag may receive patch updates; preserve the named volume and review major upgrades separately.

npm audit reports five High findings in the development lint dependency chain:
eslint-config-next -> @next/eslint-plugin-next -> fast-glob -> micromatch -> braces (GHSA-vfj7-8cjw-p6xm).
The registry currently publishes braces 3.0.3 with no patched version.
Do not run audit fix --force: its proposed downgrade breaks the selected Next.js tooling alignment.
The current High findings were reviewed before GitHub sharing and accepted with a note.
They are limited to this Skeleton's development lint dependencies, with no confirmed production runtime exposure or GitHub sharing blocker.
ESLint 9 is deprecated; a compatible supported lint upgrade should be evaluated with that review.
The installed Starlette TestClient also warns about future httpx deprecation; current tests pass.
These notices are separate from full business acceptance, which has not been run.


## First Notice slice

All supplied notices are synthetic DEMO/TEST inputs, not actual government notices.
Existing Bizinfo Probe data is masked and insufficient for text/page evidence; it is not used as a completed analysis fixture.
Local login uses the account stored in the ignored root .env; configure DEMO_OPERATOR_USER and DEMO_OPERATOR_PASSWORD (no public default password).
The Browser role is never used as an authorization source. Local HttpOnly/SameSite=strict sessions and explicit Origin validation are for localhost development.

From apps/api, prepare input-only fixtures and start the same-code Worker:

~~~powershell
uv sync --locked
uv run alembic upgrade head
uv run python -m app.demo
uv run python -m app.demo --fixture conflict
uv run python -m app.demo --fixture partial
uv run python -m app.worker
~~~

If an input fixture changes, re-running the loader creates a new NoticeVersion and retains previous source/analysis/review history; unchanged input is idempotent.
Keep API, Worker and Web in separate terminals. Open http://localhost:3000/notice.
Login, select a notice, request analysis, inspect candidate/source/page evidence, record source verification and review note, then confirm the selected clause.
Confirmed snapshots, reviewer, input Version and evidence persist after refresh.
Job SUCCEEDED means execution succeeded; it never confirms a requirement.
Missing sources remain visible and confirmed scope is limited to selected clauses.
Conflicting period clauses require an explicit human resolution note and retain both source values.
Use the source download action to fetch immutable content through authorized Backend access; raw storage paths are never public URLs.

The deterministic adapter handles explicitly labelled clauses only. General notice interpretation is not implemented.
HTML extraction is for the inspectable fixtures; general government portal selectors are not established.
pypdf 6.20.0 extracts the supplied text PDF's real pages. Image/scanned, encrypted, corrupted and empty documents require additional source/manual review; OCR and Korean PDF font accuracy are not claimed.
Binary files live under ignored storage/private/notice; source/file metadata and evidence locations live in PostgreSQL.

The local Worker claims with PostgreSQL SKIP LOCKED, releases the transaction before extraction, and fences completion by Attempt/state/lease.
A 300-second local execution lease bounds this initial short fixture workload. Production lease/heartbeat policy remains undecided.
To mark expired unfinished execution FAILED without deleting attempts, run uv run python -m app.worker --recover-expired.
Retry creates a new Attempt and preserves previous failure/Run/Review history. Do not use recovery against an active unexpired execution.

Backend acceptance mapping tests are in tests/test_notice_slice.py; they do not change docs/10's formal NOT_RUN records.
With the input fixtures, API and Worker running, npm.cmd run test:e2e runs the original smoke plus login/candidate/evidence/confirm/refresh and unauthorized-access checks.
The outage-specific test remains opt-in as described above.
Stop API/Web/Worker with Ctrl+C; retain the PostgreSQL volume.


### Notice slice regression fixes

Snapshots replace a selected APPLICATION_PERIOD while preserving other reviewed clauses and all historical snapshots.
Reanalysis of the same kind/value does not duplicate the current item.
Successful command replay is identified before checking current input validity; `historical_replay` and `current_valid` are separate response fields.
Confirmation identity includes actor, candidate, input version, verification, note, scope and conflict resolution; a changed command is rejected.
HTTP retry requests supply `idempotency_key`; duplicate retries reuse the recorded receipt and do not create another transition.
Period conflicts compare `period_original` metadata with HTML/PDF clauses and retain both source identities and document locations.
PDF pages without extractable text keep the job PARTIAL and expose page counts, extracted/unextractable pages and the manual-review limitation.
Notice API errors use the same `{ "reason": "..." }` schema in runtime responses, OpenAPI and generated TypeScript.
Changing the selected notice clears its actions immediately and ignores responses from an older selection/request.
Regression tests cover these behaviors, including delayed A response after B selection; formal docs/10 acceptance status remains unchanged.
