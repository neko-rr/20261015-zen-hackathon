"""言葉を、既存の関節の角度だけにする。座標は作らない。"""

from __future__ import annotations

import copy
import json
import logging
import math
import re
from typing import Any

from google import genai
from google.genai import types

from app.errors import business_error, system_error
from app.mannequin import standing_mannequin
from app.pose_catalog import lookup_catalog
from app.settings import Settings

logger = logging.getLogger(__name__)

_CACHE_LIMIT = 32
_pose_cache: dict[str, list[dict[str, Any]]] = {}


def clear_pose_cache() -> None:
    _pose_cache.clear()

# 正が曲げる向き。範囲は度。
_LIMITS: dict[str, tuple[int, int]] = {
    "shoulder_l": (-60, 170),
    "shoulder_r": (-60, 170),
    "elbow_l": (0, 150),
    "elbow_r": (0, 150),
    "wrist_l": (-40, 40),
    "wrist_r": (-40, 40),
    "hip_l": (-40, 110),
    "hip_r": (-40, 110),
    "knee_l": (0, 140),
    "knee_r": (0, 140),
    "ankle_l": (-30, 40),
    "ankle_r": (-30, 40),
}

_PROMPT = """絵は描かない。座標も返さない。
日常の短い言葉を、デッサン人形の関節角度にする。
「座っている人」「手を挙げている人」のように曖昧でも、読みを3通りに分ける。
3つは別のポーズにする。同じ角度のコピーは禁止。
返す JSON だけ。
{"options":[
  {"summary":"一言","mirrored":false,"upper_deg":0,"lower_deg":0,"bends":{"hip_l":90}}
]}
関節は次だけ。値は度。
shoulder_l shoulder_r は -60 から 170。正で腕を上げる。手を挙げるなら 130 から 160。
elbow_l elbow_r は 0 から 150。正で肘を曲げる。
wrist_l wrist_r は -40 から 40。
hip_l hip_r は -40 から 110。正で太ももを前に出す。座るなら 80 から 110。
knee_l knee_r は 0 から 140。正で膝を曲げる。座るなら 90 から 130。
ankle_l ankle_r は -30 から 40。
upper_deg は肩のねじれ、lower_deg は腰のねじれ。どちらも -70 から 70。
left は人形の左、right は人形の右。
例: 座っている人は椅子（股90膝100）、床（股110膝130）、片側を崩す、の3つ。
例: 手を挙げている人は右手、左手、両手。挙げた肩は140前後、肘は10から30。
歩く、しゃがむ、片足、も同じ関節で表す。動かさない関節は書かない。
"""

# モデルが座りや挙手を立ちのまま返したときの控え。
_SIT = (
    {"summary": "椅子に座る", "bends": {"hip_l": 90, "hip_r": 90, "knee_l": 100, "knee_r": 100}},
    {"summary": "床に座る", "bends": {"hip_l": 110, "hip_r": 110, "knee_l": 130, "knee_r": 130, "elbow_l": 40, "elbow_r": 40}},
    {"summary": "崩して座る", "bends": {"hip_l": 80, "hip_r": 45, "knee_l": 110, "knee_r": 70}, "lower_deg": 12},
)
_RAISE = (
    {"summary": "右手を挙げる", "bends": {"shoulder_r": 145, "elbow_r": 20}},
    {"summary": "左手を挙げる", "bends": {"shoulder_l": 145, "elbow_l": 20}},
    {"summary": "両手を挙げる", "bends": {"shoulder_l": 155, "shoulder_r": 155, "elbow_l": 15, "elbow_r": 15}},
)


def instruct_pose(message: str, settings: Settings) -> dict[str, Any]:
    text = message.strip()
    if not text:
        raise business_error("empty_message", "言葉を入れてください。")
    catalog = lookup_catalog(text)
    if catalog is not None:
        return {
            "mannequin": standing_mannequin(),
            "options": [_one_pose(item) for item in catalog],
            "pose_source": "catalog",
        }
    key = re.sub(r"\s+", "", text).casefold()
    cached = _pose_cache.get(key)
    if cached is not None:
        return {
            "mannequin": standing_mannequin(),
            "options": copy.deepcopy(cached),
            "pose_source": "cache",
        }
    settings.require_gemini()
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=f"{_PROMPT}\n指示: {text[:500]}",
            config=types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json",
            ),
        )
        raw = response.text or ""
    except Exception as exc:
        logger.exception("spoken pose failed")
        raise system_error("spoken_pose_failed", "ポーズを読めませんでした。") from exc
    options = ensure_pose_options(text, poses_from_text(raw))
    _pose_cache[key] = copy.deepcopy(options)
    while len(_pose_cache) > _CACHE_LIMIT:
        _pose_cache.pop(next(iter(_pose_cache)))
    return {"mannequin": standing_mannequin(), "options": options, "pose_source": "new"}


def pose_from_text(raw: str) -> dict[str, Any]:
    options = poses_from_text(raw)
    return options[0]


def poses_from_text(raw: str) -> list[dict[str, Any]]:
    payload = _json_value(raw)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("options"), list):
        rows = payload["options"]
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        rows = []
    options: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        one = _one_pose(row)
        key = json.dumps(one["bends"], sort_keys=True)
        key = f"{key}|{one['upper_deg']}|{one['lower_deg']}|{one['mirrored']}"
        if key in seen:
            continue
        seen.add(key)
        options.append(one)
        if len(options) >= 3:
            break
    return options or [_one_pose({})]


def ensure_pose_options(message: str, options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """座りや挙手が立ちのままなら、決まった3候補に替える。"""
    folded = message.casefold()
    if _mentions_sit(folded) and not any(_is_sitting(item) for item in options):
        return [_one_pose(item) for item in _SIT]
    if _mentions_raise(folded) and not any(_is_raised(item) for item in options):
        return [_one_pose(item) for item in _RAISE]
    return options


def _one_pose(payload: dict[str, Any]) -> dict[str, Any]:
    bends: dict[str, float] = {}
    incoming = payload.get("bends")
    if isinstance(incoming, dict):
        for joint_id, value in incoming.items():
            if joint_id not in _LIMITS:
                continue
            try:
                degrees = float(value)
            except (TypeError, ValueError):
                continue
            low, high = _LIMITS[joint_id]
            degrees = min(high, max(low, degrees))
            if abs(degrees) < 0.5:
                continue
            bends[joint_id] = round(math.radians(degrees), 4)
    return {
        "summary": _summary(payload.get("summary")),
        "mirrored": payload.get("mirrored") is True,
        "upper_deg": _twist(payload.get("upper_deg")),
        "lower_deg": _twist(payload.get("lower_deg")),
        "bends": bends,
    }


def _mentions_sit(text: str) -> bool:
    return any(word in text for word in ("座", "すわ", "すわっ"))


def _mentions_raise(text: str) -> bool:
    return any(word in text for word in ("挙", "あげ", "上げ"))


def _is_sitting(pose: dict[str, Any]) -> bool:
    bends = pose.get("bends") or {}
    hips = max(abs(float(bends.get("hip_l", 0))), abs(float(bends.get("hip_r", 0))))
    knees = max(abs(float(bends.get("knee_l", 0))), abs(float(bends.get("knee_r", 0))))
    return hips >= math.radians(60) and knees >= math.radians(60)


def _is_raised(pose: dict[str, Any]) -> bool:
    bends = pose.get("bends") or {}
    arm = max(abs(float(bends.get("shoulder_l", 0))), abs(float(bends.get("shoulder_r", 0))))
    return arm >= math.radians(90)


def _twist(value: Any) -> int:
    try:
        degrees = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(-70, min(70, degrees))


def _summary(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:80] or "言葉のポーズ"


def _json_value(raw: str) -> Any:
    match = re.search(r"[\{\[].*[\}\]]", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
