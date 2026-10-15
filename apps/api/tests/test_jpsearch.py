"""ジャパンサーチの権利コード。通信はしない。"""

from app.editor_assist import risk_level
from app.jpsearch import search_rights, sources_from_payload
from app.lookup import clear_lookup_cache, lookup_object
from app.settings import Settings


def test_sources_keep_official_rights_code_only() -> None:
    sources = sources_from_payload(
        {
            "list": [
                {
                    "id": "arc_books-Ebi0824",
                    "common": {
                        "id": "arc_books-Ebi0824",
                        "title": "北斎伝",
                        "contentsRightsType": "ccbyncsa",
                    },
                },
                {"common": {"id": "bad id", "title": "空白", "contentsRightsType": "cc0"}},
                {"common": {"id": "made-up", "title": "未知", "contentsRightsType": "free"}},
                {"common": {"id": "no-code", "title": "無し"}},
                "not-an-item",
            ]
        }
    )
    assert sources == [
        {
            "url": "https://jpsearch.go.jp/item/arc_books-Ebi0824",
            "title": "北斎伝",
            "license": "unknown",
            "created": "unknown",
            "copyright": "unknown",
            "material_kind": "web",
            "rights_code": "ccbyncsa",
        }
    ]


def test_rights_code_does_not_change_risk() -> None:
    assert risk_level({"license": "unknown", "material_kind": "web", "rights_code": "cc0"}) == "review"


def test_search_failure_returns_empty(monkeypatch) -> None:
    def broken(_keyword: str) -> dict:
        raise TimeoutError("down")

    monkeypatch.setattr("app.jpsearch._fetch", broken)
    assert search_rights("葛飾北斎") == []


def test_lookup_caches_japan_search(monkeypatch) -> None:
    clear_lookup_cache()
    calls = {"jp": 0}

    def fake_search(_settings: Settings, _prompt: str) -> tuple[str, list[dict[str, str]], str]:
        return ("説明", [{"url": "https://example.com/a", "title": "Example", "text": ""}], "")

    def fake_rights(label: str) -> list[dict[str, str]]:
        calls["jp"] += 1
        assert label == "北斎"
        return sources_from_payload(
            {
                "list": [
                    {
                        "common": {
                            "id": "sample-1",
                            "title": "北斎",
                            "contentsRightsType": "incr",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.lookup._search", fake_search)
    monkeypatch.setattr("app.lookup.search_rights", fake_rights)
    monkeypatch.setattr("app.lookup.retrieve", lambda *_args, **_kwargs: [])

    settings = Settings(
        cors_origins=["http://127.0.0.1:3000"],
        gemini_model="test-model",
        cloud_project="",
        use_enterprise=False,
        session_signing_secret="test",
        session_cookie_secure=False,
    )
    first = lookup_object(settings, "人", owner_id="owner-a", query="北斎")
    second = lookup_object(settings, "人", owner_id="owner-a", query="北斎")
    assert calls["jp"] == 1
    assert second["cached"] is True
    assert any(item.get("rights_code") == "incr" for item in first["sources"])
