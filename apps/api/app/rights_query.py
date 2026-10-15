"""著作権の検索に使う語。見た目の呼び方は使わない。"""

_GENERIC = frozenset(
    {
        "人",
        "女性",
        "男性",
        "子供",
        "子ども",
        "不明",
        "unknown",
        "none",
        "n/a",
        "人物",
        "大人",
        "駅",
        "建物",
        "風景",
        "動物",
        "道具",
        "衣服",
        "シャツ",
    }
)


def rights_query(public_name: str = "", work_title: str = "", user_query: str = "") -> str:
    """題名か作者として使える語。一般的な呼び方だけでは空。"""
    for value in (user_query, public_name, work_title):
        cleaned = " ".join(str(value).split())
        if cleaned and cleaned.casefold() not in _GENERIC:
            return cleaned[:80]
    return ""
