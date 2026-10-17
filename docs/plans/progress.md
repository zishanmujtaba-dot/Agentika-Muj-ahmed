# ECHO implementation progress

## Sprint status

| Sprint | Status |
| --- | --- |
| 1 — Baseline and organization | Complete locally; external answer generation and cloud state unverified |
| 2 — Backend reliability | Next |
| 3 — Student and staff experience | Pending |
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

## Next sprint blocker list

1. Verify actual Groq output once external-data permission is granted; add bounded model/network failures and inspect model support.
2. Calibrate retrieval threshold and category fallback. The existing pipeline bases escalation only on distance/model failure; a model's textual refusal after a confident match does not itself open a ticket. Explicit human requests need handling.
3. Make graph lookup failure nonfatal and return a clear default department. Related graph IDs are currently returned as metadata, not expanded policy text.
4. Repair transaction handling on pooled-connection errors and set dependency timeouts. Runtime PostgreSQL uses demo admin credentials; read-only policy privileges are optional commented SQL, not enforced. Neo4j also uses admin credentials.
5. Add text input, backend-validated staff authentication, conversation authorization, safe rendering, and robust polling/voice sending. Current staff reply trusts a client-provided session ID.
6. Persist replies if a small change fits; otherwise explicitly retain the single-process, restart-loss limitation. Do not add Redis for this submission.

## Startup and demo path

Run commands from repository root using .venv. Full setup is in README.md.

```sh
docker compose up -d
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

The local preview is running on port 8001 because port 8000 was already occupied. Health, student page, and staff page returned HTTP 200 from the actual running server.

Student: http://localhost:8001/ — staff: http://localhost:8001/staff — health: http://localhost:8001/health.

Use the sample attendance question, an unrelated cake question, and a staff reply as the initial demo. Public hosting is not ready until staff access and session isolation are fixed. Health currently reports liveness only.

The four-sprint submission plan is implementation.md. Continue from this record rather than rebuilding the existing components.
