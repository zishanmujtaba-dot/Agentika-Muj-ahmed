# Docker demo runbook

The submission target is a local Docker demo. The app, PostgreSQL/pgvector, and Neo4j run together; there are no paid managed database accounts or cloud deployment steps.

## Fresh setup

From the repository root, copy `.env.example` to `.env` if no local file exists. On macOS/Linux use `cp .env.example .env`; on PowerShell use `Copy-Item .env.example .env`.

Set your own `PG_READONLY_PASSWORD` and `STAFF_PASSWORD`; placeholders deliberately fail setup. Use `PG_READONLY_USER=echo_runtime` and `STAFF_USERNAME=staff`. Set `GROQ_API_KEY` to the developer key intended for model testing, or leave it blank for a staff-only demo. Do not paste secrets into the source or commit `.env`.

```sh
docker compose up -d --wait --wait-timeout 180
docker compose --profile setup run --build --rm bootstrap
docker compose --profile app up -d --build --wait --wait-timeout 180
```

The first build is the slow step: it downloads CPU dependencies and the embedding model. Later builds reuse those layers. The setup container has ingestion/admin access; the running app has only public-policy reads and conversation/ticket permissions. Setup never calls Groq. Local database administrator defaults in Compose are for this demo only.

Open http://localhost:8001/ for students and http://localhost:8001/staff for staff. Use the staff username/password you chose in `.env`. Recognition and speech playback depend on your browser; text chat always remains available. Use the same hostname consistently: `localhost` and `127.0.0.1` have separate browser session storage.

## Two minute submission demo

1. With a valid Groq key configured, ask `What is the minimum attendance requirement?`. Check that the answer cites the attendance policy and matches the sample rulebook. This live model step must be checked with the intended developer's key before claiming generated-answer correctness.
2. Ask `I want to speak to a staff member.`. The app should create a routed ticket without calling Groq.
3. Sign in at `/staff` in another tab, type a reply, and send. The reply should arrive in the student's conversation and the ticket should leave the pending queue.
4. Refresh the student tab. The conversation should remain. Use a separate browser tab with a new conversation to show it cannot see the other student's replies.
5. Restart the app with `docker compose restart app`, wait for `/ready` to return 200, then refresh the original student tab again. Saved replies should remain.

For a zero-Groq-credit demonstration, leave the key blank and perform steps 2–5. A known policy question with no key is escalated; it is not a grounded model answer.

## Check status and troubleshoot

```sh
docker compose --profile app ps
docker compose logs --tail 80 app
docker compose logs --tail 40 postgres neo4j
```

Readiness: http://localhost:8001/ready. The response reports database readiness and whether a provider key is configured; it does not validate that key or call the provider.

- Runtime password/authentication failure: confirm `.env` values, rerun bootstrap, then recreate the app. Changing a `.env` value does not update an already running container.
- Missing table/view or role privilege: rerun bootstrap after pulling schema changes.
- Staff sign-in failure: use your current `STAFF_USERNAME` and `STAFF_PASSWORD`, then recreate the app after edits. Five failed logins trigger a one-minute per-process throttle.
- Port 8001 occupied: stop the process using it or change the host side of the app port mapping, for example `8002:3000`, and use that URL.
- Database startup timeout: inspect database logs; setup is safe to rerun by policy/graph ID. Do not delete volumes to retry.
- Lost student token: refreshing the same tab retains access, but clearing session storage or starting a new conversation loses that tab's access to its previous conversation. Staff replies remain stored in PostgreSQL.
- Unsupported browser/microphone: use text. Browser speech recognition may use the browser vendor's service.

## Update, stop, and recover

After `git pull --ff-only origin main`:

```sh
docker compose --profile setup run --build --rm bootstrap
docker compose --profile app up -d --build --wait --wait-timeout 180
```

To stop without losing data:

```sh
docker compose --profile app stop
```

To remove containers while retaining volumes:

```sh
docker compose --profile app down
```

Do not add `-v`: it deletes the databases. Return to the previous Git commit if a code update is broken, rebuild its app image, and retain current volumes. Avoid schema/data changes during the final demo; this project has no automated migration rollback. For a simple pre-demo PostgreSQL backup, `docker compose exec -T postgres pg_dump -U postgres -d postgres > echo-backup.sql`; keep backups private and outside Git.

## Later public hosting

The optional Alternate Clouds project is connected to the repository but has not been deployed. A public host would need the same app plus reachable, persistent PostgreSQL and Neo4j containers. The app's Dockerfile binds `${PORT:-3000}` and runs as a non-root user. Do not point a cloud app at `localhost` databases on a laptop or upload personal keys without deciding who owns the deployment. Public hosting is outside the agreed local-demo submission scope.

## Expanded reference and questions

See [student rulebook](reference/student-rulebook.md) and [demo questions](demo-questions.md). These are fictional demo policies. After pulling updated seed files, rerun the bootstrap and rebuild the app using the setup commands above. Existing database volumes and conversations are retained. No Groq calls are made during ingestion.

Run the local retrieval checks without paid model usage:

```sh
docker compose --profile app exec -T app python scripts/evaluate_retrieval.py
```

This validates policy selection only. Check live answer quality and model-stage handoffs separately with the configured key.
