"""Durable conversation messages and retry-safe question/reply delivery."""
import hashlib
import hmac
import secrets
from uuid import uuid4

from psycopg2.extras import Json

from .rag_pipeline import db_connection


class ConversationDenied(Exception):
    pass


class RequestConflict(Exception):
    pass


class RequestProcessing(Exception):
    pass


class TicketMissing(Exception):
    pass


def create_conversation():
    session_id, token = str(uuid4()), secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO conversations (session_id, token_hash) VALUES (%s, %s)",
                        (session_id, token_hash))
    return {"session_id": session_id, "session_token": token}


def authorize_conversation(session_id, token):
    if not token or len(token) > 256:
        raise ConversationDenied()
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT token_hash FROM conversations WHERE session_id = %s", (session_id,))
            row = cur.fetchone()
    if not row or not hmac.compare_digest(row[0], hashlib.sha256(token.encode()).hexdigest()):
        raise ConversationDenied()


def reserve_question(session_id, request_id, query):
    """Reserve once, or replay a stored response. Recover crashed reservations after 120s."""
    claim = str(uuid4())
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 1))", (session_id,))
            cur.execute(
                """INSERT INTO chat_requests (session_id, request_id, query, claim)
                   VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING request_id""",
                (session_id, request_id, query, claim),
            )
            if cur.fetchone():
                cur.execute(
                    """INSERT INTO conversation_messages (session_id, sender, text, request_id)
                       VALUES (%s, 'student', %s, %s)""", (session_id, query, request_id),
                )
                return claim, None
            cur.execute(
                """SELECT query, response, updated_at < now() - interval '120 seconds'
                   FROM chat_requests WHERE session_id = %s AND request_id = %s FOR UPDATE""",
                (session_id, request_id),
            )
            original, response, stale = cur.fetchone()
            if original != query:
                raise RequestConflict("Request ID already belongs to another question.")
            if response is not None:
                return None, response
            if not stale:
                raise RequestProcessing()
            cur.execute(
                "UPDATE chat_requests SET claim = %s, updated_at = now() "
                "WHERE session_id = %s AND request_id = %s", (claim, session_id, request_id),
            )
            return claim, None


def finish_question(session_id, request_id, claim, result):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 1))", (session_id,))
            cur.execute(
                """UPDATE chat_requests SET response = %s, updated_at = now()
                   WHERE session_id = %s AND request_id = %s AND claim = %s
                     AND response IS NULL RETURNING request_id""",
                (Json(result), session_id, request_id, claim),
            )
            if not cur.fetchone():
                raise RequestProcessing()
            cur.execute(
                """INSERT INTO conversation_messages
                   (session_id, sender, text, request_id, metadata)
                   VALUES (%s, 'agent', %s, %s, %s)""",
                (session_id, result["answer"], request_id, Json(result)),
            )
    return result


def messages_after(session_id, after=0):
    with db_connection() as conn:
        with conn.cursor() as cur:
            # Serialize readers with message writers for this conversation. Sequence IDs
            # alone do not guarantee commit order; the lock prevents cursor skips.
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 1))", (session_id,))
            cur.execute(
                """SELECT m.id, m.sender, m.text, m.created_at, m.request_id, m.metadata,
                          COALESCE(m.metadata->>'question', e.student_query)
                   FROM conversation_messages m
                   LEFT JOIN escalations e ON e.id = m.escalation_id AND e.session_id = m.session_id
                   WHERE m.session_id = %s AND m.id > %s
                   ORDER BY m.id LIMIT 100""", (session_id, after),
            )
            rows = cur.fetchall()
    messages = [{"id": r[0], "from": r[1], "text": r[2], "created_at": r[3].isoformat(),
                 "request_id": r[4], "metadata": r[5],
                 "reply_to": {"question": r[6]} if r[1] == 'staff' and r[6] else None}
                for r in rows]
    return {"messages": messages, "cursor": rows[-1][0] if rows else after,
            "has_more": len(rows) == 100}


def pending_tickets():
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT e.id, e.created_at, e.student_query, e.reason, e.department,
                          c.session_id IS NOT NULL
                   FROM escalations e LEFT JOIN conversations c ON c.session_id = e.session_id
                   WHERE e.status = 'pending' ORDER BY e.created_at, e.id LIMIT 100"""
            )
            return [{"id": r[0], "created_at": r[1].isoformat(), "student_query": r[2],
                     "reason": r[3], "department": r[4], "can_reply": r[5]}
                    for r in cur.fetchall()]


def reply_to_ticket(ticket_id, text, staff_name):
    """Save reply and resolve atomically; retrying the same reply replays success."""
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT session_id, status, student_query, department FROM escalations WHERE id = %s FOR UPDATE",
                        (ticket_id,))
            ticket = cur.fetchone()
            if not ticket:
                raise TicketMissing()
            session_id, status, original_question, department = ticket
            cur.execute("SELECT 1 FROM conversations WHERE session_id = %s", (session_id,))
            if not cur.fetchone():
                raise RequestConflict("Legacy ticket has no recoverable student conversation.")
            if status == 'resolved':
                cur.execute(
                    "SELECT id, text FROM conversation_messages "
                    "WHERE escalation_id = %s AND sender = 'staff'", (ticket_id,),
                )
                previous = cur.fetchone()
                if previous and previous[1] == text:
                    return {"status": "sent", "message_id": previous[0]}
                raise RequestConflict("This ticket has already been resolved.")
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 1))", (session_id,))
            cur.execute(
                """INSERT INTO conversation_messages
                   (session_id, sender, text, escalation_id, metadata)
                   VALUES (%s, 'staff', %s, %s, %s) RETURNING id""",
                (session_id, text, ticket_id, Json({"author": staff_name, "ticket_id": ticket_id,
                                                   "question": original_question, "department": department})),
            )
            message_id = cur.fetchone()[0]
            cur.execute("UPDATE escalations SET status = 'resolved' WHERE id = %s", (ticket_id,))
    return {"status": "sent", "message_id": message_id}
