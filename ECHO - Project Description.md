# ECHO: Evaluated Conversational Helpdesk Orchestrator

Hackathon build — Workflow Automation / Agentika, human-in-the-loop theme

## 1. Overview

ECHO is an AI-powered helpdesk for FAST NUCES that answers student questions about university policy — fee deadlines, registration rules, attendance requirements, course withdrawal, and similar topics — through a chat and voice interface. It answers only from a defined rulebook using retrieval-augmented generation (RAG), never from the model's general knowledge, and it hands off to a real staff member whenever it isn't confident or the information is restricted. A graph database models the university's actual structure (departments, teachers, courses, semesters) so the system can route escalations to the right person and reason about relationships a plain text search can't capture.

The project was scoped down from a full semester-length capstone proposal into a buildable two-day hackathon version: one retrieval backend (not several model configurations), no custom evaluation dashboard yet, and voice handled entirely in the browser rather than through dedicated speech infrastructure.

## 2. Motivation

University helpdesks are inconsistent by nature — different staff give different answers to the same question, phone lines get busy, and there's no record of whether an answer given was actually correct. ECHO addresses this by grounding every answer in an approved, versioned rulebook, by making every low-confidence or restricted answer escalate to an actual person rather than let the model guess, and by keeping a clear structural line between "the agent can look things up" and "the agent can change the record" — the agent never has write access to the rulebook or university data, only to a ticket queue a human reviews.

## 3. Objectives

- Answer student questions from a defined policy rulebook using RAG, never from unconstrained generation

- Support both a text chat and a voice interface (speech-to-text in, text-to-speech out)

- Enforce access control so some information (e.g. disciplinary records) is never retrievable by the agent at all

- Guarantee the agent is read-only against the data of record — all writes happen through a separate, offline, human-run ingestion process

- Route anything the agent can't confidently answer to the right department, with a real person able to reply directly into the student's live chat

- Model the university's actual organizational structure (departments, teachers, courses, semesters) so routing and relationship queries are possible, not just keyword search

## 4. System Architecture

### 4.1 High-level flow

Two independent paths touch the same database:

Path A — loading the rulebook (offline, run manually by the team). Policy text and university organizational data are written to JSON files, then loaded into Postgres (with the pgvector extension) and Neo4j by two standalone scripts. This is the only path in the entire system that ever writes to the data of record.

Path B — answering a question (runtime, every time a student asks something). A question arrives as text (typed, or transcribed from voice in the browser). The backend parses intent, searches Postgres for the closest-matching public policies, optionally expands that result through Neo4j for related policies and department routing, and sends only the retrieved text to an LLM (via Groq) to generate a grounded answer. If no confident match is found, or the match is a protected/restricted policy, the agent does not guess — it creates an escalation ticket instead and tells the student it's being handed to a person.

### 4.2 Data ingestion (offline, write path)

insert_policies.py reads sample_policies.json (each entry: id, category, title, full policy text, access level, tags), generates a 384-dimensional embedding for each policy using a local sentence-transformer model (all-MiniLM-L6-v2, no API call needed), and upserts the rows into a Postgres table indexed with HNSW for fast approximate nearest-neighbor search. Policies are not chunked — each one is short and self-contained, so the whole policy is the retrieval unit.

insert_graph.py reads sample_org.json and populates Neo4j with the university's structure: departments, teachers, courses, semesters, who teaches what, who belongs to which department, and — critically — which department each policy escalates to if a student's question about it needs a human.

Both scripts are safe to re-run; they upsert by ID rather than wiping data, so editing the rulebook is just editing the JSON and re-running the script.

### 4.3 Retrieval + answer generation (runtime, read-only path)

rag_pipeline.py is the only code that answers questions, and every database call inside it is a plain, parameterized SELECT — never LLM-generated SQL, and never a write to policy or organizational data. The flow for a single question:

- Intent parsing — a lightweight LLM call turns the raw question into a structured intent: an optional category hint (fees, registration, courses, attendance, general) and a cleaned-up semantic search phrase.

- Vector search — the question is embedded and compared against policy embeddings in Postgres using cosine distance, filtered to access_level = 'public' and, if present, the category hint. Top 5 candidates are returned.

- Confidence check — any result above a distance threshold is discarded as "not actually relevant." If nothing confident remains, the question is flagged needs_human.

- Graph expansion — for confident matches, Neo4j is queried (read-only) for any related policies and the department that policy escalates to.

- Answer generation — the retrieved policy text (and only that text) is handed to the LLM with an instruction to answer strictly from it, cite the policy title, and explicitly say "I don't have a confident answer" rather than fabricate one if the context doesn't support an answer.

- Escalation (if needed) — if the question was unanswerable, or the LLM call itself failed, a ticket is written to a separate escalations table, tagged with the routed department and the student's session ID.

### 4.4 Access control

Every policy is tagged public or protected. Protected policies are excluded at the SQL query level — they are never returned to the application layer, never seen by the LLM, and never appear in an answer. This is currently a simple binary flag (the sample data marks disciplinary records as protected); the rules for who, if anyone, can unlock protected content are intentionally left as a future design decision, scaffolded but not yet implemented.

### 4.5 Human-in-the-loop escalation

This is the project's core theme, and it's enforced structurally, not just by convention:

- The agent's only write permission against the database is INSERT/UPDATE on the escalations table — a ticket queue, not the rulebook. It has no permission to touch policies, Teacher, Course, or any graph node, under any code path.

- When an answer can't be given confidently, a ticket is created automatically, including the original question, the reason, and the department it was routed to (pulled from the Neo4j Policy → ESCALATES_TO → Department relationship, falling back to a default department if no policy matched at all).

- A staff-facing page (staff.html) polls for pending tickets and lets a real person type a reply.

- That reply is delivered back into the exact student's open chat within a few seconds via a lightweight polling mechanism keyed by a per-session ID generated when the student's page loads — no telephony or WebRTC infrastructure required, and no live "someone must be watching" requirement for the escalation ticket itself to work (only the live-reply feature needs a staff member actively present).

- If a student's issue actually requires a real data change (correcting a record, granting an exception), the staff member makes that change themselves, outside the agent entirely, through insert_policies.py or direct database access. The agent cannot and does not perform that write.

### 4.6 Voice interface

Speech-to-text and text-to-speech both run entirely in the browser using the Web Speech API — no server-side audio processing, no dedicated STT/TTS infrastructure, and no API costs for voice. The interaction model is click-to-talk rather than hold-to-talk or fully automatic voice-activity detection: the student clicks once to start listening (with live interim transcription shown so they can see it's working), and clicks again to finalize and send. This was chosen over a hold-to-talk pattern after testing showed physically holding a button down while speaking is unreliable, especially on trackpads.

### 4.7 Concurrency & infrastructure

The backend (FastAPI) handles each request on its own thread. Postgres access goes through a connection pool (up to 10 concurrent connections) rather than a single shared connection, so multiple students asking questions at the same moment don't interfere with each other's queries. The Neo4j driver and the Groq API client are both naturally safe for concurrent use without extra work. The one deliberately simple piece is the live staff-reply queue, which is held in memory on the single backend process — correct and sufficient for a demo-scale deployment, but not designed to survive a server restart or to work across multiple backend instances; that would require moving session state into a shared store like Redis, which was out of scope for the timeline.

## 5. Database design

Postgres — policies table

| Field | Purpose |
| --- | --- |
| source_id | Unique identifier |
| category | fees / registration / courses / attendance / general — hard filter before vector search |
| title | Shown in citations |
| text | Full policy text, not chunked |
| access_level | public / protected |
| tags | Reserved for future filtering |
| embedding | 384-dim vector, HNSW-indexed |

Postgres — escalations table

| Field | Purpose |
| --- | --- |
| id, created_at | Ticket identity and timestamp |
| session_id | Routes a staff reply back to the right open chat |
| student_query | The original question |
| reason | no_confident_match / llm_call_failed / etc. |
| department | Routed department, from the graph |
| status | pending / resolved |

Neo4j graph

Nodes: Department, Teacher, Course, Semester, Policy, StaffContact.

Relationships: (Teacher)-[:BELONGS_TO]->(Department), (Teacher)-[:TEACHES]->(Course), (Course)-[:BELONGS_TO]->(Department), (Course)-[:OFFERED_IN]->(Semester), (Policy)-[:RELATED_TO]->(Policy), (Policy)-[:ESCALATES_TO]->(Department), (Department)-[:HAS_CONTACT]->(StaffContact).

Policy nodes in the graph are lightweight (just an ID), used only to attach relationships — the actual policy text and access level live in Postgres as the single source of truth, so the two databases never hold conflicting copies of the same content.

## 6. Tech stack

- Backend: Python, FastAPI

- Vector search: PostgreSQL + pgvector, HNSW index

- Graph database: Neo4j

- Embeddings: sentence-transformers (all-MiniLM-L6-v2), run locally, no API cost

- LLM: Groq-hosted model, used for intent parsing and answer generation

- Frontend: Plain HTML/JS, Web Speech API for STT/TTS, no framework

- Infrastructure: Docker Compose (Postgres + Neo4j), deployed to Alternate Clouds via GitHub integration

## 7. Deployment

The project is connected to GitHub and deploys to Alternate Clouds on push to main. Local development uses Docker Compose to run both databases on fixed ports matching the application's configuration, so the same .env-driven setup works identically on any team member's machine.

## 8. Current status — what's built

- End-to-end text RAG pipeline: retrieval, grounding, citation, confidence-based fallback

- Neo4j graph populated with sample organizational data and policy routing

- Access control enforced at the query level for protected content

- Full human-in-the-loop escalation: automatic ticket creation, department routing, live staff reply delivered back into the student's chat

- Voice input and output via the Web Speech API

- Connection pooling for safe multi-user concurrent access

- Local Docker-based database setup and a cloud deployment pipeline

## 9. Remaining work

- Replace sample rulebook and organizational data with FAST NUCES' actual policies and structure

- Build the evaluation engine (scoring answers for groundedness and resolution) described in the original project proposal — not yet implemented

- Build an administrator dashboard summarizing conversations and complaint trends — not yet implemented

- Define the actual rules for protected-content access (currently a simple always-excluded flag)

- Move the live staff-reply queue from in-memory storage to a persistent store if the system needs to survive restarts or scale beyond one backend process

## 10. Team

- Mujtaba Zishan — Developer

- Musawar Ahmed Khan — AI / Agent Engineer
