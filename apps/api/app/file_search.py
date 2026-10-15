"""人ごとの Gemini API File Search。RAG Engine は使わない。

Developer API 専用。Enterprise（Vertex）のクライアントではストアを作れない。
検索は、その owner のストア名だけを渡す。返ってきた断片も、その人の資料に
一致するものだけ残す。
"""

from __future__ import annotations

import io
import logging
import os
import re
import time
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_SAFE_FILTER = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_WAIT_SECONDS = 45
_lock = Lock()
_stores: dict[str, str] = {}
_client_obj = None


def configured() -> bool:
    return _enabled() and bool(_api_key())


def metadata_filter(project_id: str) -> str | None:
    pid = (project_id or "").strip()
    if not pid or not _SAFE_FILTER.fullmatch(pid):
        return None
    return f'project_id = "{pid}"'


def index_material(owner_id: str, meta: dict[str, Any]) -> str:
    """索引テキストをその人のストアへ上げる。失敗時は空。文書名を返す。"""
    if not configured() or not owner_id.strip():
        return ""
    text = str(meta.get("index_text") or meta.get("title") or "").strip()
    doc_id = str(meta.get("doc_id") or "").strip()
    if not text or not doc_id:
        return ""
    try:
        store = ensure_store(owner_id)
        if not store:
            return ""
        payload = io.BytesIO(text.encode("utf-8"))
        payload.name = "index.txt"  # type: ignore[attr-defined]
        items = [
            {"key": "doc_id", "string_value": doc_id},
            {
                "key": "material_kind",
                "string_value": str(meta.get("material_kind") or "third_party"),
            },
        ]
        project_id = str(meta.get("project_id") or "").strip()
        if project_id and _SAFE_FILTER.fullmatch(project_id):
            items.append({"key": "project_id", "string_value": project_id})
        client = _client()
        operation = client.file_search_stores.upload_to_file_search_store(
            file_search_store_name=store,
            file=payload,
            config={
                "mime_type": "text/plain",
                "display_name": str(meta.get("title") or doc_id)[:200],
                "custom_metadata": items,
            },
        )
        operation = _wait(client, operation)
        if getattr(operation, "error", None):
            logger.error("file search index error owner=%s", owner_id[:8])
            return ""
        response = getattr(operation, "response", None)
        name = str(getattr(response, "document_name", "") or "")
        if name.startswith(f"{store}/documents/"):
            return name
        return ""
    except Exception as exc:
        _log_failure("index", owner_id, exc)
        return ""


def remove_document(owner_id: str, document_name: str) -> None:
    """その人のストア配下の文書だけ消す。"""
    if not configured() or not owner_id.strip():
        return
    name = (document_name or "").strip()
    store = _load_store(owner_id)
    if not store or not name.startswith(f"{store}/documents/"):
        return
    try:
        _client().file_search_stores.documents.delete(name=name)
    except Exception as exc:
        _log_failure("delete", owner_id, exc)


def search(
    owner_id: str,
    query: str,
    rows: list[dict[str, Any]],
    limit: int = 4,
    project_id: str = "",
) -> list[dict[str, Any]]:
    """その人のストアだけを意味検索する。一致しない断片は捨てる。"""
    if not configured() or not owner_id.strip() or not query.strip() or limit <= 0:
        return []
    store = _load_store(owner_id)
    if not store:
        return []
    model = os.getenv("GEMINI_MODEL", "").strip()
    if not model:
        return []
    file_search_tool = {
        "file_search_store_names": [store],
        "top_k": limit,
    }
    filt = metadata_filter(project_id)
    if filt:
        file_search_tool["metadata_filter"] = filt
    try:
        from google.genai import types

        client = _client()
        response = client.models.generate_content(
            model=model,
            contents=query.strip()[:800],
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=128,
                system_instruction="関係する資料が無ければ「なし」とだけ答える。",
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(**file_search_tool)
                    )
                ],
            ),
        )
    except Exception as exc:
        _log_failure("query", owner_id, exc)
        return []
    return hits_from_chunks(_chunks(response), rows, project_id, limit)


def hits_from_chunks(
    chunks: list[Any],
    rows: list[dict[str, Any]],
    project_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    by_doc = {str(row.get("doc_id") or ""): row for row in rows if row.get("doc_id")}
    by_name = {
        str(row.get("file_search_document") or ""): row
        for row in rows
        if row.get("file_search_document")
    }
    pid = project_id.strip()
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in chunks:
        ctx = _context(chunk)
        if ctx is None:
            continue
        meta = _meta_map(ctx)
        row = by_doc.get(meta.get("doc_id", "")) or by_name.get(_text(ctx, "document_name"))
        if row is None:
            continue
        doc_id = str(row.get("doc_id") or "")
        if not doc_id or doc_id in seen:
            continue
        if pid and str(row.get("project_id") or "") != pid:
            continue
        seen.add(doc_id)
        text = _text(ctx, "text") or str(row.get("text") or "")
        hits.append(
            {
                "url": f"material://{doc_id}",
                "title": row.get("title") or doc_id,
                "text": text[:1200],
                "material_kind": row.get("material_kind") or "third_party",
                "media_type": row.get("media_type") or "note",
                "page": _text(ctx, "page_number") or row.get("page") or "unknown",
                "doc_id": doc_id,
                "project_id": row.get("project_id") or "",
                "tags": list(row.get("tags") or []),
            }
        )
        if len(hits) >= limit:
            break
    return hits


def ensure_store(owner_id: str) -> str:
    if not owner_id.strip():
        return ""
    current = _load_store(owner_id)
    if current:
        return current
    with _lock:
        current = _load_store(owner_id)
        if current:
            return current
        created = _client().file_search_stores.create(
            config={"display_name": f"owner-{owner_id}"[:120]}
        )
        name = str(getattr(created, "name", "") or "")
        if not name.startswith("fileSearchStores/"):
            return ""
        _save_store(owner_id, name)
        return name


def _enabled() -> bool:
    return os.getenv("RAG_ENABLED", "").strip().lower() == "true"


def _api_key() -> str:
    return (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )


def _client():
    global _client_obj
    if _client_obj is not None:
        return _client_obj
    from google import genai
    from google.genai import types

    # 環境の Enterprise フラグがあっても、File Search は Developer API へ出す。
    # クライアントは使い回す。再試行で http クライアントが閉じると鍵がログに残りやすい。
    _client_obj = genai.Client(
        api_key=_api_key(),
        vertexai=False,
        http_options=types.HttpOptions(
            timeout=60_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    return _client_obj


def _log_failure(action: str, owner_id: str, exc: Exception) -> None:
    logger.error(
        "file search %s failed owner=%s type=%s detail=%s",
        action,
        owner_id[:8],
        type(exc).__name__,
        _scrub(exc),
    )


def _scrub(exc: Exception) -> str:
    msg = str(getattr(exc, "message", "") or exc)
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            msg = msg.replace(value, "[redacted]")
    msg = re.sub(r"key=[^&\s\"']+", "key=[redacted]", msg)
    msg = re.sub(r"AIza[0-9A-Za-z_\-]{10,}", "[redacted]", msg)
    return msg[:300]


def _load_store(owner_id: str) -> str:
    cached = _stores.get(owner_id, "")
    if cached.startswith("fileSearchStores/"):
        return cached
    from app.cloud_config import cloud_persistence_enabled

    if not cloud_persistence_enabled():
        return ""
    from app.record_store import load_file_search_store

    name = load_file_search_store(owner_id)
    if name:
        _stores[owner_id] = name
    return name


def _save_store(owner_id: str, store_name: str) -> None:
    _stores[owner_id] = store_name
    from app.cloud_config import cloud_persistence_enabled

    if not cloud_persistence_enabled():
        return
    from app.record_store import save_file_search_store

    save_file_search_store(owner_id, store_name)


def _wait(client, operation):
    deadline = time.monotonic() + _WAIT_SECONDS
    while not getattr(operation, "done", False):
        if time.monotonic() >= deadline:
            raise TimeoutError("file search index timed out")
        time.sleep(1)
        operation = client.operations.get(operation)
    return operation


def _chunks(response) -> list[Any]:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    meta = getattr(candidates[0], "grounding_metadata", None)
    if meta is None:
        return []
    return list(getattr(meta, "grounding_chunks", None) or [])


def _context(chunk) -> Any:
    return getattr(chunk, "retrieved_context", None)


def _text(ctx, name: str) -> str:
    value = getattr(ctx, name, None)
    if value is None:
        return ""
    return str(value)


def _meta_map(ctx) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in getattr(ctx, "custom_metadata", None) or []:
        key = str(getattr(item, "key", "") or "")
        value = getattr(item, "string_value", None)
        if key and value is not None:
            out[key] = str(value)
    return out
