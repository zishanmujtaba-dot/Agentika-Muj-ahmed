# ECHO

A university policy helpdesk with grounded retrieval, optional voice, department routing, and human staff replies. Sample policies are demonstration fixtures, not verified FAST NUCES guidance.

## Run the entire demo with Docker

You need Git and Docker with Compose. No managed cloud services or host Python installation are required.

```sh
git pull --ff-only origin main
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env`. If `.env` already exists, keep it and add any missing settings instead of overwriting it.

Edit your local `.env`:

- `GROQ_API_KEY`: your own GroqCloud key; leave blank to test staff handoffs without model usage.
- `PG_READONLY_PASSWORD`: choose a private runtime database password; replace the placeholder.
- `STAFF_PASSWORD`: choose a private staff sign-in password; replace the placeholder.
- Keep `PG_READONLY_USER=echo_runtime`, `STAFF_USERNAME=staff`, and the supplied local database settings.

Then run:

```sh
docker compose up -d --wait --wait-timeout 180
docker compose --profile setup run --build --rm bootstrap
docker compose --profile app up -d --build --wait --wait-timeout 180
```

The initial image build downloads CPU-only model dependencies and caches the embedding model; allow several minutes. Setup runs schema creation, repeatable demo-data ingestion, and restricted runtime grants inside a temporary container. The running app receives runtime credentials, not ingestion administrator credentials. Startup does not call Groq.

Open [student chat](http://localhost:8001/) and [staff sign-in](http://localhost:8001/staff). Sign in with `STAFF_USERNAME` / `STAFF_PASSWORD` from your own `.env`. Database volumes retain messages, tickets, policies, and graph data across container restarts.

A blank Groq key makes policy answer requests fall back to staff; it does not produce AI-generated answers. Your partner's key stays in their own ignored `.env`. Never commit this file.

## Demo and handoff

The expanded [student rulebook](docs/reference/student-rulebook.md) contains 41 fictional public policies. Use the [demo question guide](docs/demo-questions.md) for supported answers, edge cases and human handoffs. The [memory assessment](docs/reference/conversation-memory.md) explains why chat history is persisted but previous turns are not sent to the model. The runtime uses the Groq SDK directly, without LangChain or LangGraph.

See [Docker runbook](docs/docker-demo.md) for the demo script, logs, updates, stopping, and recovery. [Partner setup](docs/partner-setup.md) includes the optional host-Python workflow and API access details. [Verification](docs/verification.md) distinguishes actual checks from model-stubbed checks and remaining manual items.

## Layout

```text
app/             FastAPI, existing RAG pipeline, durable conversation storage
web/             Student and authenticated staff interfaces
scripts/         Offline ingestion/setup and container startup
data/            Labeled sample policies and university structure
database/        Repeatable PostgreSQL schema
/docs/plans/     Four-sprint plan and progress
/docs/reference/ Original project description
reusable_files/  Superseded prototype and temporary marker
/tests/          Local integration checks with Groq disabled
```

## Optional host Python development

Use Python 3.12. After copying/configuring `.env` and starting the two database services:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
docker compose exec -T postgres psql -U postgres -d postgres < database/schema.sql
python scripts/insert_policies.py
python scripts/insert_graph.py
python scripts/configure_runtime.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`configure_runtime.py` can generate local runtime and staff passwords for this workflow. The direct dependency constraints select platform-appropriate packages; `requirements.lock` records the resolved macOS development environment. Keep a single backend process for the demo. Health: `/health`; database readiness: `/ready`; API schema: `/docs`.

## Scope

Local Docker is the agreed submission target. A Dockerfile and configurable container port also support later hosting, but a public deployment is not part of this handoff. Neo4j still uses the configured graph account, staff share one demo identity, and generated answer quality requires a live Groq check with the intended developer's key. No production readiness is claimed.
