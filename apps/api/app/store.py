"""写真と出典履歴。GCS_BUCKET があるときは Firestore。無いときはプロセス内。"""

from threading import Lock
from uuid import uuid4

from app.cloud_config import cloud_persistence_enabled

_lock = Lock()
_photos: dict[str, dict] = {}


def create_photo(
    objects: list[dict],
    owner_id: str,
    pose: dict | None = None,
    labels_pending: bool = False,
    file_facts: dict | None = None,
    web_pages: list | None = None,
    web_images: list | None = None,
    image: bytes | None = None,
    content_type: str | None = None,
) -> str:
    if not owner_id.strip():
        raise ValueError("owner_id is required")
    photo_id = str(uuid4())
    record = {
        "owner_id": owner_id,
        "objects": objects,
        "pose": _copy_pose(pose),
        "lookups": [],
        "questions": [],
        "labels_pending": labels_pending,
        "file_facts": dict(file_facts or {}),
        "web_pages": _copy_pages(web_pages),
        "web_images": _copy_images(web_images),
        "content_type": content_type or "",
    }
    if cloud_persistence_enabled():
        from app.object_store import photo_object_name, put_bytes
        from app.record_store import delete_photo, save_photo

        save_photo(owner_id, photo_id, record)
        if image:
            try:
                put_bytes(
                    photo_object_name(owner_id, photo_id),
                    image,
                    content_type or "application/octet-stream",
                )
            except Exception:
                delete_photo(owner_id, photo_id)
                raise
        return photo_id
    with _lock:
        _photos[photo_id] = record
    return photo_id


def get_photo(photo_id: str, owner_id: str) -> dict | None:
    """所有者以外には存在を明かさない。"""
    if not photo_id.strip() or not owner_id.strip():
        return None
    if cloud_persistence_enabled():
        from app.record_store import load_photo

        photo = load_photo(owner_id, photo_id)
        if photo is None:
            return None
        return _view(photo)
    with _lock:
        photo = _photos.get(photo_id)
        if photo is None:
            return None
        if photo.get("owner_id") != owner_id:
            return None
        return _view(photo)


def finish_labels(photo_id: str, owner_id: str, objects: list[dict]) -> bool:
    """呼び方だけを差し替える。姿勢は残す。"""
    if not photo_id.strip() or not owner_id.strip():
        return False
    if cloud_persistence_enabled():
        from app.record_store import change_photo

        def _apply(photo: dict) -> None:
            photo["objects"] = list(objects)
            photo["labels_pending"] = False

        return change_photo(owner_id, photo_id, _apply)
    with _lock:
        photo = _photos.get(photo_id)
        if photo is None or photo.get("owner_id") != owner_id:
            return False
        photo["objects"] = list(objects)
        photo["labels_pending"] = False
        return True


def _copy_pages(pages: list | None) -> list[dict[str, str]]:
    copied: list[dict[str, str]] = []
    for item in pages or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        if not url.startswith("https://"):
            continue
        copied.append({"url": url, "title": str(item.get("title") or url)})
    return copied


def _copy_images(images: list | None) -> list[dict[str, str]]:
    copied: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in images or []:
        if not isinstance(item, dict) or len(copied) >= 8:
            continue
        url = str(item.get("url") or "")
        match = str(item.get("match") or "")
        if not url.startswith("https://") or url in seen or match not in ("full", "partial", "similar"):
            continue
        page_url = str(item.get("page_url") or "")
        seen.add(url)
        copied.append(
            {
                "url": url,
                "page_url": page_url if page_url.startswith("https://") else "",
                "match": match,
            }
        )
    return copied


def _copy_pose(pose: dict | None) -> dict:
    source = pose or {}
    return {
        "landmarks": list(source.get("landmarks") or []),
        "edges": list(source.get("edges") or []),
        "muscles": list(source.get("muscles") or []),
        "hands": list(source.get("hands") or []),
        "mannequin": _copy_mannequin(source.get("mannequin")),
        "people": [_copy_person(item) for item in source.get("people") or [] if isinstance(item, dict)],
    }


def _copy_person(person: dict) -> dict:
    return {
        "object_id": str(person.get("object_id") or ""),
        "landmarks": list(person.get("landmarks") or []),
        "edges": list(person.get("edges") or []),
        "muscles": list(person.get("muscles") or []),
        "hands": list(person.get("hands") or []),
        "mannequin": _copy_mannequin(person.get("mannequin")),
    }


def _copy_mannequin(mannequin: dict | None) -> dict:
    source = mannequin or {}
    return {
        "joints": list(source.get("joints") or []),
        "bones": list(source.get("bones") or []),
        "head": source.get("head"),
        "aspect": float(source.get("aspect") or 1),
    }


def add_lookup(photo_id: str, owner_id: str, lookup: dict) -> bool:
    return _append(photo_id, owner_id, "lookups", lookup)


def add_question(photo_id: str, owner_id: str, question: dict) -> bool:
    return _append(photo_id, owner_id, "questions", question)


def _append(photo_id: str, owner_id: str, field: str, item: dict) -> bool:
    if cloud_persistence_enabled():
        from app.record_store import change_photo

        def _apply(photo: dict) -> None:
            photo.setdefault(field, []).append(item)

        return change_photo(owner_id, photo_id, _apply)
    with _lock:
        photo = _photos.get(photo_id)
        if photo is None or photo.get("owner_id") != owner_id:
            return False
        photo.setdefault(field, []).append(item)
        return True


def _view(photo: dict) -> dict:
    return {
        "owner_id": photo["owner_id"],
        "objects": list(photo["objects"]),
        "pose": _copy_pose(photo.get("pose")),
        "lookups": list(photo.get("lookups") or []),
        "questions": list(photo.get("questions") or []),
        "labels_pending": bool(photo.get("labels_pending")),
        "file_facts": dict(photo.get("file_facts") or {}),
        "web_pages": _copy_pages(photo.get("web_pages")),
        "web_images": _copy_images(photo.get("web_images")),
    }
