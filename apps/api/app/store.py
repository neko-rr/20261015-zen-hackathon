"""プロセス内の履歴。再起動で消える。本番は Firestore に置き換える。owner 単位で隔離する。"""

from threading import Lock
from uuid import uuid4

_lock = Lock()
_photos: dict[str, dict] = {}


def create_photo(objects: list[dict], owner_id: str, pose: dict | None = None) -> str:
    if not owner_id.strip():
        raise ValueError("owner_id is required")
    photo_id = str(uuid4())
    with _lock:
        _photos[photo_id] = {
            "owner_id": owner_id,
            "objects": objects,
            "pose": pose or {"landmarks": [], "edges": [], "muscles": []},
            "lookups": [],
            "questions": [],
        }
    return photo_id


def get_photo(photo_id: str, owner_id: str) -> dict | None:
    """所有者以外には存在を明かさない。"""
    if not photo_id.strip() or not owner_id.strip():
        return None
    with _lock:
        photo = _photos.get(photo_id)
        if photo is None:
            return None
        if photo.get("owner_id") != owner_id:
            return None
        pose = photo.get("pose") or {"landmarks": [], "edges": [], "muscles": []}
        return {
            "owner_id": photo["owner_id"],
            "objects": list(photo["objects"]),
            "pose": {
                "landmarks": list(pose.get("landmarks") or []),
                "edges": list(pose.get("edges") or []),
                "muscles": list(pose.get("muscles") or []),
            },
            "lookups": list(photo["lookups"]),
            "questions": list(photo.get("questions", [])),
        }


def add_lookup(photo_id: str, owner_id: str, lookup: dict) -> bool:
    with _lock:
        photo = _photos.get(photo_id)
        if photo is None or photo.get("owner_id") != owner_id:
            return False
        photo["lookups"].append(lookup)
        return True


def add_question(photo_id: str, owner_id: str, question: dict) -> bool:
    with _lock:
        photo = _photos.get(photo_id)
        if photo is None or photo.get("owner_id") != owner_id:
            return False
        photo.setdefault("questions", []).append(question)
        return True
