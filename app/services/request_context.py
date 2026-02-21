from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_logger = logging.getLogger("moretale.api")


def generate_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(request_id: str | None) -> Token[str | None]:
    return _request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


def reset_request_id(token: Token[str | None]) -> None:
    _request_id_ctx.reset(token)


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "level": logging.getLevelName(level),
        "request_id": fields.pop("request_id", None) or get_request_id(),
        "event": event,
    }
    payload.update({key: value for key, value in fields.items() if value is not None})
    _logger.log(level, json.dumps(payload, ensure_ascii=False))

