"""案件フォルダ。owner 単位。GCS_BUCKET があるときは Firestore。"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from app.cloud_config import cloud_persistence_enabled

_lock = Lock()
# owner_id -> { project_id -> meta }
_projects: dict[str, dict[str, dict[str, Any]]] = {}


def list_projects(owner_id: str) -> list[dict[str, Any]]:
    if not owner_id.strip():
        return []
    if cloud_persistence_enabled():
        from app.record_store import list_project_records

        items = [
            item
            for item in list_project_records(owner_id)
            if item.get("owner_id") == owner_id
        ]
        return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)
    with _lock:
        items = list(_projects.get(owner_id, {}).values())
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def get_project(owner_id: str, project_id: str) -> dict[str, Any] | None:
    if not owner_id.strip() or not project_id.strip():
        return None
    if cloud_persistence_enabled():
        from app.record_store import load_project

        return load_project(owner_id, project_id)
    with _lock:
        return _projects.get(owner_id, {}).get(project_id)


def create_project(owner_id: str, name: str) -> dict[str, Any]:
    if not owner_id.strip():
        raise ValueError("owner_id is required")
    label = name.strip()
    if not label:
        raise ValueError("empty project name")
    project_id = str(uuid4())
    record = {
        "project_id": project_id,
        "owner_id": owner_id,
        "name": label[:80],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "photos": [],
        "library_calls": [],
        "citations": [],
        "prompts": [],
        "memo": "",
    }
    _persist(owner_id, record)
    return dict(record)


def note_photo(owner_id: str, project_id: str, photo_id: str) -> dict[str, Any] | None:
    """この作業で上げた写真を記録する。実体はユーザーの写真のまま。"""
    if not photo_id.strip():
        return None
    return _append(
        owner_id,
        project_id,
        "photos",
        {"photo_id": photo_id, "at": _now()},
        "photo_id",
    )


def note_library_call(
    owner_id: str,
    project_id: str,
    doc_id: str,
    title: str,
    via: str,
) -> dict[str, Any] | None:
    """資料庫から呼び出したファイルを記録する。中身は資料庫に残す。"""
    if not doc_id.strip():
        return None
    return _append(
        owner_id,
        project_id,
        "library_calls",
        {
            "doc_id": doc_id,
            "title": (title or doc_id)[:180],
            "via": via if via in ("open", "chat") else "open",
            "at": _now(),
        },
        "doc_id",
    )


def note_citation(
    owner_id: str,
    project_id: str,
    doc_id: str,
    title: str,
    term: str,
    searched_at: str,
    sources: list[dict[str, Any]],
    cached: bool,
) -> dict[str, Any] | None:
    """どの資料を、いつ、どの権利の記録で確認したかを残す。"""
    if not doc_id.strip():
        return None
    rights = []
    for item in sources[:8]:
        rights.append(
            {
                "url": str(item.get("url") or ""),
                "title": str(item.get("title") or "")[:180],
                "license": str(item.get("license") or "unknown"),
                "created": str(item.get("created") or "unknown"),
                "copyright": str(item.get("copyright") or "unknown"),
                "rights_code": str(item.get("rights_code") or ""),
            }
        )
    record = _load(owner_id, project_id)
    if record is None:
        return None
    rows = list(record.get("citations") or [])
    rows.append(
        {
            "doc_id": doc_id,
            "title": (title or doc_id)[:180],
            "term": term[:80],
            "searched_at": searched_at,
            "at": _now(),
            "cached": cached,
            "sources": rights,
        }
    )
    record["citations"] = rows[-40:]
    _persist(owner_id, record)
    return dict(record)


def note_prompt(
    owner_id: str,
    project_id: str,
    label: str,
    message: str,
    answer: str,
) -> dict[str, Any] | None:
    """チャットの質問と返答を、その作業の記録に残す。"""
    text = message.strip()
    if not text:
        return None
    record = _load(owner_id, project_id)
    if record is None:
        return None
    rows = list(record.get("prompts") or [])
    rows.append(
        {
            "at": _now(),
            "label": label.strip()[:80],
            "message": text[:2000],
            "answer": answer.strip()[:4000],
        }
    )
    record["prompts"] = rows[-40:]
    _persist(owner_id, record)
    return dict(record)


def save_memo(owner_id: str, project_id: str, memo: str) -> dict[str, Any] | None:
    """作業の自由メモ。マークダウンのまま保存する。"""
    record = _load(owner_id, project_id)
    if record is None:
        return None
    record["memo"] = memo[:20000]
    _persist(owner_id, record)
    return dict(record)


def _append(
    owner_id: str,
    project_id: str,
    key: str,
    entry: dict[str, Any],
    identity: str,
) -> dict[str, Any] | None:
    record = _load(owner_id, project_id)
    if record is None:
        return None
    rows = [row for row in list(record.get(key) or []) if row.get(identity) != entry.get(identity)]
    rows.append(entry)
    record[key] = rows[-40:]
    _persist(owner_id, record)
    return dict(record)


def _load(owner_id: str, project_id: str) -> dict[str, Any] | None:
    current = get_project(owner_id, project_id)
    if current is None:
        return None
    record = dict(current)
    record["photos"] = list(record.get("photos") or [])
    record["library_calls"] = list(record.get("library_calls") or [])
    record["citations"] = list(record.get("citations") or [])
    record["prompts"] = list(record.get("prompts") or [])
    record["memo"] = str(record.get("memo") or "")
    return record


def _persist(owner_id: str, record: dict[str, Any]) -> None:
    project_id = str(record.get("project_id") or "")
    if cloud_persistence_enabled():
        from app.record_store import save_project

        save_project(owner_id, project_id, record)
        return
    with _lock:
        bucket = _projects.setdefault(owner_id, {})
        bucket[project_id] = record


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def delete_project(owner_id: str, project_id: str) -> bool:
    if cloud_persistence_enabled():
        from app.record_store import delete_project_record

        return delete_project_record(owner_id, project_id)
    with _lock:
        bucket = _projects.get(owner_id, {})
        if project_id not in bucket:
            return False
        del bucket[project_id]
        return True
