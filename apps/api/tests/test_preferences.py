"""言語とテーマ色はアカウントごとに残る。"""

from fastapi.testclient import TestClient

from app.main import app


def test_locale_and_theme_stay_with_the_account() -> None:
    first = TestClient(app)
    second = TestClient(app)
    assert (
        first.post(
            "/accounts",
            json={"username": "theme_user_a", "password": "long-password"},
        ).status_code
        == 200
    )
    assert (
        second.post(
            "/accounts",
            json={"username": "theme_user_b", "password": "long-password"},
        ).status_code
        == 200
    )

    initial = first.get("/preferences")
    assert initial.status_code == 200
    assert initial.json()["locale"] == "ja"
    assert initial.json()["theme_id"] == "default"

    changed = first.patch("/preferences", json={"locale": "en", "theme_id": "sky-dark"})
    assert changed.status_code == 200
    assert changed.json()["locale"] == "en"
    assert changed.json()["theme_id"] == "sky-dark"
    assert changed.json()["citation_refresh_days"] == 30

    kept = first.patch("/preferences", json={"locale": "ja"})
    assert kept.status_code == 200
    assert kept.json()["locale"] == "ja"
    assert kept.json()["theme_id"] == "sky-dark"

    other = second.get("/preferences")
    assert other.status_code == 200
    assert other.json()["locale"] == "ja"
    assert other.json()["theme_id"] == "default"

    rejected = first.patch("/preferences", json={"theme_id": "not-a-theme"})
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "invalid_preference"
