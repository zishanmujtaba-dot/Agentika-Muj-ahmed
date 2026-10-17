"""Optional LangSmith spans with aggregate-only payloads and fail-open tracing.

No function arguments, questions, answers, citations, credentials, session IDs or
exception messages are submitted. Enabling tracing uploads stage timings and the
explicit safe summaries below. LangChain/LangGraph are not required.
"""
from contextlib import ExitStack
from functools import wraps
import logging
import os
from threading import Lock

logger = logging.getLogger(__name__)
_client = None
_client_lock = Lock()


def tracing_enabled():
    return (os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
            and bool(os.getenv("LANGSMITH_API_KEY", "").strip()))


def _get_client():
    global _client
    with _client_lock:
        if _client is None:
            from langsmith import Client
            from urllib3.util import Retry
            _client = Client(
                api_key=os.environ["LANGSMITH_API_KEY"],
                api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
                timeout_ms=1000, retry_config=Retry(total=0),
                workspace_id=os.getenv("LANGSMITH_WORKSPACE_ID") or None,
                headers=({"X-Organization-Id": os.environ["LANGSMITH_ORGANIZATION_ID"]}
                         if os.getenv("LANGSMITH_ORGANIZATION_ID") else None),
                hide_inputs=True, omit_traced_runtime_info=True,
            )
    return _client


def _close(stack):
    try:
        stack.close()
    except Exception as exc:
        logger.warning("Optional trace cleanup failed (%s)", type(exc).__name__)


def observed(name, run_type="chain", summarize=None):
    """Trace once when enabled; telemetry failure never replays business logic."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if not tracing_enabled():
                return function(*args, **kwargs)
            stack = ExitStack()
            try:
                from langsmith import trace, tracing_context
                client = _get_client()
                stack.enter_context(tracing_context(enabled=True, client=client,
                    project_name=os.getenv("LANGSMITH_PROJECT", "echo-helpdesk")))
                run = stack.enter_context(trace(name, run_type=run_type, inputs={},
                    client=client, metadata={"application": "echo", "payload_mode": "aggregate-only"}))
            except Exception as exc:
                _close(stack)
                logger.warning("Optional tracing unavailable (%s)", type(exc).__name__)
                return function(*args, **kwargs)
            try:
                result = function(*args, **kwargs)
            except BaseException as exc:
                # Do not let the SDK serialize the original exception/traceback.
                try:
                    run.end(outputs={"outcome": "error", "error_type": type(exc).__name__},
                            error=type(exc).__name__)
                except Exception:
                    pass
                raise
            else:
                try:
                    run.end(outputs=summarize(result) if summarize else {"outcome": "completed"})
                except Exception as exc:
                    logger.warning("Optional trace summary failed (%s)", type(exc).__name__)
                    try:
                        run.end(outputs={"outcome": "summary_unavailable"})
                    except Exception:
                        pass
                return result
            finally:
                # Close with no exception details: raw prompts can appear in errors.
                _close(stack)
        return wrapped
    return decorate


def answer_summary(result):
    return {"status": result.get("status"), "reason": result.get("reason"),
            "needs_human": bool(result.get("needs_human")),
            "source_count": len(result.get("source_ids", []))}


def retrieval_summary(result):
    return {"candidate_count": len(result),
            "best_distance": min((p['distance'] for p in result
                                  if p.get('distance') is not None), default=None)}


def flush_traces():
    if _client is not None:
        try:
            _client.flush()
        except Exception as exc:
            logger.warning("Optional trace flush failed (%s)", type(exc).__name__)
