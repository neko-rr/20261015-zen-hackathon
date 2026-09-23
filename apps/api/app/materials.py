"""手元資料の登録・一覧・削除・タグ／案件更新。"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.errors import business_error, system_error
from app.extract import (
    MATERIAL_KINDS,
    MAX_MATERIAL_BYTES,
    MAX_MATERIALS_COUNT,
    MAX_MATERIALS_TOTAL_BYTES,
    guess_mime,
    prepare_index_payload,
    resolve_media_type,
)
from app.material_store import (
    add_material,
    get_material,
    list_materials,
    owner_stats,
    remove_material,
    update_material,
)
from app.project_store import get_project
from app.rag import material_dir, remove_index_entry, upsert_index_entry

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._\-\u3040-\u30ff\u3400-\u9fff]+")
_MAX_TAGS = 12
_MAX_TAG_LEN = 40


def normalize_tags(raw: list[str] | None) -> list[str]:
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in raw:
        tag = " ".join(str(item).split()).strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        out.append(tag[:_MAX_TAG_LEN])
        if len(out) >= _MAX_TAGS:
            break
    return out


def register_material(
    owner_id: str,
    material_kind: str,
    filename: str,
    content_type: str | None,
    raw: bytes,
    project_id: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    if not owner_id.strip():
        raise business_error("session_required", "先にセッションを開始してください。")
    kind = material_kind.strip()
    if kind not in MATERIAL_KINDS:
        raise business_error(
            "invalid_material_kind",
            "資料の種別は own_work か third_party を指定してください。",
        )
    if not raw:
        raise business_error("invalid_material", "ファイルが空です。")
    if len(raw) > MAX_MATERIAL_BYTES:
        raise business_error("material_too_large", "資料は 100MB 以下にしてください。")

    media_type = resolve_media_type(filename, content_type)
    if media_type is None:
        raise business_error(
            "unsupported_material_type",
            "JPEG、PNG、WebP、PDF、Word、Excel、Markdown、テキストのいずれかを上げてください。",
        )

    pid = (project_id or "").strip()
    if pid and get_project(owner_id, pid) is None:
        raise business_error("object_not_found", "案件が見つかりません。")

    count, total = owner_stats(owner_id)
    if count >= MAX_MATERIALS_COUNT:
        raise business_error("material_limit", "資料は 30 件までです。")
    if total + len(raw) > MAX_MATERIALS_TOTAL_BYTES:
        raise business_error("material_limit", "資料の合計は 2GB までです。")

    doc_id = str(uuid4())
    safe_name = _safe_filename(filename)
    mime = guess_mime(filename, content_type)
    clean_tags = normalize_tags(tags)

    try:
        index_text, derivative, page = prepare_index_payload(media_type, safe_name, raw)
        index_text = _with_tags(index_text, clean_tags)
        folder = material_dir(owner_id, kind, doc_id)
        original_path = folder / safe_name
        original_path.write_bytes(raw)
        if derivative:
            (folder / "index.jpg").write_bytes(derivative)
        (folder / "index.txt").write_text(index_text, encoding="utf-8")
    except business_error:
        raise
    except Exception as exc:
        logger.exception("material save failed")
        raise system_error("material_failed", "資料の保存に失敗しました。") from exc

    meta = {
        "doc_id": doc_id,
        "owner_id": owner_id,
        "material_kind": kind,
        "media_type": media_type,
        "title": safe_name,
        "mime_type": mime,
        "byte_size": len(raw),
        "page": page,
        "project_id": pid,
        "tags": clean_tags,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "relative_path": str(Path(owner_id) / kind / doc_id / safe_name).replace("\\", "/"),
        "index_text": index_text,
    }
    add_material(owner_id, meta)
    _reindex(owner_id, meta)
    logger.info(
        "material_saved kind=%s media=%s bytes=%s",
        kind,
        media_type,
        len(raw),
    )
    return _public_meta(meta)


def patch_material(
    owner_id: str,
    doc_id: str,
    tags: list[str] | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    item = get_material(owner_id, doc_id)
    if item is None:
        raise business_error("object_not_found", "資料が見つかりません。")

    patch: dict[str, Any] = {}
    new_tags = list(item.get("tags") or [])
    if tags is not None:
        new_tags = normalize_tags(tags)
        patch["tags"] = new_tags
    if project_id is not None:
        pid = project_id.strip()
        if pid and get_project(owner_id, pid) is None:
            raise business_error("object_not_found", "案件が見つかりません。")
        patch["project_id"] = pid

    base_text = item.get("index_text") or item.get("title") or ""
    body = "\n".join(
        line for line in str(base_text).splitlines() if not line.startswith("tags:")
    )
    patch["index_text"] = _with_tags(body, new_tags)

    updated = update_material(owner_id, doc_id, patch)
    if updated is None:
        raise business_error("object_not_found", "資料が見つかりません。")
    _reindex(owner_id, updated)
    return _public_meta(updated)


def list_owner_materials(owner_id: str, project_id: str = "") -> list[dict[str, Any]]:
    items = list_materials(owner_id)
    if project_id.strip():
        items = [item for item in items if item.get("project_id") == project_id.strip()]
    return [_public_meta(item) for item in items]


def list_owner_tags(owner_id: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in list_materials(owner_id):
        for tag in item.get("tags") or []:
            if tag not in seen:
                seen.add(tag)
                out.append(tag)
    return sorted(out)


def delete_material(owner_id: str, doc_id: str) -> None:
    item = get_material(owner_id, doc_id)
    if item is None:
        raise business_error("object_not_found", "資料が見つかりません。")
    removed = remove_material(owner_id, doc_id)
    if removed is None:
        raise business_error("object_not_found", "資料が見つかりません。")
    remove_index_entry(owner_id, doc_id)
    try:
        folder = material_dir(owner_id, removed["material_kind"], doc_id)
        for path in folder.glob("*"):
            path.unlink(missing_ok=True)
        folder.rmdir()
    except Exception:
        logger.exception("material file cleanup failed")


def _with_tags(text: str, tags: list[str]) -> str:
    if not tags:
        return text
    line = "tags: " + " ".join(tags)
    return f"{line}\n{text}".strip()


def _reindex(owner_id: str, meta: dict[str, Any]) -> None:
    upsert_index_entry(
        owner_id,
        {
            "doc_id": meta["doc_id"],
            "title": meta.get("title") or "",
            "material_kind": meta.get("material_kind") or "third_party",
            "media_type": meta.get("media_type") or "note",
            "page": meta.get("page") or "unknown",
            "text": meta.get("index_text") or meta.get("title") or "",
            "project_id": meta.get("project_id") or "",
            "tags": list(meta.get("tags") or []),
        },
    )


def _safe_filename(filename: str) -> str:
    name = Path(filename or "file").name
    cleaned = _SAFE_NAME.sub("_", name).strip("._") or "file"
    return cleaned[:180]


def _public_meta(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_id": item["doc_id"],
        "material_kind": item["material_kind"],
        "media_type": item["media_type"],
        "title": item["title"],
        "byte_size": item.get("byte_size", 0),
        "page": item.get("page", "unknown"),
        "project_id": item.get("project_id") or "",
        "tags": list(item.get("tags") or []),
        "created_at": item.get("created_at", ""),
    }
