# Slice 0a — authenticated role portals

## Approved scope

User execution order: connect the three approved portal presentations to existing authentication only. Existing Role/Permission, Company Scope, workflow guards, immutable versions, migrations and business APIs remain unchanged. This note records implementation; it does not amend FROZEN contracts.

## Authentication and routes

`/login` posts to the existing Next `/api/notice/session` proxy and FastAPI `/notice/session`, using `local_auth`, PostgreSQL actors/sessions and the existing HttpOnly cookie. The server-returned role selects the landing route:

| Role | Landing | Presentation |
| --- | --- | --- |
| COMPANY_EDITOR | /portal/company | Existing company UI; ten business screens |
| DATCO_OPERATOR | /portal/operator | Existing operator UI; twelve screens |
| DATCO_ADMIN | /portal/admin | Existing control center; twelve screens and eleven detail screens |
| COMPANY_APPROVER | / | Existing approval-only Workspace and /proposal |

Each portal Route Handler validates the existing backend session before loading assets. No session redirects to `/login`; another role receives HTTP 403; backend/asset failures return 503. Responses are private/no-store and vary by Cookie. Only authenticated identity (ID, role, account name) is bootstrapped. Workspace business context is not passed into the new UIs.

The standalone HTML presentation reuses the existing UI build approach and bypasses the global Workspace shell, preventing duplicate headers/navigation. `npm run dev` and `npm run build` generate `.role-portals` through lifecycle scripts. Production packaging must include these generated assets; missing assets fail closed with 503. Do not invoke `next build` alone when packaging authenticated portals.

## Session and existing workflows

The client revalidates with the existing session endpoint on refresh/focus/visibility and periodically. Account-change broadcasts, server expiry and logout clear the portal. Logout uses the existing POST API, retains audit and revokes only that session. No password/session token is stored in localStorage. Existing `/company`, `/capability`, `/notice`, `/proposal`, Workspace APIs and approval-only projection remain available.

No company-context integration, business writes or external AI calls are added. Company inputs/business actions are disabled and pending integration is stated. Fixed example requests/proposals/analysis are hidden in authenticated mode. Operator example JSON is imported exclusively by the development preview entry. Real operator counts display `—`; administrator metrics remain disconnected/unmeasured. Existing preview behavior stays development-only and returns 404 in production.

## Verification

- Backend Unit: 87 PASS.
- PostgreSQL Integration: 185 PASS / 1 existing SKIP. The stored Korean Live-source test requires explicit stored-source opt-in; synthetic CI does not claim this validation.
- Three existing portal preview suites: 20 PASS; lint/typecheck/build and production preview 404 passed.
- Authenticated portal + existing business browser regression: 20 PASS. Final authentication suite, including server-side session expiry: 7 PASS. Fresh-head CI runs all 21 distinct scenarios.
- Integration covers PR #9 approver private-file denial, review-memo projection, direct context denial, exact proposal approval and Company Scope.
- No schema, migration, backend auth policy or FROZEN Role/State/Guard changes.

## Deployment hold and excluded work

The existing backend cookie policy remains HttpOnly + SameSite=Strict + Secure=False, intended for local HTTP. HTTPS production deployment requires an explicit secure-cookie/proxy configuration decision and validation. This PR is not deployment authorization: **DEPLOYMENT_HOLD**.

Slice 0b real ID context, company business-data integration, assignment backend, real KPI/infra/AI metrics and new-UI Proposal integration are NOT_STARTED. Actual recommendations are NOT_COMPLETED; complete three-role business E2E and system acceptance are NOT_TESTED. User UI acceptance remains pending.
