"""写真と手元資料の実体。GCS_BUCKET があるときだけ Cloud Storage に書く。"""

from __future__ import annotations

import logging

from app.cloud_config import gcs_bucket, gcp_project
from app.errors import system_error

logger = logging.getLogger(__name__)

_client = None


def photo_object_name(owner_id: str, photo_id: str) -> str:
    return f"owners/{_segment(owner_id)}/photos/{_segment(photo_id)}/original"


def material_prefix(owner_id: str, material_kind: str, doc_id: str) -> str:
    return (
        f"owners/{_segment(owner_id)}/materials/"
        f"{_segment(material_kind)}/{_segment(doc_id)}/"
    )


def material_object_name(
    owner_id: str,
    material_kind: str,
    doc_id: str,
    filename: str,
) -> str:
    return material_prefix(owner_id, material_kind, doc_id) + _filename(filename)


def put_bytes(object_name: str, data: bytes, content_type: str) -> None:
    if not object_name or data is None:
        raise system_error("storage_failed", "ファイルの保存に失敗しました。")
    try:
        blob = _bucket().blob(object_name)
        blob.cache_control = "private, max-age=0"
        blob.upload_from_string(data, content_type=content_type or "application/octet-stream")
    except Exception as exc:
        logger.exception("gcs write failed")
        raise system_error("storage_failed", "ファイルの保存に失敗しました。") from exc


def delete_prefix(prefix: str) -> None:
    if not prefix.startswith("owners/"):
        raise system_error("storage_failed", "ファイルの削除に失敗しました。")
    try:
        bucket = _bucket()
        for blob in bucket.list_blobs(prefix=prefix):
            blob.delete()
    except Exception as exc:
        logger.exception("gcs delete failed")
        raise system_error("storage_failed", "ファイルの削除に失敗しました。") from exc


def _segment(value: str) -> str:
    text = (value or "").strip()
    if not text or "/" in text or "\\" in text or ".." in text:
        raise system_error("storage_failed", "保存先を決められませんでした。")
    return text


def _filename(value: str) -> str:
    text = (value or "").strip().replace("\\", "/")
    name = text.split("/")[-1]
    if not name or name in {".", ".."}:
        raise system_error("storage_failed", "保存先を決められませんでした。")
    return name


def _bucket():
    name = gcs_bucket()
    if not name:
        raise system_error("config_missing", "GCS_BUCKET が未設定です。")
    try:
        return _storage_client().bucket(name)
    except Exception as exc:
        logger.exception("gcs client failed")
        raise system_error("storage_failed", "ファイルの保存に失敗しました。") from exc


def _storage_client():
    global _client
    if _client is not None:
        return _client
    from google.cloud import storage

    project = gcp_project() or None
    _client = storage.Client(project=project)
    return _client
