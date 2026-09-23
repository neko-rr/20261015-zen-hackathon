"""セッション発行と owner 隔離。"""

from fastapi.testclient import TestClient

from app.main import app
from app.store import create_photo, get_photo

client = TestClient(app)


def test_session_mint_and_me() -> None:
    created = client.post("/sessions")
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    me = client.get("/sessions/me")
    assert me.status_code == 200
    assert me.json()["session_id"] == session_id

    again = client.post("/sessions")
    assert again.status_code == 200
    assert again.json()["session_id"] == session_id


def test_photo_isolation_between_sessions() -> None:
    first = TestClient(app)
    second = TestClient(app)

    a = first.post("/sessions").json()["session_id"]
    b = second.post("/sessions").json()["session_id"]
    assert a != b

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
        a,
    )
    assert get_photo(photo_id, a) is not None
    assert get_photo(photo_id, b) is None

    denied = second.get(f"/photos/{photo_id}/lookups")
    assert denied.status_code == 400
    assert denied.json()["error"]["code"] == "object_not_found"

    allowed = first.get(f"/photos/{photo_id}/lookups")
    assert allowed.status_code == 200
    assert allowed.json() == {"lookups": []}
