"""ジャパンサーチの権利コードだけを取る。キーは不要。権利者の断定はしない。"""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.term import latest_year

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://jpsearch.go.jp/api/item/search/jps-cross"
_ITEM_URL = "https://jpsearch.go.jp/item/{item_id}"
_MAX_ITEMS = 3
_TIMEOUT_SECONDS = 8
_MAX_BYTES = 1_000_000
_ITEM_ID = re.compile(r"^[A-Za-z0-9._-]{1,200}$")

# 簡易 Web API ガイド 3.2.2.1 のコード値だけ。表に無い値は捨てる。
_RIGHTS_CODES = frozenset(
    {
        "edu",
        "noncom",
        "com",
        "cc0",
        "pdm",
        "ccby",
        "ccbysa",
        "ccbynd",
        "ccbync",
        "ccbyncsa",
        "ccbyncnd",
        "incr",
        "incr_edu",
        "nocr_cont",
        "nocr_other",
        "uneval",
        "undet",
        "others",
    }
)


def search_rights(label: str) -> list[dict[str, str]]:
    """呼び方でアイテムを探す。失敗しても空を返し、ほかの出典は残す。"""
    keyword = " ".join(label.split())
    if not keyword:
        return []
    try:
        payload = _fetch(keyword)
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, ValueError):
        logger.exception("jpsearch failed")
        return []
    return sources_from_payload(payload)


def sources_from_payload(payload: Any) -> list[dict[str, str]]:
    """レスポンスにある権利コードだけを出典にする。"""
    if not isinstance(payload, dict):
        return []
    items = payload.get("list")
    if not isinstance(items, list):
        return []
    sources: list[dict[str, str]] = []
    for item in items:
        if len(sources) >= _MAX_ITEMS:
            break
        source = _one_source(item)
        if source is None:
            continue
        sources.append(source)
    return sources


def _one_source(item: Any) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None
    common = item.get("common")
    if not isinstance(common, dict):
        return None
    code = str(common.get("contentsRightsType") or "").strip()
    if code not in _RIGHTS_CODES:
        return None
    item_id = str(common.get("id") or item.get("id") or "").strip()
    if not _ITEM_ID.fullmatch(item_id):
        return None
    title = str(common.get("title") or "").strip() or item_id
    year = _temporal_year(common.get("temporal"))
    return {
        "url": _ITEM_URL.format(item_id=item_id),
        "title": title[:200],
        "license": "unknown",
        "created": str(year) if year else "unknown",
        "copyright": "unknown",
        "material_kind": "web",
        "rights_code": code,
    }


def _temporal_year(temporal: Any) -> int | None:
    """API の時間表記のうち、条件を満たすいちばん新しい西暦。"""
    if isinstance(temporal, str):
        parts = [temporal]
    elif isinstance(temporal, list):
        parts = [str(item) for item in temporal if item is not None]
    else:
        return None
    return latest_year(" ".join(parts))


def _fetch(keyword: str) -> Any:
    query = urllib.parse.urlencode({"keyword": keyword, "size": str(_MAX_ITEMS)})
    request = urllib.request.Request(
        f"{_SEARCH_URL}?{query}",
        headers={"Accept": "application/json", "User-Agent": "illustration-support"},
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        raw = response.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise ValueError("jpsearch response too large")
    return json.loads(raw.decode("utf-8"))
