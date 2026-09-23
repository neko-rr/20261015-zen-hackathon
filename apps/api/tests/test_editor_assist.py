"""危険度と引用メモの合成テスト。"""

from app.editor_assist import credit_memo, enrich_turn, risk_level


def test_risk_easy_own_claim() -> None:
    assert risk_level({"license": "own_claim", "material_kind": "own_work"}) == "easy"


def test_risk_easy_cc0() -> None:
    assert risk_level({"license": "CC0", "material_kind": "web"}) == "easy"


def test_risk_conditional_cc_by() -> None:
    assert risk_level({"license": "CC-BY 4.0", "material_kind": "web"}) == "conditional"


def test_risk_review_unknown() -> None:
    assert risk_level({"license": "unknown", "material_kind": "web"}) == "review"


def test_credit_memo_and_enrich_turn() -> None:
    payload = enrich_turn(
        {
            "summary": "note",
            "sources": [
                {
                    "url": "https://example.com/a",
                    "title": "Example",
                    "material_kind": "web",
                    "license": "CC0",
                }
            ],
        },
        "猫",
    )
    assert payload["object_label"] == "猫"
    assert payload["viewed_at"]
    source = payload["sources"][0]
    assert source["risk_level"] == "easy"
    assert "タイトル: Example" in source["credit_memo"]
    assert "種別: Web" in source["credit_memo"]
    memo = credit_memo(source, "2026-09-20T12:00:00+00:00")
    assert "取得日: 2026-09-20T12:00:00+00:00" in memo
