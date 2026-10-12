"""Jev 無しでも権利は unknown、％は null。"""

from app.verify import quoted_rights, verify_sources


def test_verify_without_jev_returns_null_scores(monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    sources = verify_sources(
        "cat",
        [
            {
                "url": "https://example.com/a",
                "title": "Example",
                "text": "CC-BY 4.0 Copyright 2020 Example.",
            }
        ],
        "ライセンスは？",
    )
    assert len(sources) == 1
    item = sources[0]
    assert item["license"] == "unknown"
    assert item["material_kind"] == "web"
    assert item["jev"] == {
        "about": None,
        "license": None,
        "created": None,
        "copyright": None,
    }


def test_quoted_rights_copies_page_text_only() -> None:
    quoted = quoted_rights(
        [
            {
                "url": "https://example.com/a",
                "title": "Example",
                "text": "CC-BY 4.0 Copyright 2020 Example.",
                "material_kind": "web",
            },
            {
                "url": "https://example.com/b",
                "title": "Empty",
                "text": "説明だけ。",
                "material_kind": "web",
            },
        ]
    )
    assert quoted[0]["license"].startswith("CC-BY")
    assert "Copyright" in quoted[0]["copyright"]
    assert quoted[0]["created"] == "2020"
    assert quoted[1]["license"] == "unknown"
    assert quoted[1]["copyright"] == "unknown"
