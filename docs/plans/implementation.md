# ECHO Three Hour Submission Plan

Deliver a working demo of the existing ECHO helpdesk within **180 minutes**, using **four implementation sprints total**. Prioritize a complete student question → grounded answer or escalation → staff reply flow. Reuse the current code and deployment rather than redesigning the application.

## Starting point and success criteria

The companion `../reference/project-description.md` preserves the supplied DOCX content. Its descriptions of completed features are claims to verify, not confirmation of what currently works. Application code has not yet been reviewed for this plan.

A successful submission demonstrates:

- A student asks a policy question and receives an answer citing a supplied public policy.
- An unsupported question creates a ticket with department routing or a documented default.
- Staff can reply and the reply reaches the correct student's chat.
- Protected policy text is excluded from retrieval and model context.
- A reviewer can open the deployed application or use the submission's documented fallback and run the demo.

Use labeled sample policies if official material is not immediately available. Do not present sample data as verified FAST NUCES policy. Keep PostgreSQL/pgvector, Neo4j, Groq, FastAPI, and the existing HTML/JavaScript unless a concrete blocker requires a small fallback.

## Sprint 1 — Verify the baseline and lock the demo path

**Minutes 0–20. Hard stop at minute 20.**

Inspect the current code, configuration, and startup instructions once. Start the existing application and databases and identify which parts of the demo already work. Check required secrets and the actual Alternate Clouds deployment state, including GitHub App access to the repository.

Run a quick baseline: one known policy question, one unknown question, and one staff reply. Check whether protected filtering exists and whether any credentials are exposed. Choose one canonical student page and one staff page if duplicate frontends exist.

Record a short blocker list and the exact commands needed to start the app. Fix only trivial startup issues during this sprint. Preserve working code and data; do not introduce a framework, broad refactor, or new service.

**Done when:** The team knows the working path, missing configuration, deployment status, and the smallest fixes required. If something cannot start, its blocker is explicit and receives priority in Sprint 2.

## Sprint 2 — Make the backend demo reliable

**Minutes 20–80. Hard stop at minute 80.**

Fix startup and dependency blockers first. Ensure a repeatable way to load the existing sample policies and graph data, avoiding duplicate records on reruns. Reuse existing schema and ingestion scripts; add only fields or setup changes needed for the demo.

Complete or repair the question flow:

- Retrieve public policies using matching ingestion/query embedding dimensions. Keep protected text out of both direct retrieval and graph-expanded context.
- If category filtering removes an otherwise useful result, retry without the category hint. Use a few known and unknown questions to choose a practical relevance threshold; do not build an evaluation engine.
- Give the model only the retrieved evidence and require policy citations. If the evidence is insufficient or generation fails, return an explicit fallback and create a ticket.
- Route through the existing graph where available. If graph routing fails, use a default department and document the limitation. Do not allow an optional graph failure to break the entire chat.
- Include the question, reason, department, status, and conversation identifier in tickets. Report ticket-storage failure honestly rather than claiming a handoff succeeded.

Check the existing runtime credentials. Use separate ingestion credentials and read-only policy/graph access if this can be configured within the time box; otherwise retain parameterized queries, remove any runtime policy/graph write path, and explicitly document that database-level privilege enforcement remains incomplete. Do not claim stronger isolation than verified.

**Done when:** A known question returns a relevant cited answer, an unknown question creates a routed ticket, and protected policy text does not enter an answer or model context.

## Sprint 3 — Complete the student and staff experience

**Minutes 80–130. Hard stop at minute 130.**

Connect the existing student and staff pages to the working backend. Show clear sending, answered, escalated, replied, and error states. Render messages as text and avoid inserting untrusted HTML.

Verify that replies reach the correct conversation and are not repeated on every poll. Use the existing session mechanism if adequate; enforce conversation access on the backend rather than trusting an arbitrary client-supplied ID. Protect staff ticket and reply endpoints with a minimal server-validated login/session or equivalent access control; never embed a shared staff secret in public JavaScript.

If reply persistence is already supported or requires only a small change, use PostgreSQL. If replacing an in-memory queue would exceed the time box, keep one backend process, document that pending live replies can be lost on restart, and demonstrate the limitation honestly. Do not add Redis.

Retain existing voice functionality if working. Give voice a maximum of ten minutes within this sprint: check microphone denial, stop/send, and text fallback. If browser recognition is unreliable, submit working text chat with voice marked as browser-dependent. Browser recognition may use the browser vendor's speech service; do not claim guaranteed offline processing.

**Done when:** Two student sessions receive only their own replies, staff endpoints require authorization, and text chat works end to end. Working voice is a bonus after this path is solid.

## Sprint 4 — Deploy, verify, and submit

**Minutes 130–180. Freeze features at minute 150. Reserve minutes 165–180 for submission.**

Deploy using the existing Alternate Clouds setup. Verify build/start commands, port binding, required secrets, database connectivity, and a public HTTPS URL. Do not assume Docker Compose is accepted unchanged or that push-to-main deployment is enabled. Keep secrets out of Git and restrict database exposure.

If the GitHub picker is blocked, ask the repository owner early to install/authorize the platform app for the original repo and connect the installation. Time-box this blocker to ten minutes within this sprint; if unresolved, use an already supported image/manual deployment route if available. Otherwise prepare a reproducible local demo and a recording, and check whether submission rules accept them. A recording is not a substitute for a required live deployment.

After the feature freeze, make only fixes that unblock startup, the core demo, or submission. Run this compact checklist rather than a full test-suite expansion:

| Check | Expected result |
| --- | --- |
| Known policy and one paraphrase | Relevant answer with a source policy citation |
| Unknown question | Clear fallback and a ticket in the staff queue |
| Protected request and prompt-injection request | No protected text or unsupported policy claim |
| Staff reply with two student sessions | Reply appears only in the intended conversation |
| Unauthenticated staff request | Ticket/reply access denied |
| Model or routing failure | Clear error or documented fallback, no false success |
| Deployed page and browser voice fallback | Text demo usable over HTTPS |

By minute 165, have the deployment URL or permitted fallback, a short demo recording if needed, exact startup/environment instructions, sample-data notice, and known limitations ready. Use the last fifteen minutes to complete the actual submission and verify its links.

**Done when:** Submission is delivered through the required channel, links open, and the core demo works on the submitted artifact. Document unpassed checks and demo limitations without claiming production readiness.

## Deferred beyond submission

Official policy collection, protected-content unlocking, custom evaluation dashboards, complaint analytics, elaborate migrations, multi-instance deployment, Redis, a frontend rewrite, extensive performance tuning, and broad automated test coverage are outside this three-hour build. Fix a concrete security or correctness blocker when encountered, but do not expand these into new feature tracks.

## Working rules

Keep the implementation at four sprints. Bundle related fixes and focused checks into the current sprint; move unfinished essentials into the remaining time instead of creating additional sprints. Keep one short progress note with sprint status, commands, blockers, and the next action so future sessions do not need to rediscover the repository.

The clock starts when implementation begins. If any of the three-hour window has already elapsed, compress the first three sprints and protect the final deployment/submission window. This document is a plan only; application implementation has not started as part of the conversion task.
