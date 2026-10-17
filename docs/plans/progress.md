# ECHO implementation progress

## Sprint status

| Sprint | Status |
| --- | --- |
| 1 — Baseline and organization | Complete locally; external answer generation and cloud state unverified |
| 2 — Backend reliability | Implemented; runtime checks deferred to final testing |
| 3 — Student and staff experience | Implemented; runtime/browser checks deferred to final testing |
| 4 — Deployment and submission | Pending |

## Sprint 1 completed

- Preserved and reused the Python backend, retrieval pipeline, ingestion scripts, SQL schema, and sample data.
- Organized the repository into app, web, scripts, data, database, docs, and reusable_files directories. The early voice page and temporary commit marker are archived; the newer session-aware page is canonical.
- Updated package imports, ingestion file paths, document references, and browser API URLs. FastAPI serves both pages from the API origin.
- Added environment template, secret/virtualenv ignores, dependency constraints, resolved Python 3.12 dependency lockfile, and exact startup instructions.
- Created the local virtual environment and installed dependencies. Started the existing Colima Docker runtime and the project's PostgreSQL and Neo4j containers. Database host ports bind only to localhost.
- Initialized PostgreSQL schema and loaded six demo policies plus the existing organizational graph through the original ingestion scripts.
- Saved the supplied Groq credential in the ignored, owner-readable-only .env. The mistakenly supplied xAI key is not used or retained in that file. No secret is committed.

## Verification evidence

- Python syntax, sample JSON, Compose configuration, Git whitespace checks, secret exclusions, and installed dependency compatibility passed.
- PostgreSQL accepts connections and contains policies/escalations; Neo4j connectivity query passed.
- HTTP wiring check with a stubbed pipeline passed for student/staff pages, health, required session ID, polling isolation, and staff reply delivery.
- Local integration used real embedding model, PostgreSQL retrieval, Neo4j lookup, ticket creation/resolution, and FastAPI routes. All external LLM calls were disabled: intent used the original question, answer text was a fixed test placeholder.
- Attendance question retrieved the attendance policy but also four other public policies: threshold calibration remains necessary.
- Cake-baking question returned no confident match, created an escalation, accepted a staff reply, and delivered it only to the matching test session. Its test ticket was resolved.
- External Groq answer generation was blocked by automatic approval review pending explicit permission to send sample policy context and demo questions to Groq. Do not claim the key, selected model, generated citations, or end-to-end model quality have been verified.
- No deployed app URL or cloud database credentials were supplied; Alternate Clouds deployment and push automation remain unverified.

## Partner handoff

See ../partner-setup.md for a fresh checkout, local credentials, database loading, and exact model/staff test steps. No live Groq calls were made during preparation of the handoff.

## Sprint 2 implemented

- Reused the embedding, PostgreSQL, Neo4j, ingestion, and ticket code while repairing the request flow.
- Local category hints replace the intent-parsing model call. Category misses retry unrestricted public retrieval. No-match requests create tickets without calling Groq.
- Retrieval now uses a public-only PostgreSQL view, a provisional 0.60 distance ceiling, a relative relevance margin, and at most three direct matches. This threshold still needs final calibration.
- Related graph policies are loaded through the same public view. Graph queries have limits/timeouts and failure falls back without dropping valid evidence. Routing uses the closest direct match.
- Model generation requests structured JSON. Application validation requires a supported public policy ID and a verbatim supporting excerpt; malformed responses, refusals, unsupported citations, and provider failures create tickets. This validates provenance, not full semantic entailment.
- Explicit human requests and restricted-record requests produce handoffs. Responses include status, ticket ID, reason, citation metadata, and whether ticket storage actually succeeded.
- Pending-ticket retries for the same conversation/question reuse a ticket under a PostgreSQL transaction lock. Failed ticket writes return an honest unsaved-follow-up message.
- Added bounded provider calls, safe exception logging, PostgreSQL timeouts, pooled-transaction rollback, shutdown cleanup, and request-length/whitespace validation.
- Ingestion validates IDs, required fields, access levels, categories, tags, and embedding dimensions before writes. It applies the shared schema and commits the upsert batch atomically.
- Added offline scripts/configure_runtime.py to grant public-view reads and ticket writes to a dedicated PostgreSQL role and save generated credentials only in local .env. No HTTP route can run this setup. Neo4j privilege enforcement remains incomplete; query READ mode is only a client hint.

Per user instruction, Sprint 2 runtime/integration/model tests are deferred until the final testing pass. No Groq calls were made. Only source syntax and whitespace checks were performed. The updated schema and role setup must be applied before restarting this version:

```sh
docker compose exec -T postgres psql -U postgres -d postgres < database/schema.sql
python scripts/configure_runtime.py
```

## Sprint 3 implemented

- Student chat supports typed questions and optional voice, complete conversation history, clear pending/escalated/error states, sample prompts, mobile layout, and opt-in interruptible speech output.
- Voice recognition sends once on the end event after explicit stop, with interim transcript in the question field and typed fallback for permission/support errors.
- Server-generated conversation IDs require a separate random token on ask/poll. PostgreSQL stores only token hashes. The browser stores its token in per-tab session storage and can restore history after a refresh.
- Replaced in-memory queues with durable PostgreSQL messages and ID-based polling cursors. Per-conversation transaction locks serialize message writes and reads to prevent cursor skips across concurrent commits.
- Questions have retry-safe request IDs and stored results. Active duplicate requests return 409; interrupted reservations can be recovered after 120 seconds. A stale process cannot overwrite a newer reservation's result.
- Staff sign-in uses backend-validated credentials from local environment, constant-time comparison, and a small per-process failed-login limiter. No staff password is embedded in public assets or browser storage. Cross-origin API access is disabled and app pages use a strict content security policy.
- Staff queue renders untrusted fields as text, preserves drafts during polling, shows loading/empty/error states, and verifies reply responses before showing success.
- Staff replies use the ticket's stored conversation, save author/timestamp/message and ticket resolution atomically, and safely replay an identical retry. Another reply to an already resolved ticket is rejected. Legacy tickets without a secure conversation are shown as not deliverable.
- Offline role setup now grants only the required conversation/message/request privileges and generates a local staff password. Reapply schema and rerun setup before restarting.

Python/JavaScript syntax and whitespace checks passed for this sprint. Application, browser, persistence, permission, concurrency, and Groq tests remain deferred by user instruction. No Groq requests were made. Completed implementation does not imply verified acceptance criteria.

## Next actions

1. Sprint 4: package cloud startup, verify the actual deployment route and configuration, run the final focused verification pass, and prepare submission artifacts.
2. Final checks must cover both students' isolation, staff authentication, message/reply persistence across restarts, duplicate asks/replies, failed storage, graph outage, citations, protected-data exclusion, request timeouts, and browser voice/text fallback.
3. Use the designated developer/test key for approved Groq calls; previous automatic approval review required explicit permission to send sample context/questions to Groq. No live provider test has been performed.
4. The public-policy threshold remains provisional; calibrate it using labeled questions during final testing. Keep demo sample policies labeled and document the shared staff identity and graph-privilege limitation.

## Startup and demo path

Run commands from repository root using .venv. Full setup is in README.md.

```sh
docker compose up -d
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

The Sprint 1 preview used port 8001 because port 8000 was occupied and returned HTTP 200. It does not verify Sprint 2 or Sprint 3; restart only after the updated schema and role setup are applied.

Student: http://localhost:8001/ — staff: http://localhost:8001/staff — health: http://localhost:8001/health.

Use the sample attendance question, an unrelated cake question, and a staff reply as the initial demo. Public hosting is not ready until staff access and session isolation are fixed. Health currently reports liveness only.

The four-sprint submission plan is implementation.md. Continue from this record rather than rebuilding the existing components.
