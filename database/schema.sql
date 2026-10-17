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


-- ---------------------------------------------------------------------------
-- OPTIONAL but recommended: a read-only role for the chatbot backend.
-- Run this block manually, once, in psql (replace the password). The backend
-- (.env PG_READONLY_USER / PG_READONLY_PASSWORD) can then use this role instead
-- of the admin postgres user, so it is PHYSICALLY unable to write to the table
-- even if something upstream went wrong - not just "shouldn't", but "can't".
-- ---------------------------------------------------------------------------
-- CREATE ROLE echo_readonly WITH LOGIN PASSWORD 'change_me';
-- GRANT CONNECT ON DATABASE postgres TO echo_readonly;
-- GRANT USAGE ON SCHEMA public TO echo_readonly;
-- GRANT SELECT ON policies TO echo_readonly;
--
-- -- This role can log and manage tickets but STILL cannot touch the rulebook - no
-- -- INSERT, UPDATE or DELETE on `policies` at all, ever, under any grant.
-- GRANT SELECT, INSERT, UPDATE ON escalations TO echo_readonly;
-- GRANT USAGE, SELECT ON SEQUENCE escalations_id_seq TO echo_readonly;
