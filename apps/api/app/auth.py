"""署名付きセッション Cookie。第三者 IdP は使わない。"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request, Response

from app.errors import business_error, unauthorized_error

COOKIE_NAME = "drawref_session"
SESSION_MAX_AGE_SEC = 60 * 60 * 24 * 7


@dataclass(frozen=True)
class Principal:
    kind: str
    id: str


def _sign(session_id: str, secret: str) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{session_id}.{digest}"


def parse_session_value(raw: str | None, secret: str) -> str | None:
    if not raw or not secret:
        return None
    if "." not in raw:
        return None
    session_id, signature = raw.rsplit(".", 1)
    if not session_id.strip() or not signature.strip():
        return None
    expected = hmac.new(
        secret.encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    return session_id


def require_signing_secret(secret: str) -> None:
    if not secret.strip():
        raise business_error(
            "config_missing",
            "SESSION_SIGNING_SECRET が未設定です。.env に長いランダム文字列を書いてください。",
        )


def principal_from_request(request: Request, secret: str) -> Principal | None:
    raw = request.cookies.get(COOKIE_NAME)
    session_id = parse_session_value(raw, secret)
    if session_id is None:
        return None
    return Principal(kind="session", id=session_id)


def require_principal(request: Request, secret: str) -> Principal:
    principal = principal_from_request(request, secret)
    if principal is None:
        raise unauthorized_error(
            "session_required",
            "セッションがありません。「はじめる」から開始してください。",
        )
    return principal


def attach_session_cookie(
    response: Response,
    session_id: str,
    secret: str,
    *,
    secure: bool,
) -> None:
    require_signing_secret(secret)
    response.set_cookie(
        key=COOKIE_NAME,
        value=_sign(session_id, secret),
        max_age=SESSION_MAX_AGE_SEC,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def mint_session_id() -> str:
    return str(uuid4())
