"""ECHO API with authorized conversations, persistent replies, and staff access control."""
import hmac
import logging
import os
import psycopg2
from pathlib import Path
from threading import Lock
from time import monotonic
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import conversations, rag_pipeline
from .observability import flush_traces

logger = logging.getLogger(__name__)
app = FastAPI(title="ECHO helpdesk")
WEB_DIR = Path(__file__).resolve().parents[1] / "web"
security = HTTPBasic(auto_error=False)
_auth_failures = {}
_auth_lock = Lock()


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=2000)
    session_id: UUID
    request_id: UUID = Field(default_factory=uuid4)


class StaffReplyRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=6000)


def require_staff(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    username = os.environ.get("STAFF_USERNAME", "staff")
    password = os.environ.get("STAFF_PASSWORD", "")
    if not password or password == "set_by_configure_runtime":
        raise HTTPException(503, "Staff access is not configured.")
    address = request.client.host if request.client else "unknown"
    now = monotonic()
    with _auth_lock:
        failures = [t for t in _auth_failures.get(address, []) if now - t < 60]
        if len(failures) >= 5:
            raise HTTPException(429, "Too many login attempts. Wait one minute.",
                                headers={"Retry-After": "60"})
    valid_user = hmac.compare_digest((credentials.username if credentials else "").encode(),
                                     username.encode())
    valid_password = hmac.compare_digest((credentials.password if credentials else "").encode(),
                                         password.encode())
    if not credentials or not (valid_user and valid_password):
        if credentials:
            with _auth_lock:
                # Keep this single-process demo limiter bounded.
                if len(_auth_failures) >= 1000:
                    _auth_failures.clear()
                _auth_failures[address] = failures + [now]
        raise HTTPException(401, "Staff username or password is incorrect.")
    with _auth_lock:
        _auth_failures.pop(address, None)
    return username


@app.middleware("http")
async def same_origin_and_headers(request: Request, call_next):
    # No cross-origin CORS access. Browser mutations must originate from this host.
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
        if origin.rstrip("/") != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Cross-origin requests are not permitted."}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    policy = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    if not request.url.path.startswith(("/docs", "/redoc")):
        response.headers["Content-Security-Policy"] = policy
    return response


@app.exception_handler(psycopg2.Error)
async def database_unavailable(request, exc):
    logger.warning("Conversation storage unavailable (%s)", type(exc).__name__)
    return JSONResponse({"detail": "Conversation storage is unavailable. Please retry shortly."},
                        status_code=503)


@app.exception_handler(conversations.ConversationDenied)
async def conversation_denied(request, exc):
    return JSONResponse({"detail": "Conversation access denied. Start a new conversation."}, status_code=401)


@app.exception_handler(conversations.RequestProcessing)
async def request_processing(request, exc):
    return JSONResponse({"detail": "Your question is still processing. Retry the same request shortly."},
                        status_code=409, headers={"Retry-After": "3"})


@app.exception_handler(conversations.RequestConflict)
async def request_conflict(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.exception_handler(conversations.TicketMissing)
async def ticket_missing(request, exc):
    return JSONResponse({"detail": "Ticket not found."}, status_code=404)


@app.on_event("startup")
def startup():
    rag_pipeline.init_pipeline()


@app.on_event("shutdown")
def shutdown():
    rag_pipeline.close_pipeline()
    flush_traces()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    try:
        with rag_pipeline.db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM public_policies")
                policy_count = cur.fetchone()[0]
                cur.execute("SELECT 1 FROM conversations LIMIT 1")
                cur.execute("SELECT 1 FROM conversation_messages LIMIT 1")
                cur.execute("SELECT 1 FROM chat_requests LIMIT 1")
        if not policy_count:
            raise ValueError("No policies loaded")
    except Exception as exc:
        logger.warning("Readiness check failed (%s)", type(exc).__name__)
        return JSONResponse({"status": "not_ready", "detail": "Database setup or policy ingestion is incomplete."}, status_code=503)
    return {"status": "ready", "public_policies": policy_count,
            "provider_configured": bool(os.environ.get("GROQ_API_KEY", "").strip())}


@app.post("/sessions", status_code=201)
def new_session():
    return conversations.create_conversation()


@app.post("/ask")
def ask(req: AskRequest, session_token: str | None = Header(default=None, alias="X-Conversation-Token")):
    session_id, request_id = str(req.session_id), str(req.request_id)
    conversations.authorize_conversation(session_id, session_token)
    claim, previous = conversations.reserve_question(session_id, request_id, req.query)
    if previous is not None:
        return previous
    try:
        previous_question = conversations.previous_student_question(session_id, request_id)
        result = rag_pipeline.answer_query(req.query, session_id=session_id,
                                           previous_question=previous_question)
    except Exception as exc:
        # Complete the reserved request with a durable, honest fallback when possible.
        logger.warning("Question processing failed (%s)", type(exc).__name__)
        result = rag_pipeline.escalate(req.query, session_id, "processing_failed")
    return conversations.finish_question(session_id, request_id, claim, result)


@app.get("/poll/{session_id}")
def poll(session_id: UUID, since: int = Query(default=0, ge=0, le=9223372036854775807),
         session_token: str | None = Header(default=None, alias="X-Conversation-Token")):
    session_id = str(session_id)
    conversations.authorize_conversation(session_id, session_token)
    return conversations.messages_after(session_id, since)


@app.get("/escalations")
def list_escalations(staff_name: str = Depends(require_staff)):
    return conversations.pending_tickets()


@app.post("/escalations/{escalation_id}/reply")
def reply_to_escalation(escalation_id: int, req: StaffReplyRequest,
                        staff_name: str = Depends(require_staff)):
    return conversations.reply_to_ticket(escalation_id, req.text, staff_name)


@app.get("/staff/auth")
def staff_auth(staff_name: str = Depends(require_staff)):
    return {"username": staff_name}


@app.get("/", include_in_schema=False)
def student_page():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/staff", include_in_schema=False)
def staff_page():
    return FileResponse(WEB_DIR / "staff.html")


app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")
