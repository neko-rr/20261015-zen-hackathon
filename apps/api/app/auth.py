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


def _payload(kind: str, owner_id: str) -> str:
    return f"{kind}:{owner_id}"


def _sign(kind: str, owner_id: str, secret: str) -> str:
    body = _payload(kind, owner_id)
    digest = hmac.new(
        secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{body}.{digest}"


def parse_session_value(raw: str | None, secret: str) -> tuple[str, str] | None:
    """署名が正しければ (kind, owner_id)。旧形式の uuid.署名 はゲストとして扱う。"""
    if not raw or not secret:
        return None
    if "." not in raw:
        return None
    body, signature = raw.rsplit(".", 1)
    if not body.strip() or not signature.strip():
        return None
    expected = hmac.new(
        secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    if ":" in body:
        kind, owner_id = body.split(":", 1)
        if kind not in {"session", "account"} or not owner_id.strip():
            return None
        return kind, owner_id
    return "session", body


def require_signing_secret(secret: str) -> None:
    if not secret.strip():
        raise business_error(
            "config_missing",
            "SESSION_SIGNING_SECRET が未設定です。.env に長いランダム文字列を書いてください。",
        )


def principal_from_request(request: Request, secret: str) -> Principal | None:
    raw = request.cookies.get(COOKIE_NAME)
    parsed = parse_session_value(raw, secret)
    if parsed is None:
        return None
    kind, owner_id = parsed
    return Principal(kind=kind, id=owner_id)


def require_principal(request: Request, secret: str) -> Principal:
    principal = principal_from_request(request, secret)
    if principal is None:
        raise unauthorized_error(
            "session_required",
            "ログインがありません。アカウントで入ってください。",
        )
    return principal


def require_account(request: Request, secret: str) -> Principal:
    """保存できるのはアカウントだけ。ゲストの Cookie ではフォルダを増やさない。"""
    principal = require_principal(request, secret)
    if principal.kind != "account":
        raise unauthorized_error(
            "session_required",
            "ログインがありません。アカウントで入ってください。",
        )
    return principal


def clear_session_cookie(response: Response, *, secure: bool) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=secure,
    )


def attach_session_cookie(
    response: Response,
    session_id: str,
    secret: str,
    *,
    secure: bool,
    kind: str = "session",
) -> None:
    require_signing_secret(secret)
    response.set_cookie(
        key=COOKIE_NAME,
        value=_sign(kind, session_id, secret),
        max_age=SESSION_MAX_AGE_SEC,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def mint_session_id() -> str:
    return str(uuid4())
