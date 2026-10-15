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
