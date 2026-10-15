"""保護期間の満了日。通信しない。"""

from app.editor_assist import enrich_turn
from app.jpsearch import sources_from_payload
from app.term import protection_until


def test_one_year_ends_on_december_31_after_70_years() -> None:
    assert protection_until("1989年") == "2059-12-31"
    assert protection_until("1893") == "1963-12-31"


def test_missing_year_stays_unknown() -> None:
    assert protection_until("unknown") == "unknown"
    assert protection_until("") == "unknown"
    assert protection_until("明治二六") == "unknown"
    assert protection_until("2999年") == "unknown"


def test_several_years_use_the_newer_valid_one() -> None:
    assert protection_until("1989年と2001年") == "2071-12-31"
    assert protection_until("1989年と2999年") == "2059-12-31"


def test_japan_search_keeps_one_western_year() -> None:
    sources = sources_from_payload(
        {
            "list": [
                {
                    "common": {
                        "id": "sample-1",
                        "title": "北斎伝",
                        "contentsRightsType": "ccbyncsa",
                        "temporal": ["1893", "明治二六"],
                    }
                },
                {
                    "common": {
                        "id": "sample-2",
                        "title": "幅がある",
                        "contentsRightsType": "incr",
                        "temporal": ["1890", "1893"],
                    }
                },
            ]
        }
    )
    dated = next(item for item in sources if item["title"] == "北斎伝")
    ranged = next(item for item in sources if item["title"] == "幅がある")
    assert dated["created"] == "1893"
    assert ranged["created"] == "1893"
    enriched = enrich_turn({"sources": sources}, "北斎")
    by_title = {item["title"]: item for item in enriched["sources"]}
    assert by_title["北斎伝"]["protection_until"] == "1963-12-31"
    assert by_title["幅がある"]["protection_until"] == "1963-12-31"
    assert by_title["北斎伝"]["license"] == "unknown"


def test_page_year_does_not_change_license() -> None:
    enriched = enrich_turn(
        {
            "sources": [
                {
                    "url": "https://example.com/a",
                    "title": "Example",
                    "created": "1989年",
                    "license": "unknown",
                    "material_kind": "web",
                }
            ]
        },
        "手塚",
    )
    source = enriched["sources"][0]
    assert source["protection_until"] == "2059-12-31"
    assert source["license"] == "unknown"
    assert source["risk_level"] == "review"
    assert "満了日: 2059-12-31" in source["credit_memo"]
