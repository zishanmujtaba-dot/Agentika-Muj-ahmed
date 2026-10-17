"""Existing ECHO retrieval and answer pipeline, reused for the demo.

PostgreSQL/pgvector retrieves public policy text; Neo4j provides relationship
metadata and department routing. Runtime writes are limited by the current code
to escalation tickets, but database enforcement requires restricted credentials.
Policy and graph ingestion remain separate offline scripts in scripts/.
"""
import os
from pathlib import Path
import json
import psycopg2
from psycopg2 import pool as pg_pool
from contextlib import contextmanager
from groq import Groq
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

client_groq = Groq(api_key=os.environ["GROQ_API_KEY"])
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7689")
NEO4J_AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password123"))
DEFAULT_ESCALATION_DEPARTMENT = "Registrar's Office"  # fallback when no policy matched at all

DB_CONFIG = dict(
    host=os.environ.get("PG_HOST", "localhost"),
    port=int(os.environ.get("PG_PORT", 5434)),
    dbname=os.environ.get("PG_DBNAME", "postgres"),
    # Point this at the echo_readonly role from schema.sql once it exists. Falls back to the
    # admin credentials for now so the project runs out of the box before that role is set up -
    # swap PG_READONLY_USER/PASSWORD in .env as soon as you've created the role.
    user=os.environ.get("PG_READONLY_USER", "postgres"),
    password=os.environ.get("PG_READONLY_PASSWORD", "postgres"),
)
TABLE_NAME = "policies"
DISTANCE_THRESHOLD = 0.8   # above this cosine distance, treat it as "nothing relevant found"
TOP_K = 5

LLM_FAILURE_MARKER = "[[LLM_CALL_FAILED]]"

_embed_model = None
_pg_pool = None
_neo4j_driver = None


def init_pipeline():
    """Call once at process startup (FastAPI's startup event does this) - loads the embedding
    model, opens a Postgres connection POOL (not a single connection - see db_connection()
    below for why), and opens the Neo4j driver, all a single time instead of per-request."""
    global _embed_model, _pg_pool, _neo4j_driver
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    if _pg_pool is None:
        # minconn=1, maxconn=10: 10 concurrent students/staff is plenty for a hackathon demo -
        # raise maxconn if you're load-testing with more simulated users than that.
        _pg_pool = pg_pool.ThreadedConnectionPool(1, 10, **DB_CONFIG)
    if _neo4j_driver is None:
        _neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    return _embed_model, _pg_pool, _neo4j_driver


@contextmanager
def db_connection():
    """Borrows one connection from the pool for the duration of a single request, then returns
    it. This is the fix for concurrent users: FastAPI runs sync routes like /ask on a thread
    pool, so two students asking questions at the same moment means two threads touching
    Postgres at once. A single shared connection isn't safe for that - interleaved queries on
    one connection can return the wrong results to the wrong request. Each request now gets
    its own connection from the pool instead."""
    _, pool_, _ = init_pipeline()
    conn = pool_.getconn()
    try:
        yield conn
    finally:
        pool_.putconn(conn)


def call_llm(prompt, max_tokens=1024):
    try:
        resp = client_groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"{LLM_FAILURE_MARKER}{e}"


def is_llm_failure(text):
    return isinstance(text, str) and text.startswith(LLM_FAILURE_MARKER)


def parse_query_intent(query):
    """Deliberately simple for the timeline. A category hint narrows the search when the LLM
    can confidently tell what kind of policy this is about; semantic_query always falls back to
    the raw question, so retrieval still works even if this parsing step is wrong."""
    prompt = f"""Classify this question about a university's policies. Respond ONLY with valid JSON.

Question: "{query}"

Output format:
{{"category": null, "semantic_query": ""}}

Rules:
- Set "category" to ONE of: "fees", "registration", "courses", "attendance", "general" - only
  if the question is clearly about that category. Otherwise leave it null.
- Set "semantic_query" to the question rewritten as a short, clear search phrase capturing what
  it's actually asking.
"""
    raw = call_llm(prompt, max_tokens=200)
    if is_llm_failure(raw):
        return {"category": None, "semantic_query": query}
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        intent = json.loads(raw.strip())
        return {
            "category": intent.get("category"),
            "semantic_query": intent.get("semantic_query") or query,
        }
    except Exception:
        return {"category": None, "semantic_query": query}


def retrieve_policies(intent):
    """The ONLY function that talks to the database during question-answering. Always
    restricted to access_level = 'public' - this is the extension point for real access
    control later (e.g. passing in an authorized-caller flag), not somewhere else."""
    embed_model, _, _ = init_pipeline()
    vector = embed_model.encode([intent["semantic_query"]], convert_to_numpy=True)[0]
    vector_str = "[" + ",".join(map(str, vector.tolist())) + "]"

    conditions = ["access_level = 'public'"]
    params = [vector_str]
    if intent.get("category"):
        conditions.append("category = %s")
        params.append(intent["category"])

    where_clause = "WHERE " + " AND ".join(conditions)
    params.append(vector_str)
    params.append(TOP_K)

    sql = f"""
        SELECT source_id, category, title, text, embedding <=> %s AS distance
        FROM {TABLE_NAME}
        {where_clause}
        ORDER BY embedding <=> %s
        LIMIT %s;
    """
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()

    return [
        {"source_id": r[0], "category": r[1], "title": r[2], "text": r[3], "distance": r[4]}
        for r in rows
    ]


def graph_lookup(policy_source_ids):
    """Read-only Neo4j lookup. For the policies pgvector already found, pulls (a) any other
    policies related to them, and (b) which department each escalates to. This is expansion
    on top of vector search, not a replacement for it - pgvector finds the match, Neo4j adds
    context vector search can't represent (relationships, routing)."""
    if not policy_source_ids:
        return {"related_policies": [], "department": None}

    _, _, driver = init_pipeline()
    with driver.session() as session:
        related = session.run(
            """
            MATCH (p:Policy)-[:RELATED_TO]->(related:Policy)
            WHERE p.source_id IN $ids
            RETURN DISTINCT related.source_id AS source_id
            """,
            ids=policy_source_ids,
        )
        related_ids = [r["source_id"] for r in related]

        dept = session.run(
            """
            MATCH (p:Policy)-[:ESCALATES_TO]->(d:Department)
            WHERE p.source_id IN $ids
            RETURN d.name AS department
            LIMIT 1
            """,
            ids=policy_source_ids,
        ).single()
        department = dept["department"] if dept else None

    return {"related_policies": related_ids, "department": department}


def create_escalation(student_query, reason, department, session_id=None):
    """The ONLY function in the project that writes anything triggered by a live question -
    and it writes exclusively to `escalations`, a ticket queue, never to `policies` or any
    graph node. This is what "forwarding to a human" actually means here: a routed ticket a
    staff member reviews and acts on themselves - the agent cannot make the change itself.

    session_id (if provided) is what lets a staff member's reply find its way back to this
    specific student's open browser tab, via the in-memory poll queue in backend.py."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO escalations (session_id, student_query, reason, department)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (session_id, student_query, reason, department or DEFAULT_ESCALATION_DEPARTMENT),
        )
        escalation_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
    return escalation_id


def get_pending_escalations():
    """Read-only - lists open tickets for staff to review. Does not change anything."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, created_at, session_id, student_query, reason, department, status
               FROM escalations WHERE status = 'pending' ORDER BY created_at DESC;"""
        )
        rows = cur.fetchall()
        cur.close()
    return [
        {
            "id": r[0], "created_at": r[1].isoformat(), "session_id": r[2],
            "student_query": r[3], "reason": r[4], "department": r[5], "status": r[6],
        }
        for r in rows
    ]


def resolve_escalation(escalation_id):
    """Marks a ticket resolved once a staff member has replied. Still only touches
    `escalations`, never the rulebook or graph data."""
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE escalations SET status = 'resolved' WHERE id = %s;", (escalation_id,))
        conn.commit()
        cur.close()


def build_prompt(query, policies):
    if not policies:
        context = "(No matching policies were found in the rulebook.)"
    else:
        context = "\n\n".join(
            f"[Policy: {p['title']} | Category: {p['category']}]\n{p['text']}"
            for p in policies
        )

    return f"""You are ECHO, a university helpdesk assistant for FAST NUCES. Answer the
student's question using ONLY the policy text given below. Do not use outside knowledge and
do not guess.

Rules:
- If the policies below fully answer the question, answer clearly and cite the policy title(s)
  you used.
- If the policies below are only partially relevant, or not relevant at all, say so plainly
  and do NOT make up an answer. Tell the student you don't have a confident answer and offer to
  connect them with a human staff member.
- Keep the answer short and conversational - this may be read aloud by text-to-speech.

Retrieved policies:
{context}

Student's question: "{query}"

Answer:"""


def answer_query(query, session_id=None):
    """Main entrypoint - call this from the API layer. Returns the answer plus a needs_human
    flag and routed department so the frontend can show a human-in-the-loop handoff when
    confidence is low or the matched policy is something the agent can't resolve alone.

    When needs_human is true, this function ALSO writes an escalation ticket tagged with
    session_id, so a staff member's reply (sent via the staff page) can be delivered back into
    this exact student's open chat through the poll queue in backend.py. The agent still never
    edits policies/teachers/courses itself - it only ever logs a routed request for a person to
    act on."""
    intent = parse_query_intent(query)
    policies = retrieve_policies(intent)

    confident_matches = [p for p in policies if p["distance"] <= DISTANCE_THRESHOLD]
    needs_human = len(confident_matches) == 0

    graph_info = {"related_policies": [], "department": None}
    if confident_matches:
        graph_info = graph_lookup([p["source_id"] for p in confident_matches])

    prompt = build_prompt(query, confident_matches)
    raw_answer = call_llm(prompt, max_tokens=400)

    if is_llm_failure(raw_answer):
        create_escalation(query, reason="llm_call_failed",
                           department=graph_info["department"], session_id=session_id)
        return {
            "answer": "Sorry, I'm having trouble reaching the AI service right now. I've "
                      "flagged this for a staff member to follow up.",
            "needs_human": True,
            "department": graph_info["department"] or DEFAULT_ESCALATION_DEPARTMENT,
            "sources": [],
        }

    if needs_human:
        create_escalation(query, reason="no_confident_match",
                           department=graph_info["department"], session_id=session_id)

    return {
        "answer": raw_answer.strip(),
        "needs_human": needs_human,
        "department": graph_info["department"] if needs_human else None,
        "sources": [p["title"] for p in confident_matches],
        "related_policies": graph_info["related_policies"],
    }
