"""アカウントは owner が分かれる。審査用 reviewer は一般登録できない。"""

from fastapi.testclient import TestClient

from app.accounts import DEMO_PASSWORD, DEMO_USERNAME
from app.main import app

client = TestClient(app)


def test_register_login_keeps_the_same_owner() -> None:
    created = client.post(
        "/accounts",
        json={"username": "painter_a", "password": "long-password"},
    )
    assert created.status_code == 200
    owner_id = created.json()["session_id"]
    assert created.json()["kind"] == "account"

    again = client.post(
        "/accounts/login",
        json={"username": "painter_a", "password": "long-password"},
    )
    assert again.status_code == 200
    assert again.json()["session_id"] == owner_id

    me = client.get("/sessions/me")
    assert me.status_code == 200
    assert me.json()["username"] == "painter_a"


def test_two_accounts_do_not_share_photos() -> None:
    from app.store import create_photo, get_photo

    first = TestClient(app)
    second = TestClient(app)
    owner_a = first.post(
        "/accounts",
        json={"username": "painter_b", "password": "long-password"},
    ).json()["session_id"]
    owner_b = second.post(
        "/accounts",
        json={"username": "painter_c", "password": "long-password"},
    ).json()["session_id"]
    assert owner_a != owner_b

    photo_id = create_photo(
        [{"object_id": "obj_1", "label": "cat", "kind": "animal", "is_primary": True}],
        owner_a,
    )
    assert get_photo(photo_id, owner_a) is not None
    assert get_photo(photo_id, owner_b) is None
    denied = second.get(f"/photos/{photo_id}")
    assert denied.status_code == 400
    assert denied.json()["error"]["code"] == "object_not_found"


def test_suggestion_is_unused_and_can_be_registered() -> None:
    suggested = client.post("/accounts/suggestions")
    assert suggested.status_code == 200
    name = suggested.json()["username"]
    assert name == name.lower()
    assert name != "reviewer"

    created = client.post(
        "/accounts",
        json={"username": name, "password": "long-password"},
    )
    assert created.status_code == 200

    another = client.post("/accounts/suggestions")
    assert another.status_code == 200
    assert another.json()["username"] != name


def test_same_username_is_rejected_regardless_of_case() -> None:
    created = client.post(
        "/accounts",
        json={"username": "case_user", "password": "long-password"},
    )
    assert created.status_code == 200
    taken = client.post(
        "/accounts",
        json={"username": "Case_User", "password": "another-password"},
    )
    assert taken.status_code == 400
    assert taken.json()["error"]["code"] == "username_taken"


def test_logout_ends_the_session() -> None:
    alone = TestClient(app)
    created = alone.post(
        "/accounts",
        json={"username": "painter_out", "password": "long-password"},
    )
    assert created.status_code == 200
    assert alone.get("/sessions/me").status_code == 200
    gone = alone.post("/accounts/logout")
    assert gone.status_code == 200
    assert alone.get("/sessions/me").status_code == 401


def test_login_failure_hides_which_field_was_wrong() -> None:
    bad = client.post(
        "/accounts/login",
        json={"username": "painter_a", "password": "wrong-password"},
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "invalid_login"


def test_reviewer_login_and_register_blocked() -> None:
    logged = client.post(
        "/accounts/login",
        json={"username": DEMO_USERNAME, "password": DEMO_PASSWORD},
    )
    assert logged.status_code == 200
    assert logged.json()["username"] == DEMO_USERNAME

    taken = client.post(
        "/accounts",
        json={"username": DEMO_USERNAME, "password": "another-password"},
    )
    assert taken.status_code == 400
    assert taken.json()["error"]["code"] == "username_taken"
