"""手元資料の登録と隔離。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _session() -> TestClient:
    started = TestClient(app)
    response = started.post("/sessions")
    assert response.status_code == 200
    return started


def test_material_requires_kind_and_session() -> None:
    response = client.post(
        "/materials",
        params={"material_kind": "own_work"},
        files=[("files", ("note.txt", b"hello cat", "text/plain"))],
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_required"


def test_material_upload_list_delete_and_reject_type() -> None:
    user = _session()
    ok = user.post(
        "/materials",
        params={"material_kind": "own_work"},
        files=[("files", ("setting.md", b"# cat ears\nshape notes", "text/markdown"))],
    )
    assert ok.status_code == 200
    body = ok.json()
    assert len(body["materials"]) == 1
    assert body["materials"][0]["material_kind"] == "own_work"
    assert body["materials"][0]["media_type"] == "note"
    doc_id = body["materials"][0]["doc_id"]

    listed = user.get("/materials")
    assert listed.status_code == 200
    assert len(listed.json()["materials"]) == 1

    bad = user.post(
        "/materials",
        params={"material_kind": "third_party"},
        files=[("files", ("shot.cr3", b"rawbytes", "application/octet-stream"))],
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "unsupported_material_type"

    gone = user.delete(f"/materials/{doc_id}")
    assert gone.status_code == 200
    assert user.get("/materials").json()["materials"] == []


def test_material_isolation_between_owners() -> None:
    a = _session()
    b = _session()
    created = a.post(
        "/materials",
        params={"material_kind": "third_party"},
        files=[("files", ("ref.txt", b"reference dog", "text/plain"))],
    )
    doc_id = created.json()["materials"][0]["doc_id"]
    assert b.get("/materials").json()["materials"] == []
    denied = b.delete(f"/materials/{doc_id}")
    assert denied.status_code == 400
    assert denied.json()["error"]["code"] == "object_not_found"


def test_own_work_verify_uses_own_claim_not_third_party_license(monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    from app.verify import verify_sources

    sources = verify_sources(
        "cat",
        [
            {
                "url": "material://doc1",
                "title": "mine.md",
                "text": "CC-BY should be ignored for own work",
                "material_kind": "own_work",
            }
        ],
        "ライセンスは？",
    )
    assert sources[0]["license"] == "own_claim"
    assert sources[0]["copyright"] == "own_claim"
    assert sources[0]["material_kind"] == "own_work"
    assert sources[0]["jev"]["license"] is None
    assert sources[0]["jev"]["copyright"] is None


def test_kind_aware_questions_include_material_kind() -> None:
    from app.verify import _group, _questions, _state

    class FakeNoul:
        def __init__(self, instructions: str) -> None:
            self.instructions = instructions

    sources = _group(
        [
            {
                "url": "material://a",
                "title": "own.md",
                "text": "my sketch notes about a cat",
                "material_kind": "own_work",
            },
            {
                "url": "https://example.com/b",
                "title": "web",
                "text": "CC-BY 4.0 Copyright 2020 Example about a cat",
                "material_kind": "web",
            },
        ]
    )
    state = _state("cat", sources, "形は？")
    assert state["sources"][0]["material_kind"] == "own_work"
    assert state["sources"][1]["material_kind"] == "web"
    assert "own work" in state["sources"][0]["material_kind_meaning"]

    questions = _questions(sources, FakeNoul, "形は？")
    assert "src_0_about" in questions
    assert "own_work" in questions["src_0_about"].instructions
    assert "src_0_license" not in questions
    assert "src_1_about" in questions
    assert "web" in questions["src_1_about"].instructions
    assert "src_1_license" in questions
    assert "third-party or web" in questions["src_1_license"].instructions
