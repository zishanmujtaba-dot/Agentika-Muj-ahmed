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

## Reply context and interface update

Staff replies now quote the complete original question, with a ticket lookup fallback for replies saved before this update. Student timestamps no longer require ticket-number tracking. New regression coverage verifies that a reply references its original question even when newer questions exist, and that older metadata recovers the question from the ticket. Twelve integration tests passed with Groq disabled. The student and staff screens were visually reviewed in a separate preview, and the quoted-question handoff was exercised there without model calls.

## Expanded rulebook update

Expanded the fictional demo dataset from five to 41 public policies, retaining one protected fixture. Added department routing for every policy and related-policy links. The readable public reference is `docs/reference/student-rulebook.md`; demo prompts and expected paths are in `docs/demo-questions.md`. Memory architecture and the decision to keep current model calls standalone are documented in `docs/reference/conversation-memory.md`. No LangChain/LangGraph dependency or conversational model buffer was added.

Offline ingestion completed against the local Docker databases without deleting conversation volumes. All 46 labelled retrieval checks passed; all 12 integration tests passed with Groq disabled/stubbed. Updated the fixture count assertion and forced-empty category fallback test so they do not rely on the original five-policy corpus. These results do not establish live model answer accuracy; review the live answers with the intended demo key. No Groq calls were made for these checks.

## One-prompt memory and live voice update

Added one completed previous student prompt to the authenticated model context and referential retrieval hints, without a second provider call. Added optional live voice mode with two-second silence sending, final-result draining, speech-triggered audio cancellation, continuous listening through fresh utterance recognizers, ordered follow-up requests, and end-call/error cleanup. Plain one-shot dictation remains available.

All 13 backend integration tests passed with Groq disabled/stubbed. Eighteen JavaScript tests cover existing dictation, live-call state transitions, silence, interruption notification, request serialization, late events, errors, and simulated student-page wiring including first-answer speech. No paid provider calls were made. Physical microphone, speaker echo and browser/OS simultaneous speech behavior require the manual checks in `docs/live-voice.md`. Database volumes and runtime secrets were preserved.

## LangSmith integration

Added the standalone LangSmith SDK with default-enabled tracing when a key is present. The ECHO root span nests intent, retrieval, graph, Groq, validation and human-handoff stages. Payloads are aggregate-only and exception text is excluded. A key was subsequently supplied and saved only in the ignored owner-only .env. A synthetic aggregate-only upload to the US endpoint returned 403 Forbidden; that initial attempt was unverified until explicit organization/workspace scope resolved authorization, as recorded below. Added optional workspace/organization scope configuration.

All 20 Python tests passed (13 helpdesk integration tests and seven LangSmith tests), including explicit workspace/organization scope configuration. SDK tests exercise real nested run trees with mocked create/update transport, verifying parentage, redaction, default/key gating and fail-open behavior. Tests and the retrieval evaluator explicitly disable external tracing. pip check passed. No Groq calls were made. Offline tests make no LangSmith uploads; the subsequent synthetic connectivity attempt was rejected by LangSmith. The local Docker app was rebuilt; no cloud deployment or GitHub push was initiated during the provider outage.

### Live LangSmith verification

Configured the supplied service key with the organization ID observed in the authenticated UI and the Workspace 1 ID returned by LangSmith's documented workspace-list API. Both IDs are stored only in local .env. Scoped US API requests now return 200. Readback confirmed completed `ECHO tracing verification`, `ECHO question` and `Human handoff` spans in `echo-helpdesk`, project `ba961747-4276-450e-b4e4-ef89864adab0`. Immediate readback briefly returned not-found before the stored runs became queryable. The synthetic test patched only ticket storage: no Groq requests or student tickets were created. Tracing remains enabled.
