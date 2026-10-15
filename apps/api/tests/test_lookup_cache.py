"""同じ呼び方のウェブ検索は1回だけ。資料庫は出典に混ぜない。"""

from app.lookup import clear_lookup_cache, lookup_object
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


def test_same_label_uses_one_web_search(monkeypatch) -> None:
    clear_lookup_cache()
    calls = {"search": 0}

    def fake_search(_settings: Settings, _prompt: str) -> tuple[str, list[dict[str, str]], str]:
        calls["search"] += 1
        return (
            "駅の説明",
            [{"url": "https://example.com/a", "title": "Example", "text": "CC-BY"}],
            "",
        )

    monkeypatch.setattr("app.lookup._search", fake_search)
    monkeypatch.setattr("app.lookup.search_rights", lambda _label: [])

    first = lookup_object(_settings(), "駅のホーム", owner_id="owner-a", query="駅のホーム")
    second = lookup_object(_settings(), "  駅のホーム ", owner_id="owner-b", query="駅のホーム")

    assert calls["search"] == 1
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["summary"] == "駅の説明"
    assert all(not str(item["url"]).startswith("library://") for item in second["sources"])
    assert all(not str(item["url"]).startswith("material://") for item in first["sources"])


def test_generic_label_does_not_search_the_web(monkeypatch) -> None:
    clear_lookup_cache()
    calls = {"search": 0}

    def fake_search(_settings: Settings, _prompt: str) -> tuple[str, list[dict[str, str]], str]:
        calls["search"] += 1
        return ("", [], "")

    monkeypatch.setattr("app.lookup._search", fake_search)
    monkeypatch.setattr("app.lookup.search_rights", lambda _label: (_ for _ in ()).throw(AssertionError("rights")))

    result = lookup_object(_settings(), "成人の女性、白いシャツ", owner_id="owner-a")
    assert calls["search"] == 0
    assert result["search_skipped"] is True
    assert result["sources"] == []
    assert "題名" in result["summary"]
