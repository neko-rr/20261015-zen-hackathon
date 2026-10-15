"""作業の記録。資料庫は人に1つ。案件は参照と権利の証拠。"""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.lookup import answer_question, cite_material
from app.main import app
from app.material_store import add_material
from app.project_store import create_project, get_project, note_photo
from app.settings import Settings


def _settings() -> Settings:
    return Settings(
        cors_origins=["http://127.0.0.1:3000"],
        gemini_model="test-model",
        cloud_project="",
        use_enterprise=False,
        session_signing_secret="test",
        session_cookie_secure=False,
    )


def test_chat_searches_whole_library_and_logs(monkeypatch) -> None:
    project = create_project("owner-log", "夏の場面")
    seen: dict[str, str] = {}

    def fake_retrieve(_owner: str, _query: str, limit: int = 4, project_id: str = "") -> list[dict]:
        del limit
        seen["project_id"] = project_id
        return [
            {
                "doc_id": "doc-sleeve",
                "title": "sleeve.md",
                "text": "袖",
                "material_kind": "own_work",
                "project_id": "other-shelf",
            }
        ]

    monkeypatch.setattr("app.lookup.retrieve", fake_retrieve)
    monkeypatch.setattr("app.lookup._library_answer", lambda *_args, **_kwargs: "袖です。")
    result = answer_question(
        _settings(),
        "シャツ",
        "袖は？",
        owner_id="owner-log",
        project_id=project["project_id"],
    )
    assert seen["project_id"] == ""
    assert result["materials"][0]["doc_id"] == "doc-sleeve"
    saved = get_project("owner-log", project["project_id"])
    assert saved is not None
    assert saved["library_calls"][0]["via"] == "chat"
    assert saved["library_calls"][0]["doc_id"] == "doc-sleeve"
    assert saved["prompts"][0]["message"] == "袖は？"
    assert saved["prompts"][0]["answer"] == "袖です。"
    assert get_project("someone-else", project["project_id"]) is None


def test_citation_log_keeps_rights_snapshot(monkeypatch) -> None:
    owner = f"owner-cite-{uuid4().hex[:8]}"
    project = create_project(owner, "キャラA")
    add_material(
        owner,
        {
            "doc_id": "doc-rights",
            "material_kind": "third_party",
            "media_type": "note",
            "title": "ref.md",
            "byte_size": 8,
            "page": "unknown",
            "project_id": "",
            "tags": [],
            "created_at": "2026-10-15T00:00:00+00:00",
            "index_text": "題名: 夏の袖\n",
        },
    )

    def fake_web(_settings, _term):
        return (
            {
                "summary": "出典",
                "sources": [
                    {
                        "url": "https://example.com/sleeve",
                        "title": "夏の袖",
                        "material_kind": "web",
                        "license": "CC BY",
                        "copyright": "著者",
                        "created": "2020",
                    }
                ],
                "search_suggestions_html": "",
            },
            False,
        )

    monkeypatch.setattr("app.lookup._web_for_label", fake_web)
    cite_material(_settings(), owner, "doc-rights", project_id=project["project_id"])
    saved = get_project(owner, project["project_id"])
    assert saved is not None
    row = saved["citations"][0]
    assert row["term"] == "夏の袖"
    assert row["sources"][0]["license"] == "CC BY"
    assert row["sources"][0]["copyright"] == "著者"
    assert row["cached"] is False


def test_library_open_is_owner_scoped() -> None:
    user = TestClient(app)
    name = f"e{uuid4().hex[:12]}"
    assert user.post("/accounts", json={"username": name, "password": "long-password"}).status_code == 200
    project_id = user.post("/projects", json={"name": "記録"}).json()["project"]["project_id"]
    uploaded = user.post(
        "/materials",
        params={"material_kind": "own_work"},
        files=[("files", ("note.md", b"sleeve note", "text/markdown"))],
    )
    doc_id = uploaded.json()["materials"][0]["doc_id"]
    noted = user.post(f"/projects/{project_id}/library-calls", json={"doc_id": doc_id})
    assert noted.status_code == 200
    assert noted.json()["project"]["library_calls"][0]["via"] == "open"

    other = TestClient(app)
    other.post("/accounts", json={"username": f"o{uuid4().hex[:12]}", "password": "long-password"})
    blocked = other.post(f"/projects/{project_id}/library-calls", json={"doc_id": doc_id})
    assert blocked.status_code == 400


def test_photo_notes_do_not_grow_without_limit() -> None:
    project = create_project("owner-cap", "上限")
    for index in range(45):
        note_photo("owner-cap", project["project_id"], f"photo-{index}")
    saved = get_project("owner-cap", project["project_id"])
    assert saved is not None
    assert len(saved["photos"]) == 40
    assert saved["photos"][-1]["photo_id"] == "photo-44"


def test_prompt_is_logged_when_library_is_empty(monkeypatch) -> None:
    project = create_project("owner-prompt", "プロンプト")
    monkeypatch.setattr("app.lookup.retrieve", lambda *_args, **_kwargs: [])
    answer_question(
        _settings(),
        "シャツ",
        "袖の重なりを思い出して",
        owner_id="owner-prompt",
        project_id=project["project_id"],
    )
    saved = get_project("owner-prompt", project["project_id"])
    assert saved is not None
    assert saved["prompts"][0]["message"] == "袖の重なりを思い出して"
    assert "手元の資料" in saved["prompts"][0]["answer"]


def test_memo_is_saved_for_that_owner_only() -> None:
    user = TestClient(app)
    assert user.post(
        "/accounts",
        json={"username": f"m{uuid4().hex[:12]}", "password": "long-password"},
    ).status_code == 200
    project_id = user.post("/projects", json={"name": "メモ"}).json()["project"]["project_id"]
    saved = user.patch(f"/projects/{project_id}", json={"memo": "# 袖\n\n- 左が前"})
    assert saved.status_code == 200
    assert saved.json()["project"]["memo"].startswith("# 袖")

    other = TestClient(app)
    other.post("/accounts", json={"username": f"n{uuid4().hex[:12]}", "password": "long-password"})
    blocked = other.patch(f"/projects/{project_id}", json={"memo": "他人のメモ"})
    assert blocked.status_code == 400
    assert get_project_memo(user, project_id) == "# 袖\n\n- 左が前"


def get_project_memo(user: TestClient, project_id: str) -> str:
    listed = user.get("/projects")
    assert listed.status_code == 200
    for item in listed.json()["projects"]:
        if item["project_id"] == project_id:
            return str(item["memo"])
    raise AssertionError("project missing")
