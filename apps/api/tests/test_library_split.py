"""チャットは資料庫だけ。出典検索は指定した題名だけを外へ出す。"""

from app.lookup import answer_question, cite_material
from app.material_store import add_material
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


def test_chat_opens_library_without_web(monkeypatch) -> None:
    def fail_search(*_args, **_kwargs):
        raise AssertionError("web search")

    monkeypatch.setattr("app.lookup._search", fail_search)
    monkeypatch.setattr(
        "app.lookup.retrieve",
        lambda *_args, **_kwargs: [
            {
                "doc_id": "doc-1",
                "title": "sleeve.md",
                "text": "袖の重なり",
                "material_kind": "own_work",
            }
        ],
    )
    monkeypatch.setattr("app.lookup._library_answer", lambda *_args, **_kwargs: "袖を見てください。")

    result = answer_question(_settings(), "白いシャツ", "袖は？", owner_id="owner-a")
    assert result["sources"] == []
    assert result["materials"][0]["doc_id"] == "doc-1"
    assert result["answer"] == "袖を見てください。"


def test_cite_material_uses_title_line_only(monkeypatch) -> None:
    add_material(
        "owner-cite",
        {
            "doc_id": "doc-cite",
            "material_kind": "third_party",
            "media_type": "note",
            "title": "note.md",
            "byte_size": 10,
            "page": "unknown",
            "project_id": "",
            "tags": [],
            "created_at": "2026-10-15T00:00:00+00:00",
            "index_text": "メモ本文は出さない\n題名: 夏の袖\n",
        },
    )
    seen: list[str] = []

    def fake_web(_settings, term):
        seen.append(term)
        return (
            {
                "summary": "出典",
                "sources": [{"url": "https://example.com/work", "title": "夏の袖", "material_kind": "web"}],
                "search_suggestions_html": "",
            },
            False,
        )

    monkeypatch.setattr("app.lookup._web_for_label", fake_web)
    result = cite_material(_settings(), "owner-cite", "doc-cite")
    assert seen == ["夏の袖"]
    assert result["search_skipped"] is False


def test_fresh_citation_does_not_search_again(monkeypatch) -> None:
    from datetime import datetime, timezone

    add_material(
        "owner-fresh",
        {
            "doc_id": "doc-fresh",
            "material_kind": "third_party",
            "media_type": "note",
            "title": "note.md",
            "byte_size": 8,
            "page": "unknown",
            "project_id": "",
            "tags": [],
            "created_at": "2026-10-15T00:00:00+00:00",
            "index_text": "題名: 夏の袖\n",
            "citation": {
                "term": "夏の袖",
                "searched_at": datetime.now(timezone.utc).isoformat(),
                "summary": "保存済み",
                "sources": [{"url": "https://example.com/saved", "title": "保存", "material_kind": "web"}],
            },
        },
    )

    def fail_web(*_args, **_kwargs):
        raise AssertionError("web")

    monkeypatch.setattr("app.lookup._web_for_label", fail_web)
    result = cite_material(_settings(), "owner-fresh", "doc-fresh")
    assert result["cached"] is True
    assert result["searched_at"]
    assert result["sources"][0]["url"] == "https://example.com/saved"


def test_stale_citation_searches_again(monkeypatch) -> None:
    add_material(
        "owner-stale",
        {
            "doc_id": "doc-stale",
            "material_kind": "third_party",
            "media_type": "note",
            "title": "note.md",
            "byte_size": 8,
            "page": "unknown",
            "project_id": "",
            "tags": [],
            "created_at": "2026-10-15T00:00:00+00:00",
            "index_text": "題名: 夏の袖\n",
            "citation": {
                "term": "夏の袖",
                "searched_at": "2020-01-01T00:00:00+00:00",
                "summary": "古い",
                "sources": [],
            },
        },
    )
    monkeypatch.setattr(
        "app.lookup._web_for_label",
        lambda *_args, **_kwargs: (
            {
                "summary": "新しい出典",
                "sources": [{"url": "https://example.com/new", "title": "新", "material_kind": "web"}],
                "search_suggestions_html": "",
            },
            False,
        ),
    )
    result = cite_material(_settings(), "owner-stale", "doc-stale")
    assert result["cached"] is False
    assert result["summary"] == "新しい出典"


def test_refresh_days_are_per_owner() -> None:
    from app.errors import AppError
    from app.owner_prefs import citation_refresh_days, set_citation_refresh_days

    assert citation_refresh_days("owner-days-a") == 30
    assert set_citation_refresh_days("owner-days-a", 7) == 7
    assert citation_refresh_days("owner-days-a") == 7
    assert citation_refresh_days("owner-days-b") == 30
    try:
        set_citation_refresh_days("owner-days-a", 0)
    except AppError as exc:
        assert exc.code == "invalid_refresh"
    else:
        raise AssertionError("expected invalid_refresh")


def test_cite_material_skips_without_title(monkeypatch) -> None:
    add_material(
        "owner-cite",
        {
            "doc_id": "doc-plain",
            "material_kind": "own_work",
            "media_type": "note",
            "title": "plain.md",
            "byte_size": 4,
            "page": "unknown",
            "project_id": "",
            "tags": [],
            "created_at": "2026-10-15T00:00:00+00:00",
            "index_text": "袖のメモだけ",
        },
    )

    def fail_web(*_args, **_kwargs):
        raise AssertionError("web")

    monkeypatch.setattr("app.lookup._web_for_label", fail_web)
    result = cite_material(_settings(), "owner-cite", "doc-plain")
    assert result["search_skipped"] is True
    assert result["sources"] == []
