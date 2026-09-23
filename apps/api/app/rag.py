"""手元資料の索引と検索。RAG Engine 未設定時はローカル簡易検索。"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_lock = Lock()
_index: dict[str, list[dict[str, Any]]] = {}


def rag_engine_enabled() -> bool:
    return os.getenv("RAG_ENABLED", "").strip().lower() == "true"


def data_root() -> Path:
    root = Path(__file__).resolve().parents[1] / ".data" / "materials"
    root.mkdir(parents=True, exist_ok=True)
    return root


def material_dir(owner_id: str, material_kind: str, doc_id: str) -> Path:
    path = data_root() / owner_id / material_kind / doc_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def upsert_index_entry(owner_id: str, entry: dict[str, Any]) -> None:
    if not owner_id.strip():
        return
    doc_id = str(entry.get("doc_id") or "")
    with _lock:
        rows = _index.setdefault(owner_id, [])
        rows[:] = [row for row in rows if row.get("doc_id") != doc_id]
        rows.append(
            {
                "doc_id": doc_id,
                "title": entry.get("title") or "",
                "material_kind": entry.get("material_kind") or "third_party",
                "media_type": entry.get("media_type") or "note",
                "page": entry.get("page") or "unknown",
                "text": entry.get("text") or "",
                "project_id": entry.get("project_id") or "",
                "tags": list(entry.get("tags") or []),
            }
        )


def remove_index_entry(owner_id: str, doc_id: str) -> None:
    with _lock:
        rows = _index.get(owner_id, [])
        _index[owner_id] = [row for row in rows if row.get("doc_id") != doc_id]


def retrieve(
    owner_id: str,
    query: str,
    limit: int = 4,
    project_id: str = "",
) -> list[dict[str, Any]]:
    """owner 配下だけを検索。横断しない。project_id 指定時はその案件のみ。"""
    if not owner_id.strip() or not query.strip():
        return []
    if rag_engine_enabled():
        try:
            return _retrieve_vertex(owner_id, query, limit, project_id)
        except Exception:
            logger.exception("vertex rag failed; fallback local")
    return _retrieve_local(owner_id, query, limit, project_id)


def _retrieve_local(
    owner_id: str,
    query: str,
    limit: int,
    project_id: str = "",
) -> list[dict[str, Any]]:
    tokens = [t for t in re.split(r"\s+", query.lower()) if t]
    pid = project_id.strip()
    with _lock:
        rows = list(_index.get(owner_id, []))
    if pid:
        rows = [row for row in rows if row.get("project_id") == pid]
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        hay = f"{row.get('title', '')}\n{row.get('text', '')}".lower()
        q = query.lower().strip()
        score = sum(1 for token in tokens if token in hay)
        if score <= 0 and q and q in hay:
            score = 1
        if score <= 0 and tokens:
            continue
        if not tokens:
            score = 1
        scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    hits: list[dict[str, Any]] = []
    for score, row in scored[:limit]:
        text = str(row.get("text") or "")[:1200]
        hits.append(
            {
                "url": f"material://{row['doc_id']}",
                "title": row.get("title") or row["doc_id"],
                "text": text,
                "material_kind": row.get("material_kind") or "third_party",
                "media_type": row.get("media_type") or "note",
                "page": row.get("page") or "unknown",
                "doc_id": row["doc_id"],
                "project_id": row.get("project_id") or "",
                "tags": list(row.get("tags") or []),
            }
        )
    return hits


def _retrieve_vertex(
    owner_id: str,
    query: str,
    limit: int,
    project_id: str = "",
) -> list[dict[str, Any]]:
    logger.info("vertex rag stub owner=%s; using local index", owner_id[:8])
    return _retrieve_local(owner_id, query, limit, project_id)


def index_as_chunks(hits: list[dict[str, Any]]) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for hit in hits:
        chunks.append(
            {
                "url": hit.get("url") or "",
                "title": hit.get("title") or "",
                "text": hit.get("text") or "",
                "material_kind": hit.get("material_kind") or "third_party",
            }
        )
    return chunks
