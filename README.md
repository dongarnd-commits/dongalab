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
Root .env is read by Compose and Backend. BIZINFO_API_KEY is a Backend SecretStr used only by the Live collector.

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

The deterministic adapter preserves English labelled clauses and supports bounded Korean heading/body clauses. General notice interpretation is not implemented.
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


## Bizinfo ingestion slice

After `uv sync --locked`, run `uv run alembic upgrade head`. Migration a44df74db1ac follows the Notice migration;
existing Notice data remains intact. Start the API and `uv run python -m app.worker` as above.
The same persistent PostgreSQL Job/Attempt queue now distinguishes NOTICE_ANALYSIS and BIZINFO_COLLECTION;
collection pages and item outcomes persist separately. No scheduler or additional queue platform is used.

Login as the local DATCO_OPERATOR at `/notice`. In Bizinfo Collection, choose **SANITIZED / DEMO snapshot** or
**Live Bizinfo API**, then Request collection. Results show mode, attempts, pages, new/unchanged/version/duplicate/conflict
outcomes and source failures. Review collected notice selects the existing Notice detail and analysis/review controls.
Collection success does not request analysis or confirm requirements automatically. Refresh preserves the stored history.
Retry preserves previous attempts and successful imports. A new NoticeVersion keeps previous candidates/reviews/confirmations;
new input requires a new analysis and human review.

Live endpoint: `https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do`; Backend-only `BIZINFO_API_KEY` in ignored root `.env`.
The client uses observed `crtfcKey`, `dataType=json`, `searchCnt=0`, `pageIndex`, `pageUnit`, and `jsonArray`.
Manual browser requests use at most 3 pages of 2 notices. Backend commands accept page_unit/max_pages 1..5.
Local safety limits are 15 seconds per HTTP request, at most 2 attempts for transient network/5xx failures,
1 MiB per API page, 8 MiB per source, and a 120-second collection budget. These are local guards, not official rate limits.
Short pages still require Empty confirmation; count changes, mismatches, repeated pages and a reached limit remain visible.
A bounded page limit reports PARTIAL and does not claim a full Bizinfo sweep. No silent Snapshot fallback occurs.

Raw successful page JSON is immutable content in ignored private storage, referenced by a CollectionPage and record position.
Live Raw may contain contacts and is not a shareable fixture; the collection API excludes raw storage keys/content.
Source provenance records mode, origin, time, source field/URL, immutable hash and acquisition outcome.
Only official HTTPS Bizinfo hosts and matching detail IDs are accepted; private DNS addresses and redirects are blocked.
Downloads enforce received-byte/time limits. A supplied attachment URL is not evidence that its file was acquired.
PDF is identified by signature and strict parse, not by octet-stream MIME or print-file role. Other formats remain unsupported.
HTML acquisition verifies encoding and notice identity; general portal selectors and complete body extraction remain unverified.
HTML version comparison uses supported labelled clauses only; an otherwise unknown changed detail is held for review.
Failed reacquisition does not delete a previously acquired source or fabricate a content change.

The input-only `apps/api/fixtures/bizinfo/demo.json` follows Probe-verified field names but has synthetic, sanitized content
and a DEMO external ID that does not collide with real Live IDs. Its HTML/PDF run through the same FileProvider,
Normalizer, Notice input use case, Analysis Worker, evidence and Human Review as Live-derived notices.
The existing Probe samples are retained as masked shape evidence; they are not presented as complete analysis fixtures.
No Candidate, Review or Confirmed Requirement is preseeded by this snapshot.

Run `uv run pytest` against PostgreSQL. After API startup, regenerate contracts with `npm.cmd run api:types`,
then run lint/build/test:e2e. Collection browser tests cover snapshot persistence, deduplication, existing analysis/human confirmation,
and unauthorized requests. Controlled Live response tests are test doubles and do not establish real Live availability.
A limited real validation on 2026-10-12 performed 4 requests for one API record and its 3 references:
metadata/Notice persistence and detail HTML succeeded; the API filename metadata identifies ZIP and HWP references, which were not valid supported PDFs and remain missing.
The job is PARTIAL due to acquisition failures and the explicit one-page limit. Live PDF/whole-document analysis is not verified.
The analyser now supports bounded Korean heading/body clauses in addition to English labels; general Korean portal interpretation, OCR, HWP/HWPX,
production heartbeat, scheduling and other business domains remain outside this slice.

Formal docs/10 acceptance stays NOT_RUN / system NOT_TESTED. No docs/00~11 or Probe artifacts are changed.


## Notice operator UI

The Korean /notice screen is the government support notice module: normal notice catalog, notice detail/requirement review, and collection under operations tools.
The normal catalog includes only stored versions explicitly marked LIVE. It excludes Demo/TEST and does not imply official recruitment status or complete Bizinfo coverage.
Click a program name to open its detail. The selected notice and screen are kept in URL parameters using the native History API, including back/forward and refresh.
Demo/TEST records and Sanitized Snapshot input remain accessible through the explicit test/demo entry under operations tools; this UI context is not authorization.
Collection requests use existing DATCO_OPERATOR/Origin/Session guards. The normal collection screen uses Live; test/demo mode enables the existing Snapshot selector.
Acquisition state, unsupported files, PARTIAL, source errors and attempts are retained in detail/operations views rather than a catalog column.
Basic requirement extraction is the existing limited labelled-clause rule adapter, not general AI interpretation. Candidate, execution success and scoped human confirmation remain distinct.
Raw IDs, provenance JSON and execution data are collapsed under technical details. Earlier versions, analysis and confirmation records remain available.
Existing list/detail APIs, Backend guards and source download permissions are unchanged; no schema, contract or Worker change is required.
Catalog detail hydration is for the current local slice; large-scale server pagination and aggregation are outside this UI change.


## Korean notice requirement slice

`labelled-clauses-ko-v3` recognizes explicit Korean headings and their body within each Source,
including numbered headings, bullet summaries, split period text, PDF pages and submission tables.
It maps eligibility, application period, support scope, required documents, exclusion conditions
(`CONDITIONAL_REQUIREMENT`) and evaluation criteria into existing Candidate kinds. Values remain
verbatim source text; complex table cells, legal exceptions and page continuations require human review.
Keyword mentions, heading-only contents and attachment-reference-only headings are not requirements.

Multiple-line Evidence keeps exact extracted text and a bounded first/last block or line descriptor,
within one Source and PDF page. FileProvider reconstructs the same contiguous range before confirmation;
old single-line HTML/PDF locations remain valid. HTML extraction boundaries are unchanged to protect
historical evidence. This does not add DOM selectors, coordinates, OCR, HWP/HWPX or ZIP support.

Worker diagnostics reuse `AnalysisRun.missing`: acquired/extracted text with no recognized requirements
is distinguished from missing/unsupported files and extraction failure. A zero-candidate run stays FAILED
with `NO_VALID_REQUIREMENT_CANDIDATE`; a diagnostic Run preserves inspected scope without candidates.
Korean rule coverage remains PARTIAL with recognized/unrecognized kinds and manual-review limitations;
neither execution status nor an unrecognized field is an eligibility decision. Invalid provider output
still cannot be published. Successful English labelled fixture statuses retain their previous behavior.

Verification uses stored public Live sources read-only and copies them into rollback-only PostgreSQL
schemas. No original Live NoticeVersion, Candidate, Review or Confirmed Requirement is changed.
The opt-in local real-source regression requires both previously acquired notices and fails if inputs
are missing; no full public raw document, contact data or PDF is added to Git.

~~~powershell
cd apps/api
$env:DATCO_TEST_STORED_KO = "1"
uv run pytest
Remove-Item Env:DATCO_TEST_STORED_KO
cd ../web
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e
~~~

`tests/korean-requirements.spec.ts` starts its own localhost test API using copies of stored Korean
HTML/PDF input in an isolated schema. Browser requests are forwarded to the actual test API, which uses
existing session/Origin guards and the same `process_one` Worker path. The test checks source download,
PDF page 15 evidence, human confirmation and refresh; shutdown rolls back the entire test schema.
The existing runtime API/Web/Worker are reused without termination. A running production-like Worker
keeps its already imported adapter until the operator restarts it; new isolated test executions use v3.
No Schema, API Contract, Permission, State, Dependency or docs/00~11 change is required.
Formal system acceptance remains NOT_TESTED; this slice does not implement downstream matching.


### Korean accuracy review

Period conflict comparison recognizes explicit equivalent date formats, split HTML lines and a short
quoted year with an omitted end year. An unspecified cutoff time is unknown; a PDF-only explicit time
remains in its original Candidate/Evidence. Different dates or conflicting explicit times remain conflicts,
as do unparseable/conditional periods. The announcement period is not substituted for the application period.
All source expressions and locations are retained, including when comparison finds no conflict.

Scoped overview clauses retain their original department/track wording (for example a named award division)
and are not converted into a notice-wide eligibility condition. Downstream matching must use reviewed
scope and exceptions, not flatten these texts into common requirements.
Summary HTML is projected into inert plain text for display. Long required-document content can be expanded,
with original line breaks; stored Candidate, Evidence and historical review snapshots are unchanged.
