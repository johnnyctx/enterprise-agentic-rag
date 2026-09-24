from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar

log = logging.getLogger("agentic-rag")
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def new_correlation_id() -> str:
    value = str(uuid.uuid4())
    _correlation_id.set(value)
    return value


def audit_event(event: str, **fields) -> None:
    correlation_id = _correlation_id.get() or new_correlation_id()
    log.info(json.dumps({"event": event, "correlation_id": correlation_id, "ts": time.time(), **fields}, default=str))
