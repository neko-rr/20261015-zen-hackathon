"""プロセス内の履歴。再起動で消える。本番は Firestore に置き換える。"""

from threading import Lock
from uuid import uuid4

_lock = Lock()
_photos: dict[str, dict] = {}


def create_photo(objects: list[dict]) -> str:
    photo_id = str(uuid4())
    with _lock:
        _photos[photo_id] = {"objects": objects, "lookups": []}
    return photo_id


def get_photo(photo_id: str) -> dict | None:
    with _lock:
        photo = _photos.get(photo_id)
        if photo is None:
            return None
        return {
            "objects": list(photo["objects"]),
            "lookups": list(photo["lookups"]),
        }


def add_lookup(photo_id: str, lookup: dict) -> None:
    with _lock:
        photo = _photos.get(photo_id)
        if photo is None:
            return
        photo["lookups"].append(lookup)
