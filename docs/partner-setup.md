# Partner setup and testing

Pull Sprint 1, supply your own GroqCloud API key, and run ECHO with your own local databases. Keys, virtual environments, and database contents are not shared through Git. No API key is included in this repository.

## Docker-only quick path

The agreed submission target is a local Docker demo. Use the [Docker runbook](docker-demo.md) to run the app and both databases without host Python or cloud services. Set your own runtime/staff passwords and optional Groq key in your local ignored .env. The host-Python workflow below remains available for development.

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

After pulling a new sprint into an existing checkout, reapply `database/schema.sql` and run `python scripts/configure_runtime.py` before restarting the backend. This creates the conversation tables, refreshes runtime grants, and generates a local staff password if missing. It does not send model requests.

```sh
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If port 8000 is occupied, use `--port 8001` and change the browser URLs accordingly.

- Student text/voice page: http://localhost:8000/
- Staff sign-in and queue: http://localhost:8000/staff
- Interactive API schema: http://localhost:8000/docs
- Liveness check: http://localhost:8000/health

Open the student page and ask `What is the minimum attendance requirement?`. This sends your question and retrieved public sample-policy context to Groq using your configured key. Then ask an unrelated question such as `How do I bake a chocolate cake?`, or explicitly ask to talk to staff.

Open `/staff` in another tab. Read `STAFF_USERNAME` and `STAFF_PASSWORD` from your own local `.env` in your editor, sign in, and reply to the resulting ticket. Staff credentials are not included in Git or prefilled in the page. A successful save resolves the ticket and adds the reply to the correct student's conversation. Refresh the student tab to check history recovery. Keep that tab's private session storage: starting a new conversation or clearing browser storage discards the browser's access token for the previous conversation.

For a voice demo, click Start voice, speak, and click Stop and send. Text input always remains available. Speech recognition and synthesis depend on browser support and permissions; speech recognition may use the browser vendor's service. Audio output is opt-in.

## API access changes in Sprint 3

Clients must first call `POST /sessions` and retain `session_id` and `session_token`. Send the token as `X-Conversation-Token` on `POST /ask` and `GET /poll/{session_id}`. Use a fresh UUID `request_id` for each new question and reuse it when retrying that same question. Responses to completed requests are replayed rather than invoking the model again. Processing requests return 409 with Retry-After; a reservation interrupted by a crash can be reclaimed after 120 seconds.

Polling uses a durable message-ID cursor, not a message count: send `since=0` for history, then the returned `cursor`; fetch another batch while `has_more` is true. Staff endpoints require HTTP Basic credentials. Staff replies only accept `text`; the backend determines the target conversation from the ticket. Legacy tickets predating private conversations cannot be delivered to a new tab and are marked accordingly.

## Verification status

Sprint 1 local checks passed for startup, retrieval, graph connectivity, ticket creation, and in-memory reply delivery with model output stubbed. Sprint 2 and Sprint 3 runtime/model/browser checks are deferred to final testing. No live Groq answer-quality result has been verified. Please report the Groq model used, known-question citations, unknown-question escalation, correct-session staff reply, and any error with secrets removed.

Keep a single backend process for the initial demo. PostgreSQL now stores conversations, messages, ticket replies, and completed request results; staff sign-in failure throttling is still per process. Neo4j still uses the configured graph credentials, the relevance threshold is provisional, there is one shared staff identity, and no production retention policy has been implemented. Use HTTPS before sending staff credentials outside localhost. The supplied policies remain demo fixtures.
