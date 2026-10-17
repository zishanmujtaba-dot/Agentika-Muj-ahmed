# Final verification

Submission target: local Docker demo, confirmed by the user. No public deployment or managed cloud database service is required.

## Passed

- Built a Linux CPU-only Docker image with cached embeddings, non-root execution, and no .env in the build context.
- Started the app, PostgreSQL/pgvector, and Neo4j together with healthy container status. The app serves on host port 8001 and container port 3000.
- Ran Docker-only bootstrap successfully: shared schema, six sample policies, organizational graph, restricted PostgreSQL role. Repeated ingestion preserved stable IDs.
- Eleven integration tests passed both in the host development environment and inside the final Linux Docker image, with real PostgreSQL/Neo4j and stubbed model responses: known question and paraphrase, category fallback, unknown-question escalation, simultaneous/repeated request deduplication, staff access control, private conversation tokens, input limits, cross-origin rejection, reply routing/isolation, reply retry, polling cursors, pooled reconnection, protected source exclusion, provider/refusal/citation failures, graph outage, honest storage failure, runtime policy permissions, pages/assets, and readiness.
- Ten local retrieval fixtures passed at maximum cosine distance 0.60: seven known/paraphrased questions across all five sample categories and three unrelated questions. Known best distances were 0.1674–0.4102; unrelated questions were 0.9425–0.9721. This is a small demo fixture, not a broad accuracy benchmark.
- Real browser flow passed: typed human request → ticket in authenticated staff queue → reply saved → reply displayed in the correct student conversation.
- The original student tab retained its history and staff reply after the host backend was stopped and replaced by the Docker backend, then the page was refreshed. This verifies storage across an actual process/container transition, beyond reconnecting a test client.
- Desktop layout was visually inspected. Speech remains optional. A viewport override did not change the browser's actual width, so a real mobile device check is not claimed.

## Deliberately not claimed

- No live Groq calls were made. Provider-key validity, current model availability, generated-answer quality, and live model latency remain for the partner to verify using their own key. Integration fixtures validate the application around the model boundary, not the model itself.
- Microphone capture and audible speech playback were not exercised; they require browser/device permission and support. Typed chat was exercised in the real browser.
- Neo4j uses the configured graph account; client READ mode is not server-side privilege isolation. PostgreSQL public-policy isolation was checked with restricted runtime credentials.
- This is a demo with one shared staff identity, a per-process login-failure limiter, and no production retention/identity-management policy.
- No external hackathon submission was performed; no submission portal or required fields were supplied. The repository and Docker runbook are the deliverables.

## Repeat without spending model credits

With the optional host Python development environment configured:

```sh
python -m unittest discover -s tests -v
python scripts/evaluate_retrieval.py
```

Both commands force Groq off in their own process. The integration suite deletes only records it creates. The retrieval check performs no writes. Do not run the integration suite against production databases; use this local demo setup.

For the browser demo without model usage, leave GROQ_API_KEY blank. Explicit human requests go directly to staff. A policy answer with no provider key becomes an escalation, not a fabricated AI answer.
