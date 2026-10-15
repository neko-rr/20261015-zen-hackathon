"""写真・資料・案件のメタデータ。GCS_BUCKET があるとき Firestore に残す。"""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.cloud_config import gcp_project
from app.errors import AppError, system_error

logger = logging.getLogger(__name__)

_client = None
_MAX_DOC_BYTES = 900_000


def save_photo(owner_id: str, photo_id: str, record: dict[str, Any]) -> None:
    _set(_photo_ref(owner_id, photo_id), record)


def delete_photo(owner_id: str, photo_id: str) -> None:
    ref = _photo_ref(owner_id, photo_id)
    if _load_owned(ref, owner_id) is None:
        return
    _delete(ref)


def load_photo(owner_id: str, photo_id: str) -> dict[str, Any] | None:
    return _load_owned(_photo_ref(owner_id, photo_id), owner_id)


def change_photo(
    owner_id: str,
    photo_id: str,
    mutator: Callable[[dict[str, Any]], None],
) -> bool:
    return _change(_photo_ref(owner_id, photo_id), owner_id, mutator)


def save_material(owner_id: str, doc_id: str, record: dict[str, Any]) -> None:
    _set(_material_ref(owner_id, doc_id), record)


def load_material(owner_id: str, doc_id: str) -> dict[str, Any] | None:
    return _load_owned(_material_ref(owner_id, doc_id), owner_id)


def list_material_records(owner_id: str) -> list[dict[str, Any]]:
    return _list(_materials(owner_id))


def delete_material_record(owner_id: str, doc_id: str) -> dict[str, Any] | None:
    ref = _material_ref(owner_id, doc_id)
    current = _load_owned(ref, owner_id)
    if current is None:
        return None
    _delete(ref)
    return current


def save_project(owner_id: str, project_id: str, record: dict[str, Any]) -> None:
    _set(_project_ref(owner_id, project_id), record)


def load_project(owner_id: str, project_id: str) -> dict[str, Any] | None:
    return _load_owned(_project_ref(owner_id, project_id), owner_id)


def list_project_records(owner_id: str) -> list[dict[str, Any]]:
    return _list(_projects(owner_id))


def delete_project_record(owner_id: str, project_id: str) -> bool:
    ref = _project_ref(owner_id, project_id)
    if _load_owned(ref, owner_id) is None:
        return False
    _delete(ref)
    return True


def _photo_ref(owner_id: str, photo_id: str):
    return _owner(owner_id).collection("photos").document(photo_id)


def _material_ref(owner_id: str, doc_id: str):
    return _materials(owner_id).document(doc_id)


def _project_ref(owner_id: str, project_id: str):
    return _projects(owner_id).document(project_id)


def _materials(owner_id: str):
    return _owner(owner_id).collection("materials")


def _projects(owner_id: str):
    return _owner(owner_id).collection("projects")


def _owner(owner_id: str):
    if not owner_id.strip():
        raise system_error("storage_failed", "保存先を決められませんでした。")
    return _db().collection("owners").document(owner_id)


def _set(ref, record: dict[str, Any]) -> None:
    payload = dict(record)
    _guard_size(payload)
    try:
        ref.set(payload)
    except Exception as exc:
        logger.exception("firestore write failed")
        raise system_error("storage_failed", "履歴の保存に失敗しました。") from exc


def _load_owned(ref, owner_id: str) -> dict[str, Any] | None:
    try:
        snap = ref.get()
    except Exception as exc:
        logger.exception("firestore read failed")
        raise system_error("storage_failed", "履歴の読み取りに失敗しました。") from exc
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    if data.get("owner_id") != owner_id:
        return None
    return data


def _list(collection) -> list[dict[str, Any]]:
    try:
        snaps = collection.stream()
        return [snap.to_dict() or {} for snap in snaps]
    except Exception as exc:
        logger.exception("firestore list failed")
        raise system_error("storage_failed", "履歴の読み取りに失敗しました。") from exc


def _delete(ref) -> None:
    try:
        ref.delete()
    except Exception as exc:
        logger.exception("firestore delete failed")
        raise system_error("storage_failed", "履歴の削除に失敗しました。") from exc


def _change(ref, owner_id: str, mutator: Callable[[dict[str, Any]], None]) -> bool:
    from google.cloud import firestore

    transaction = _db().transaction()

    @firestore.transactional
    def _apply(tx) -> bool:
        snap = ref.get(transaction=tx)
        if not snap.exists:
            return False
        data = snap.to_dict() or {}
        if data.get("owner_id") != owner_id:
            return False
        mutator(data)
        _guard_size(data)
        tx.set(ref, data)
        return True

    try:
        return bool(_apply(transaction))
    except AppError:
        raise
    except Exception as exc:
        logger.exception("firestore update failed")
        raise system_error("storage_failed", "履歴の保存に失敗しました。") from exc


def save_file_search_store(owner_id: str, store_name: str) -> None:
    if not owner_id.strip() or not store_name.startswith("fileSearchStores/"):
        raise system_error("storage_failed", "保存先を決められませんでした。")
    try:
        _owner(owner_id).set(
            {"owner_id": owner_id, "file_search_store": store_name},
            merge=True,
        )
    except Exception as exc:
        logger.exception("firestore file search store write failed")
        raise system_error("storage_failed", "履歴の保存に失敗しました。") from exc


def load_file_search_store(owner_id: str) -> str:
    if not owner_id.strip():
        return ""
    try:
        snap = _owner(owner_id).get()
    except Exception as exc:
        logger.exception("firestore file search store read failed")
        raise system_error("storage_failed", "履歴の読み取りに失敗しました。") from exc
    if not snap.exists:
        return ""
    data = snap.to_dict() or {}
    if data.get("owner_id") not in (None, "", owner_id):
        return ""
    name = str(data.get("file_search_store") or "")
    if not name.startswith("fileSearchStores/"):
        return ""
    return name


def load_citation_refresh_days(owner_id: str) -> int | None:
    if not owner_id.strip():
        return None
    try:
        snap = _owner(owner_id).get()
    except Exception as exc:
        logger.exception("firestore preference read failed")
        raise system_error("storage_failed", "履歴の読み取りに失敗しました。") from exc
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    if data.get("owner_id") not in (None, "", owner_id):
        return None
    raw = data.get("citation_refresh_days")
    if isinstance(raw, int) and not isinstance(raw, bool) and 1 <= raw <= 365:
        return raw
    return None


def load_preference_text(owner_id: str, field: str) -> str | None:
    if not owner_id.strip() or field not in {"locale", "theme_id"}:
        return None
    try:
        snap = _owner(owner_id).get()
    except Exception as exc:
        logger.exception("firestore preference read failed")
        raise system_error("storage_failed", "履歴の読み取りに失敗しました。") from exc
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    if data.get("owner_id") not in (None, "", owner_id):
        return None
    raw = data.get(field)
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw


def save_preference_text(owner_id: str, field: str, value: str) -> None:
    if not owner_id.strip() or field not in {"locale", "theme_id"}:
        raise system_error("storage_failed", "保存先を決められませんでした。")
    try:
        _owner(owner_id).set(
            {"owner_id": owner_id, field: value},
            merge=True,
        )
    except Exception as exc:
        logger.exception("firestore preference write failed")
        raise system_error("storage_failed", "履歴の保存に失敗しました。") from exc


def save_citation_refresh_days(owner_id: str, days: int) -> None:
    if not owner_id.strip():
        raise system_error("storage_failed", "保存先を決められませんでした。")
    try:
        _owner(owner_id).set(
            {"owner_id": owner_id, "citation_refresh_days": days},
            merge=True,
        )
    except Exception as exc:
        logger.exception("firestore preference write failed")
        raise system_error("storage_failed", "履歴の保存に失敗しました。") from exc


def save_account(username: str, record: dict[str, Any]) -> None:
    _set(_db().collection("accounts").document(username), record)


def load_account(username: str) -> dict[str, Any] | None:
    try:
        snap = _db().collection("accounts").document(username).get()
    except Exception as exc:
        logger.exception("firestore account read failed")
        raise system_error("storage_failed", "アカウントの読み取りに失敗しました。") from exc
    if not snap.exists:
        return None
    return snap.to_dict() or {}


def find_account_username(owner_id: str) -> str:
    try:
        snaps = (
            _db()
            .collection("accounts")
            .where("owner_id", "==", owner_id)
            .limit(1)
            .stream()
        )
        for snap in snaps:
            data = snap.to_dict() or {}
            return str(data.get("username") or "")
    except Exception as exc:
        logger.exception("firestore account lookup failed")
        raise system_error("storage_failed", "アカウントの読み取りに失敗しました。") from exc
    return ""


def _guard_size(record: dict[str, Any]) -> None:
    import json

    raw = json.dumps(record, ensure_ascii=False, default=str)
    if len(raw.encode("utf-8")) > _MAX_DOC_BYTES:
        raise system_error("storage_failed", "履歴が保存できる大きさを超えています。")


def _db():
    global _client
    if _client is not None:
        return _client
    from google.cloud import firestore

    project = gcp_project() or None
    try:
        _client = firestore.Client(project=project)
    except Exception as exc:
        logger.exception("firestore client failed")
        raise system_error("storage_failed", "履歴の保存に失敗しました。") from exc
    return _client
