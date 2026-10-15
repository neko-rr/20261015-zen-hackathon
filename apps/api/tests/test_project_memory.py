"""作業メモリは、その人のメモとログだけを質問で拾う。"""

from app.lookup import answer_question
from app.project_memory import retrieve_project_memory
from app.project_store import create_project, save_memo
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


def test_memory_prefers_the_selected_project_and_stays_with_the_owner() -> None:
    owner = "owner-memory"
    selected = create_project(owner, "夏の場面")
    other = create_project(owner, "別の場面")
    save_memo(owner, selected["project_id"], "左の袖が前に出る。")
    save_memo(owner, other["project_id"], "左の袖が前に出る。別作業。")
    stranger = create_project("owner-other", "他人")
    save_memo("owner-other", stranger["project_id"], "左の袖が前に出る。他人のメモ。")

    hits = retrieve_project_memory(owner, "左の袖", selected["project_id"])
    assert hits
    assert hits[0]["project_id"] == selected["project_id"]
    assert hits[0]["source"] == "memo"
    assert all(item["project_id"] != stranger["project_id"] for item in hits)
    assert "他人" not in hits[0]["text"]


def test_chat_uses_recent_turns_and_memory_without_web(monkeypatch) -> None:
    owner = "owner-context"
    project = create_project(owner, "記録")
    save_memo(owner, project["project_id"], "色は藍色。袖は重ねる。")
    seen: dict[str, object] = {}

    def fail_search(*_args, **_kwargs):
        raise AssertionError("web search")

    def capture(*args, **_kwargs):
        seen["dialogue"] = args[5]
        seen["memory"] = args[4]
        return "藍色です。"

    monkeypatch.setattr("app.lookup._search", fail_search)
    monkeypatch.setattr("app.lookup.retrieve", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.lookup._library_answer", capture)
    history = [{"message": f"質問{index}", "answer": f"返答{index}"} for index in range(8)]
    result = answer_question(
        _settings(),
        "着物",
        "袖は重ねる",
        owner_id=owner,
        project_id=project["project_id"],
        history=history,
    )
    dialogue = seen["dialogue"]
    assert isinstance(dialogue, list)
    assert len(dialogue) == 6
    assert dialogue[0]["message"] == "質問2"
    memory = seen["memory"]
    assert isinstance(memory, list)
    assert memory[0]["text"].startswith("色は藍色")
    assert result["answer"] == "藍色です。"
    assert result["sources"] == []
    assert result["memory"][0]["project_name"] == "記録"


def test_memo_request_appends_and_keeps_existing_text(monkeypatch) -> None:
    owner = "owner-memo-write"
    project = create_project(owner, "夏")
    save_memo(owner, project["project_id"], "手書きの袖。")

    def fail_search(*_args, **_kwargs):
        raise AssertionError("web search")

    monkeypatch.setattr("app.lookup._search", fail_search)
    monkeypatch.setattr("app.lookup.retrieve", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.lookup._compose_memo", lambda *_args, **_kwargs: "- 袖は重ねる。")
    result = answer_question(
        _settings(),
        "着物",
        "これをメモにして",
        owner_id=owner,
        project_id=project["project_id"],
        history=[{"message": "袖は？", "answer": "重ねる。"}],
    )
    from app.project_store import get_project

    saved = get_project(owner, project["project_id"])
    assert saved is not None
    assert saved["memo"].startswith("手書きの袖。")
    assert "## チャットからのメモ" in saved["memo"]
    assert "袖は重ねる。" in saved["memo"]
    assert result["memo_updated"] is True


def test_asking_about_a_memo_does_not_rewrite_it(monkeypatch) -> None:
    owner = "owner-memo-read"
    project = create_project(owner, "夏")
    save_memo(owner, project["project_id"], "手書きの袖。")

    def fail_compose(*_args, **_kwargs):
        raise AssertionError("memo write")

    monkeypatch.setattr("app.lookup._compose_memo", fail_compose)
    monkeypatch.setattr("app.lookup.retrieve", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.lookup._library_answer", lambda *_args, **_kwargs: "手書きです。")
    result = answer_question(
        _settings(),
        "着物",
        "メモに何て書いた？",
        owner_id=owner,
        project_id=project["project_id"],
        history=[{"message": "袖は？", "answer": "重ねる。"}],
    )
    from app.project_store import get_project

    saved = get_project(owner, project["project_id"])
    assert saved is not None
    assert saved["memo"] == "手書きの袖。"
    assert result["memo_updated"] is False


def test_memo_request_without_project_does_not_save(monkeypatch) -> None:
    monkeypatch.setattr("app.lookup.retrieve", lambda *_args, **_kwargs: [])
    result = answer_question(
        _settings(),
        "着物",
        "メモにして",
        owner_id="owner-no-project",
        history=[{"message": "袖は？", "answer": "重ねる。"}],
    )
    assert result["memo_updated"] is False
    assert "作業の記録" in result["answer"]
