"""空質問は業務エラー。Gemini は呼ばない。セッション必須。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _start_session() -> None:
    response = client.post("/sessions")
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "session"
    assert body["session_id"]


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_question_requires_session() -> None:
    response = client.post(
        "/photos/missing/questions",
        json={"object_id": "obj_1", "message": "hello"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_required"


def test_question_empty_message() -> None:
    _start_session()
    response = client.post(
        "/photos/any-id/questions",
        json={"object_id": "obj_1", "message": "   "},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "empty_message"
    assert "error" in body
    assert "stack" not in body
