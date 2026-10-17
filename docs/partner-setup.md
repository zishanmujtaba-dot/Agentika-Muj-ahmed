# Partner setup and testing

Pull Sprint 1, supply your own GroqCloud API key, and run ECHO with your own local databases. Keys, virtual environments, and database contents are not shared through Git. No API key is included in this repository.

## 1 Pull and prepare Python

Prerequisites: Python 3.12, Git, and Docker with the Docker engine running. On Windows, use Docker Desktop with Linux containers.

Run from your existing repository checkout:

```sh
git pull --ff-only origin main
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell equivalents for creating and activating the environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If the repository is not cloned yet, first run `git clone https://github.com/zishanmujtaba-dot/Agentika-Muj-ahmed.git` and enter its directory. The development snapshot in `requirements.lock` was resolved on macOS; the direct constraints in `requirements.txt` allow the installer to select platform-appropriate optional dependencies, including on Windows.

## 2 Add your own key locally

Copy `.env.example` to `.env` once. If you already have a `.env`, edit it instead of overwriting it.

```sh
cp .env.example .env
```

In PowerShell use `Copy-Item .env.example .env`.

Open `.env` in your editor and set:

```dotenv
GROQ_API_KEY=your_own_groqcloud_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Use a GroqCloud key, not an xAI/Grok key. Leave the database values unchanged for the supplied local Compose setup. The runtime setup command below replaces the runtime-password placeholder with a generated local password. Do not commit `.env` or paste the key into source code. `git check-ignore .env` should print `.env`.

If your shell already exports a GROQ_API_KEY, remove that shell variable or set it to your intended key: exported environment values take precedence over `.env`. Restart the backend after changing credentials. All model requests from this checkout will use the key configured in that process. `RETRIEVAL_MAX_DISTANCE` defaults to a provisional 0.60; final evaluation has not calibrated it yet.

## 3 Start and load the databases

```sh
docker compose up -d
docker compose exec -T postgres pg_isready -U postgres
docker compose exec -T neo4j cypher-shell -u neo4j -p password123 'RETURN 1 AS ready;'
```

Repeat the readiness commands if the containers are still starting. PostgreSQL should say it is accepting connections; Neo4j should return `1`. New PostgreSQL volumes automatically load `database/schema.sql`.

For an existing PostgreSQL volume, apply the schema without deleting data:

```sh
docker compose exec -T postgres psql -U postgres -d postgres < database/schema.sql
```

PowerShell equivalent:

```powershell
Get-Content database/schema.sql | docker compose exec -T postgres psql -U postgres -d postgres
```

Load the supplied demo data:

```sh
python scripts/insert_policies.py
python scripts/insert_graph.py
python scripts/configure_runtime.py
```

The first ingestion downloads an embedding model. These scripts use local embeddings, PostgreSQL, and Neo4j; they do not call Groq. `configure_runtime.py` creates restricted PostgreSQL credentials and writes them only to your local `.env`. Existing volumes must have the updated schema applied before this command. Do not run `docker compose down -v` to troubleshoot: it deletes the local database volumes.

## 4 Run and test

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If port 8000 is occupied, use `--port 8001` and change the browser URLs accordingly. Keep one backend process because staff replies currently live in its memory.

- Student voice page: http://localhost:8000/
- Staff queue: http://localhost:8000/staff
- Interactive API testing: http://localhost:8000/docs
- Liveness check: http://localhost:8000/health

The current student page is voice-only. For typed testing, open `/docs`, expand `POST /ask`, choose **Try it out**, and submit:

```json
{"query":"What is the minimum attendance requirement?","session_id":"partner-demo"}
```

This sends the question and retrieved public sample-policy context to Groq using your configured key. Inspect `answer`, `sources`, and `needs_human`. The attendance policy should be retrieved; actual generated answer quality and model availability are not yet verified.

Next submit an unrelated question such as `How do I bake a chocolate cake?`, keeping `session_id` as `partner-demo`. The local retrieval baseline produced an escalation for this question. Open `/staff` to find the ticket and send a reply. In `/docs`, use `GET /poll/{session_id}` with `partner-demo` and `since=0` to confirm the reply appears. A separate student browser page has its own generated session ID, so replies to the API-test session will not appear in that unrelated browser tab.

For a voice demo, ask through the student page in a browser supporting speech recognition, then reply to that page's ticket from `/staff`. Browser support and microphone permissions vary.

## What is verified and what to report

Local checks passed for imports/startup, public-policy retrieval, graph connectivity, ticket creation, and staff reply delivery. Model generation was stubbed in those checks. Please report the Groq model used, whether the known answer cites the correct policy, whether the unknown question escalates, and any exact error message with secrets removed.

Remaining limitations: the stricter retrieval threshold is provisional; staff endpoints are unauthenticated, session IDs are client-supplied, Neo4j still uses the configured administrative account, student input is voice-only, and live replies are lost on backend restart. Sprint 2 behavior needs final runtime verification. Keep this baseline on localhost; public deployment hardening belongs to later sprints. Sample policies are demo fixtures, not verified official university rules.
