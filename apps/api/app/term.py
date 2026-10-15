"""出典に書いてある年から、保護期間の満了日だけを計算する。"""

import re
from datetime import date

# 和暦は換算しない。未来の年は条件を満たさない。
_YEAR = re.compile(r"(?<!\d)(\d{4})(?!\d)")
_MIN_YEAR = 1000


def latest_year(text: str) -> int | None:
    """条件を満たす西暦のうち、いちばん新しい年。無ければ None。"""
    if not text or text.strip().casefold() == "unknown":
        return None
    this_year = date.today().year
    found = [
        int(match)
        for match in _YEAR.findall(text)
        if _MIN_YEAR <= int(match) <= this_year
    ]
    if not found:
        return None
    return max(found)


def protection_until(text: str) -> str:
    """翌年1月1日から70年。満了日は「その年+70年」の12月31日。年が無ければ unknown。"""
    year = latest_year(text)
    if year is None:
        return "unknown"
    return f"{year + 70}-12-31"
