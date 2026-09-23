"""手元資料のメタデータ。owner 単位。再起動で消える（本番は Firestore）。"""

from __future__ import annotations

from threading import Lock
from typing import Any
from uuid import uuid4

_lock = Lock()
# owner_id -> { doc_id -> meta }
_materials: dict[str, dict[str, dict[str, Any]]] = {}
# owner_id -> total bytes
_totals: dict[str, int] = {}


def list_materials(owner_id: str) -> list[dict[str, Any]]:
    if not owner_id.strip():
        return []
    with _lock:
        items = list(_materials.get(owner_id, {}).values())
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def get_material(owner_id: str, doc_id: str) -> dict[str, Any] | None:
    if not owner_id.strip() or not doc_id.strip():
        return None
    with _lock:
        return _materials.get(owner_id, {}).get(doc_id)


def owner_stats(owner_id: str) -> tuple[int, int]:
    with _lock:
        count = len(_materials.get(owner_id, {}))
        total = _totals.get(owner_id, 0)
    return count, total


def add_material(owner_id: str, meta: dict[str, Any]) -> dict[str, Any]:
    if not owner_id.strip():
        raise ValueError("owner_id is required")
    doc_id = meta.get("doc_id") or str(uuid4())
    record = {**meta, "doc_id": doc_id, "owner_id": owner_id}
    size = int(record.get("byte_size") or 0)
    with _lock:
        bucket = _materials.setdefault(owner_id, {})
        bucket[doc_id] = record
        _totals[owner_id] = _totals.get(owner_id, 0) + size
    return record


def update_material(owner_id: str, doc_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    if not owner_id.strip() or not doc_id.strip():
        return None
    with _lock:
        bucket = _materials.get(owner_id, {})
        item = bucket.get(doc_id)
        if item is None:
            return None
        for key in ("tags", "project_id", "index_text"):
            if key in patch:
                item[key] = patch[key]
        return dict(item)


def count_materials_in_project(owner_id: str, project_id: str) -> int:
    with _lock:
        return sum(
            1
            for item in _materials.get(owner_id, {}).values()
            if item.get("project_id") == project_id
        )


def remove_material(owner_id: str, doc_id: str) -> dict[str, Any] | None:
    if not owner_id.strip() or not doc_id.strip():
        return None
    with _lock:
        bucket = _materials.get(owner_id, {})
        item = bucket.pop(doc_id, None)
        if item is None:
            return None
        size = int(item.get("byte_size") or 0)
        _totals[owner_id] = max(0, _totals.get(owner_id, 0) - size)
        return item
