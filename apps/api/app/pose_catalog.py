"""デッサンでよく使うポーズの一覧。データベースは使わない。

言葉がこの一覧に当たれば、関節の角度をすぐ返す。
当たらない言葉だけ、あとから Gemini が新しい角度を作る。
"""

from __future__ import annotations

import re
from typing import Any

# 短い語は、より長い語が同じ文にあるとき後回しにする。
_GENERIC = frozenset({"座", "挙", "挙げ", "挙げる", "あげ", "上げ", "立つ", "立ち"})

# 試しの一覧。角度は度。正で、腕は上げ、股は前、膝は折る。
_POSES: tuple[dict[str, Any], ...] = (
    {
        "group": "stand",
        "summary": "まっすぐ立つ",
        "words": ("直立", "気をつけ", "まっすぐ", "立つ", "立ち"),
        "bends": {},
    },
    {
        "group": "stand",
        "summary": "片足に体重を乗せる",
        "words": ("体重", "休め"),
        "bends": {"hip_l": 12, "knee_l": 20, "hip_r": -15, "shoulder_l": 10},
        "lower_deg": 10,
    },
    {
        "group": "stand",
        "summary": "腰に手を当てる",
        "words": ("腰",),
        "bends": {"shoulder_l": -25, "shoulder_r": -25, "elbow_l": 80, "elbow_r": 80},
    },
    {
        "group": "arms",
        "summary": "腕を組む",
        "words": ("腕を組", "腕組", "組む"),
        "bends": {"elbow_l": 100, "elbow_r": 100},
    },
    {
        "group": "move",
        "summary": "歩く",
        "words": ("歩",),
        "bends": {
            "hip_l": 35,
            "hip_r": -25,
            "knee_l": 25,
            "knee_r": 10,
            "shoulder_l": -20,
            "shoulder_r": 25,
        },
    },
    {
        "group": "move",
        "summary": "走る",
        "words": ("走",),
        "bends": {
            "hip_l": 55,
            "hip_r": -30,
            "knee_l": 80,
            "knee_r": 40,
            "shoulder_l": 50,
            "shoulder_r": -15,
            "elbow_l": 80,
            "elbow_r": 70,
        },
    },
    {
        "group": "move",
        "summary": "片足を上げる",
        "words": ("片足",),
        "bends": {"hip_r": 75, "knee_r": 100, "shoulder_l": 15},
    },
    {
        "group": "sit",
        "summary": "椅子に座る",
        "words": ("椅子", "座"),
        "bends": {"hip_l": 90, "hip_r": 90, "knee_l": 100, "knee_r": 100},
    },
    {
        "group": "sit",
        "summary": "床に座る",
        "words": ("体育", "床"),
        "bends": {
            "hip_l": 110,
            "hip_r": 110,
            "knee_l": 130,
            "knee_r": 130,
            "elbow_l": 40,
            "elbow_r": 40,
        },
    },
    {
        "group": "sit",
        "summary": "しゃがむ",
        "words": ("しゃが", "かが", "うずくま"),
        "bends": {"hip_l": 95, "hip_r": 95, "knee_l": 120, "knee_r": 120},
    },
    {
        "group": "raise",
        "summary": "右手を挙げる",
        "words": ("右手", "挙げ", "挙げる", "挙", "あげ", "上げ"),
        "bends": {"shoulder_r": 145, "elbow_r": 20},
    },
    {
        "group": "raise",
        "summary": "左手を挙げる",
        "words": ("左手",),
        "bends": {"shoulder_l": 145, "elbow_l": 20},
    },
    {
        "group": "raise",
        "summary": "両手を挙げる",
        "words": ("両手", "両方"),
        "bends": {"shoulder_l": 155, "shoulder_r": 155, "elbow_l": 15, "elbow_r": 15},
    },
)


def catalog_size() -> int:
    return len(_POSES)


def lookup_catalog(message: str) -> list[dict[str, Any]] | None:
    """当たった分類の候補を最大3つ返す。複数の分類が同点なら None。"""
    text = _fold(message)
    if not text:
        return None
    hits = [pose for pose in _POSES if _score(text, pose) != (0, 0)]
    if not hits:
        return None
    groups = {pose["group"] for pose in hits}
    if len(groups) != 1:
        return None
    group = next(iter(groups))
    ranked = sorted(
        (pose for pose in _POSES if pose["group"] == group),
        key=lambda pose: _score(text, pose),
        reverse=True,
    )
    return [dict(pose) for pose in ranked[:3]]


def _score(text: str, pose: dict[str, Any]) -> tuple[int, int]:
    matched = [word for word in pose["words"] if word in text]
    if not matched:
        return (0, 0)
    specific = [word for word in matched if word not in _GENERIC]
    specific_len = max((len(word) for word in specific), default=0)
    any_len = max(len(word) for word in matched)
    return (specific_len, any_len)


def _fold(message: str) -> str:
    return re.sub(r"\s+", "", message).casefold()
