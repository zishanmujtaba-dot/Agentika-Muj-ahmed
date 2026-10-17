# ECHO

University policy helpdesk with public-policy retrieval, graph-assisted routing, and student-to-staff handoff. The bundled policies are demonstration data, not verified official university guidance.

## Repository layout

```text
app/             FastAPI backend and existing RAG pipeline
web/             Canonical student and staff pages
scripts/         Offline policy and organizational-data ingestion
data/            Sample policies and university structure
database/        PostgreSQL schema
docs/plans/      Four-sprint implementation plan and progress
docs/reference/  Original project description in Markdown and DOCX
reusable_files/  Superseded prototype and temporary marker
```

## Partner handoff

Pull the repository and follow [partner setup and testing](docs/partner-setup.md). Each developer supplies their own ignored `.env` with their own GroqCloud key. The guide includes macOS/Linux and Windows commands and a typed test through the API docs.

## Local setup

Use Python 3.12 and a running Docker engine. Run all commands from the repository root. `requirements.txt` lists direct compatibility constraints; `requirements.lock` records the resolved Python 3.12 environment.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
cp .env.example .env
# Edit .env and set GROQ_API_KEY before starting the backend.
docker compose up -d
# Wait until both databases are accepting connections.
# New PostgreSQL volumes load database/schema.sql automatically.
# This command also applies the schema to existing volumes without deleting data:
docker compose exec -T postgres psql -U postgres -d postgres < database/schema.sql
python scripts/insert_policies.py
python scripts/insert_graph.py
python scripts/configure_runtime.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The first policy ingestion downloads the embedding model and may take longer. Do not delete database volumes to retry setup. The `.env` file is ignored by Git. Local database credentials in the example and Compose file are demo defaults; replace the admin defaults for public deployment. `configure_runtime.py` generates a dedicated PostgreSQL role with public-view reads and ticket writes, saving its credentials to `.env`. Re-run it after adding future ticket tables/grants. Neo4j still uses the configured graph credentials; read-mode queries alone do not enforce graph privileges.

Open the student page at <http://localhost:8000/> and staff page at <http://localhost:8000/staff>. Both use the same origin for API calls. API schema: <http://localhost:8000/docs>; health: <http://localhost:8000/health>. Current health is a liveness response, not a full dependency readiness check.

## Current baseline and next work

The existing Python pipeline and ingestion scripts have been reused. Sprint 2 adds public-only retrieval, validated cited responses, explicit handoffs, bounded dependency calls, and optional restricted-role setup. Runtime/model evaluation is deferred to final testing; this does not certify a working cloud deployment. See [progress and blockers](docs/plans/progress.md) and the [four-sprint plan](docs/plans/implementation.md).

The current student page is voice-only, staff routes are unauthenticated, and live replies are in memory. Do not expose this baseline publicly before the planned access-control fixes.

For cloud hosting, the eventual start command is `python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"`, with the host platform supplying PORT and reachable PostgreSQL/Neo4j settings. Build packaging and cloud verification remain Sprint 4 work.
