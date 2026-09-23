"""編集者向けの危険度・引用メモ。法的断定はしない。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.jev_client import ACT_THRESHOLD

_EASY = re.compile(
    r"(CC0|Public Domain|パブリックドメイン)",
    re.IGNORECASE,
)
_CONDITIONAL = re.compile(
    r"(CC[-\s]?BY|Creative Commons|All rights reserved|クリエイティブ・コモンズ)",
    re.IGNORECASE,
)

_KIND_JA = {
    "own_work": "自作",
    "third_party": "他者",
    "web": "Web",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def risk_level(source: dict[str, Any]) -> str:
    """easy | conditional | review。目安のみ。"""
    license_value = str(source.get("license") or "").strip()
    kind = str(source.get("material_kind") or "web")
    if license_value == "own_claim" or (license_value and _EASY.search(license_value)):
        return "easy"
    if license_value and _CONDITIONAL.search(license_value):
        return "conditional"
    if kind in ("web", "third_party"):
        jev = source.get("jev") or {}
        if isinstance(jev, dict):
            for key in ("license", "copyright"):
                score = jev.get(key)
                if score is not None and float(score) < ACT_THRESHOLD * 100 and license_value in (
                    "",
                    "unknown",
                ):
                    return "review"
        if not license_value or license_value == "unknown":
            return "review"
    if not license_value or license_value == "unknown":
        return "review"
    return "review"


def credit_memo(source: dict[str, Any], viewed_at: str = "") -> str:
    title = str(source.get("title") or "").strip() or "(無題)"
    url = str(source.get("url") or "").strip() or "(URLなし)"
    kind = str(source.get("material_kind") or "web")
    kind_label = _KIND_JA.get(kind, kind)
    license_value = str(source.get("license") or "unknown").strip() or "unknown"
    when = viewed_at.strip() or now_iso()
    return (
        f"タイトル: {title}\n"
        f"URL: {url}\n"
        f"種別: {kind_label}\n"
        f"ライセンス: {license_value}\n"
        f"取得日: {when}"
    )


def enrich_sources(sources: list[dict[str, Any]], viewed_at: str) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in sources:
        row = dict(item)
        # 自動検索の出典には license が無いことがある
        if "license" not in row:
            if row.get("material_kind") == "own_work":
                row["license"] = "own_claim"
            else:
                row["license"] = "unknown"
        row["risk_level"] = risk_level(row)
        row["credit_memo"] = credit_memo(row, viewed_at)
        enriched.append(row)
    return enriched


def enrich_turn(payload: dict[str, Any], object_label: str) -> dict[str, Any]:
    viewed = now_iso()
    sources = enrich_sources(list(payload.get("sources") or []), viewed)
    return {
        **payload,
        "object_label": object_label,
        "viewed_at": viewed,
        "sources": sources,
    }
