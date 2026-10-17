"""ECHO HTTP API and same-origin student/staff pages.

Run from repository root: uvicorn app.main:app --reload --port 8000
Offline ingestion and PostgreSQL role setup live in scripts/. Retrieval reads
the public-only view; configure_runtime.py grants only that view. Ticket creation and
resolution write to the separate escalations table. Live replies are currently
in memory; staff authentication is pending Sprint 3.
"""
from collections import defaultdict
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from . import rag_pipeline

app = FastAPI(title="ECHO backend")

# In-memory, per-session message queue for the live staff handoff. This is NOT the database -
# it's ephemeral chat state, cleared on restart, and holds no rulebook data at all. Writing to
# it is not "editing the database"; it's just passing a message from the staff page to the
# right student's open browser tab. For a hackathon-scale demo (one process, a handful of
# concurrent chats) this is enough; a real deployment would use Redis or a proper pub/sub
# instead so it works across multiple backend processes.
SESSION_MESSAGES = defaultdict(list)

# Wide open for hackathon development - voice_chat.html is opened from a file:// path or a
# different localhost port, so the browser needs CORS allowed. Tighten this before anything
# resembling a real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(min_length=1, max_length=128)


class StaffReplyRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=6000)


@app.on_event("startup")
def startup():
    # Loads the embedding model and opens the DB connection ONCE at process start, not per
    # request - this is what keeps response latency reasonable.
    rag_pipeline.init_pipeline()


@app.on_event("shutdown")
def shutdown():
    rag_pipeline.close_pipeline()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest):
    result = rag_pipeline.answer_query(req.query, session_id=req.session_id)
    SESSION_MESSAGES[req.session_id].append({"from": "agent", "text": result["answer"]})
    return result


@app.get("/escalations")
def list_escalations():
    """Staff-facing view of pending tickets - the human side of human-in-the-loop. This is
    read-only; a staff member reviews these and, for actual data changes, acts outside this
    app entirely (through insert_policies.py or direct DB access) - never through the agent."""
    return rag_pipeline.get_pending_escalations()


@app.post("/escalations/{escalation_id}/reply")
def reply_to_escalation(escalation_id: int, req: StaffReplyRequest, session_id: str):
    """A staff member's live reply to a specific student's chat. This writes to the in-memory
    poll queue (SESSION_MESSAGES) and marks the ticket resolved - it does NOT touch policies,
    teachers, courses, or any rulebook data. If the student's question actually requires a
    database change, the staff member makes that change themselves, separately, through
    insert_policies.py - this endpoint only delivers a message back into the chat."""
    SESSION_MESSAGES[session_id].append({"from": "staff", "text": req.text})
    rag_pipeline.resolve_escalation(escalation_id)
    return {"status": "sent"}


@app.get("/poll/{session_id}")
def poll(session_id: str, since: int = 0):
    """The student's browser calls this every few seconds. `since` is how many messages it has
    already shown - only new ones are returned, so the page can display and speak a staff
    reply the moment one arrives, without needing a live phone call or websocket."""
    messages = SESSION_MESSAGES[session_id]
    return {"messages": messages[since:], "total": len(messages)}


WEB_DIR = Path(__file__).resolve().parents[1] / "web"


@app.get("/", include_in_schema=False)
def student_page():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/staff", include_in_schema=False)
def staff_page():
    return FileResponse(WEB_DIR / "staff.html")
