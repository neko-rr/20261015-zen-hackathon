"""ユーザー名とパスワードのアカウント。owner_id はアカウントごと。メールは使わない。"""

from __future__ import annotations

import logging
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from app.cloud_config import cloud_persistence_enabled
from app.errors import business_error
from app.passwords import hash_password, verify_password

logger = logging.getLogger(__name__)

# 審査用。提出文と画面に出す公開のテストアカウント。一般利用者とは owner が別。
DEMO_USERNAME = "reviewer"
DEMO_PASSWORD = "review-draw-2026"

_USERNAME = re.compile(r"^[a-z0-9][a-z0-9_-]{2,31}$")
_MIN_PASSWORD = 8
_NAME_WORDS = (
    "ink",
    "line",
    "pose",
    "sketch",
    "paper",
    "brush",
    "frame",
    "study",
    "figure",
    "angle",
)
_lock = Lock()
# username -> record
_accounts: dict[str, dict[str, str]] = {}


@dataclass(frozen=True)
class Account:
    username: str
    owner_id: str


def normalize_username(raw: str) -> str:
    return raw.strip().lower()


def suggest_username() -> str:
    """まだ使われていないユーザー名を1つ返す。予約はしない。"""
    for _ in range(8):
        word = secrets.choice(_NAME_WORDS)
        suffix = secrets.randbelow(9000) + 1000
        name = f"{word}-{suffix}"
        if name == DEMO_USERNAME or not _USERNAME.match(name):
            continue
        if _find(name) is None:
            return name
    raise business_error(
        "username_unavailable",
        "空いている名前を用意できませんでした。もう一度押してください。",
    )


def register_account(username: str, password: str) -> Account:
    name = _check_username(username)
    _check_password(password)
    if name == DEMO_USERNAME:
        raise business_error("username_taken", "このユーザー名は使えません。")
    if _find(name) is not None:
        raise business_error("username_taken", "このユーザー名は既に使われています。")
    account = Account(username=name, owner_id=str(uuid4()))
    _save(account, hash_password(password))
    return account


def authenticate(username: str, password: str) -> Account | None:
    name = normalize_username(username)
    if not name or not password:
        return None
    record = _find(name)
    if record is None:
        return None
    if not verify_password(password, record["password_hash"]):
        return None
    return Account(username=name, owner_id=record["owner_id"])


def username_for_owner(owner_id: str) -> str:
    if not owner_id.strip():
        return ""
    if cloud_persistence_enabled():
        from app.record_store import find_account_username

        return find_account_username(owner_id)
    with _lock:
        for name, record in _accounts.items():
            if record.get("owner_id") == owner_id:
                return name
    return ""


def seed_reviewer() -> None:
    """審査用アカウントを用意する。既にあれば同じ owner_id のままパスワードを公開値に戻す。"""
    record = _find(DEMO_USERNAME)
    password_hash = hash_password(DEMO_PASSWORD)
    if record is None:
        _save(Account(username=DEMO_USERNAME, owner_id=str(uuid4())), password_hash)
        logger.info("reviewer account created")
        return
    _save(
        Account(username=DEMO_USERNAME, owner_id=record["owner_id"]),
        password_hash,
    )


def _check_username(username: str) -> str:
    name = normalize_username(username)
    if not _USERNAME.match(name):
        raise business_error(
            "invalid_username",
            "ユーザー名は英小文字・数字・ハイフン・アンダースコアで、3文字以上にしてください。",
        )
    return name


def _check_password(password: str) -> None:
    if len(password) < _MIN_PASSWORD:
        raise business_error("invalid_password", "パスワードは8文字以上にしてください。")


def _find(username: str) -> dict[str, str] | None:
    if cloud_persistence_enabled():
        from app.record_store import load_account

        return load_account(username)
    with _lock:
        record = _accounts.get(username)
        return dict(record) if record else None


def _save(account: Account, password_hash: str) -> None:
    record = {
        "username": account.username,
        "owner_id": account.owner_id,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if cloud_persistence_enabled():
        from app.record_store import save_account

        save_account(account.username, record)
        return
    with _lock:
        current = _accounts.get(account.username)
        if current and current.get("created_at"):
            record["created_at"] = current["created_at"]
        _accounts[account.username] = record
