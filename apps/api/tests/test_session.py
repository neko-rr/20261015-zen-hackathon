"""ゲストの新規 ID は発行しない。保存はアカウントだけ。"""

from fastapi.testclient import TestClient

from app.main import app
from app.store import create_photo, get_photo

client = TestClient(app)


def test_guest_session_is_not_issued() -> None:
    created = client.post("/sessions")
    assert created.status_code == 401
    assert created.json()["error"]["code"] == "session_required"

    me = client.get("/sessions/me")
    assert me.status_code == 401


def test_photo_isolation_between_accounts() -> None:
    first = TestClient(app)
    second = TestClient(app)
    owner_a = first.post(
        "/accounts",
        json={"username": "iso_a", "password": "long-password"},
    ).json()["session_id"]
    owner_b = second.post(
        "/accounts",
        json={"username": "iso_b", "password": "long-password"},
    ).json()["session_id"]
    assert owner_a != owner_b

    photo_id = create_photo(
        [
            {
                "object_id": "obj_1",
                "label": "cat",
                "kind": "animal",
                "is_primary": True,
                "box": None,
                "joints": [],
                "muscles": [],
                "contour": [],
            }
        ],
        owner_a,
    )
    assert get_photo(photo_id, owner_a) is not None
    assert get_photo(photo_id, owner_b) is None

    denied = second.get(f"/photos/{photo_id}/lookups")
    assert denied.status_code == 400
    assert denied.json()["error"]["code"] == "object_not_found"

    allowed = first.get(f"/photos/{photo_id}/lookups")
    assert allowed.status_code == 200
    assert allowed.json() == {"lookups": []}


def test_delete_photo_drops_owner_record_and_project_note() -> None:
    from uuid import uuid4

    from app.project_store import create_project, get_project, note_photo

    owner = TestClient(app)
    other = TestClient(app)
    suffix = uuid4().hex[:8]
    owner_id = owner.post(
        "/accounts",
        json={"username": f"del_{suffix}", "password": "long-password"},
    ).json()["session_id"]
    other.post(
        "/accounts",
        json={"username": f"keep_{suffix}", "password": "long-password"},
    )
    photo_id = create_photo(
        [
            {
                "object_id": "obj_1",
                "label": "person",
                "kind": "person",
                "is_primary": True,
                "box": None,
                "joints": [],
                "muscles": [],
                "contour": [],
            }
        ],
        owner_id,
    )
    project = create_project(owner_id, "demo")
    note_photo(owner_id, project["project_id"], photo_id)

    removed = owner.delete(f"/photos/{photo_id}")
    assert removed.status_code == 200
    assert removed.json() == {"ok": True}
    assert get_photo(photo_id, owner_id) is None
    saved = get_project(owner_id, project["project_id"])
    assert saved is not None
    assert saved["photos"] == []

    again = owner.delete(f"/photos/{photo_id}")
    assert again.status_code == 200

    kept_id = create_photo(
        [
            {
                "object_id": "obj_1",
                "label": "person",
                "kind": "person",
                "is_primary": True,
                "box": None,
                "joints": [],
                "muscles": [],
                "contour": [],
            }
        ],
        owner_id,
    )
    denied = other.delete(f"/photos/{kept_id}")
    assert denied.status_code == 200
    assert get_photo(kept_id, owner_id) is not None
