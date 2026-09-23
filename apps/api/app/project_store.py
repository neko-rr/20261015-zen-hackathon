"""案件フォルダ。owner 単位。再起動で消える。"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

_lock = Lock()
# owner_id -> { project_id -> meta }
_projects: dict[str, dict[str, dict[str, Any]]] = {}


def list_projects(owner_id: str) -> list[dict[str, Any]]:
    if not owner_id.strip():
        return []
    with _lock:
        items = list(_projects.get(owner_id, {}).values())
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def get_project(owner_id: str, project_id: str) -> dict[str, Any] | None:
    if not owner_id.strip() or not project_id.strip():
        return None
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
    }
    with _lock:
        bucket = _projects.setdefault(owner_id, {})
        bucket[project_id] = record
    return dict(record)


def delete_project(owner_id: str, project_id: str) -> bool:
    with _lock:
        bucket = _projects.get(owner_id, {})
        if project_id not in bucket:
            return False
        del bucket[project_id]
        return True
