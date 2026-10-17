-- ECHO rulebook schema. This table is written to ONLY by insert_policies.py.
-- The live chatbot backend (rag_pipeline.py / backend.py) only ever SELECTs from it.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policies (
    source_id     TEXT PRIMARY KEY,
    category      TEXT,
    title         TEXT,
    text          TEXT NOT NULL,
    access_level  TEXT NOT NULL DEFAULT 'public' CHECK (access_level IN ('public', 'protected')),
    tags          TEXT[],
    embedding     VECTOR(384)
);

CREATE INDEX IF NOT EXISTS policies_embedding_idx
    ON policies USING hnsw (embedding vector_cosine_ops);


-- ---------------------------------------------------------------------------
-- ESCALATIONS: not the rulebook. This is a ticket queue for things the agent
-- could not confidently answer or that require an actual change a human must
-- make. The agent is allowed to INSERT here (logging a request) but this is
-- NOT the same as editing real data - the policies/graph tables stay fully
-- read-only to the agent. A human reads this table (or a dashboard built on
-- top of it) and acts on it themselves, through insert_policies.py or direct
-- DB access - never through the agent.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS escalations (
    id             SERIAL PRIMARY KEY,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_id     TEXT,              -- which student's open chat this came from, so a staff
                                       -- reply can be routed back to the right browser tab
    student_query  TEXT NOT NULL,
    reason         TEXT,              -- e.g. 'no_confident_match', 'protected_policy', 'data_change_requested'
    department     TEXT,              -- routed department name, from Neo4j Policy-[:ESCALATES_TO]->Department
    status         TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'resolved'))
);


-- Student runtime reads this view, never the base policies table. Applying this
-- schema is an administrator/ingestion operation, not a server startup action.
CREATE OR REPLACE VIEW public_policies WITH (security_barrier = true) AS
    SELECT source_id, category, title, text, tags, embedding
    FROM policies WHERE access_level = 'public';

-- After applying this schema, run python scripts/configure_runtime.py offline
-- to create a dedicated login that reads public_policies and manages tickets.
-- It receives no direct access to policies and cannot edit the rulebook.


-- Sprint 3: tokens are stored as hashes; messages and request responses survive restarts.
CREATE TABLE IF NOT EXISTS conversations (
    session_id TEXT PRIMARY KEY,
    token_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_requests (
    session_id TEXT NOT NULL REFERENCES conversations(session_id),
    request_id TEXT NOT NULL,
    query TEXT NOT NULL,
    claim TEXT NOT NULL,
    response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, request_id)
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES conversations(session_id),
    sender TEXT NOT NULL CHECK (sender IN ('student', 'agent', 'staff')),
    text TEXT NOT NULL,
    request_id TEXT,
    escalation_id INTEGER REFERENCES escalations(id),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conversation_message_cursor_idx
    ON conversation_messages(session_id, id);
CREATE UNIQUE INDEX IF NOT EXISTS conversation_message_request_idx
    ON conversation_messages(session_id, request_id, sender) WHERE request_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS one_staff_reply_per_ticket_idx
    ON conversation_messages(escalation_id) WHERE sender = 'staff';
