"""手足の長さと左右を検査する。壊れた関節だけ落とす。座標は作らない。

自信のある写真では Gemini を呼ばない。長すぎる、または左右が逆のときだけ、
上がっているか隠れているかを最大2回聞き、その答えと矛盾しない範囲で直す。
"""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from app.settings import Settings

logger = logging.getLogger(__name__)

_STATES = {"down", "raised", "hidden"}
_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_SUSPECT = 1.45
_EXTREME = 1.8
_CHAINS = (
    ("left_arm", 11, 13, (13, 15)),
    ("left_arm", 13, 15, (15,)),
    ("right_arm", 12, 14, (14, 16)),
    ("right_arm", 14, 16, (16,)),
    ("left_leg", 23, 25, (25, 27)),
    ("left_leg", 25, 27, (27,)),
    ("right_leg", 24, 26, (26, 28)),
    ("right_leg", 26, 28, (28,)),
)
_ARM_INDEXES = {
    "left": (13, 15, 17, 19, 21),
    "right": (14, 16, 18, 20, 22),
}
_EDGE_INDEXES = set(range(15, 23)) | set(range(25, 33))


def refine_limbs(
    settings: Settings,
    image: bytes,
    mime_type: str,
    landmarks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """長すぎる関節を落とし、左右の腕が逆なら入れ替える。"""
    if not landmarks:
        return landmarks, _report([], False, "mechanical")
    try:
        rows = drop_edge_pins(landmarks)
        issues = audit_limbs(rows)
        view: dict[str, str] | None = None
        source = "mechanical"
        if issues and image and settings.gemini_model:
            first = ask_limbs(settings, image, mime_type, prior=None)
            second = ask_limbs(settings, image, mime_type, prior="confirm" if first else "retry")
            if first and first == second:
                view = first
                source = "agree"
        corrected, swapped = apply_limb_repairs(rows, issues, view)
        if swapped:
            source = "agree"
        return corrected, _report(_dropped(landmarks, corrected), swapped, source)
    except Exception:
        logger.exception("limb refine failed")
        return landmarks, _report([], False, "mechanical")


def drop_edge_pins(landmarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """枠に張り付いた手首・膝・足首を落とす。写っていない節を端の座標で描かない。"""
    kept: list[dict[str, Any]] = []
    for item in landmarks:
        try:
            index = int(item.get("index", -1))
            visibility = float(item.get("visibility", 1.0) or 0.0)
            x = float(item["x"])
            y = float(item["y"])
        except (TypeError, ValueError, KeyError):
            kept.append(item)
            continue
        on_edge = x <= 0.01 or x >= 0.99 or y <= 0.01 or y >= 0.99
        if index in _EDGE_INDEXES and on_edge and visibility < 0.9:
            continue
        kept.append(item)
    return kept


def audit_limbs(landmarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """胴より長すぎる節と、反対側の肩に付いた肘を見つける。"""
    points = _index(landmarks)
    torso = _torso(points)
    if torso < 0.08:
        return []
    issues: list[dict[str, Any]] = []
    for limb, start, end, drop in _CHAINS:
        first = points.get(start)
        second = points.get(end)
        if first is None or second is None:
            continue
        ratio = _distance(first, second) / torso
        if ratio >= _SUSPECT:
            issues.append({"limb": limb, "kind": "long", "ratio": round(ratio, 3), "indices": list(drop)})
    for limb, shoulder, elbow, other in (
        ("left_arm", 11, 13, 12),
        ("right_arm", 12, 14, 11),
    ):
        if shoulder not in points or elbow not in points or other not in points:
            continue
        own = _distance(points[elbow], points[shoulder])
        opposite = _distance(points[elbow], points[other])
        if opposite + 0.02 < own and own > torso * 0.45:
            wrist = 15 if limb == "left_arm" else 16
            issues.append({"limb": limb, "kind": "crossed", "ratio": round(own / torso, 3), "indices": [elbow, wrist]})
    return issues


def apply_limb_repairs(
    landmarks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    view: dict[str, str] | None,
) -> tuple[list[dict[str, Any]], bool]:
    """Gemini が『見えている』と言った節は、極端なときだけ落とす。"""
    swapped = False
    rows = landmarks
    crossed = any(issue.get("kind") == "crossed" for issue in issues)
    if view and crossed and _arms_are_reversed(rows, view):
        rows = _swap_arms(rows)
        swapped = True
        issues = audit_limbs(rows)
    drop: set[int] = set()
    for issue in issues:
        state = (view or {}).get(issue["limb"])
        if issue["kind"] == "crossed" or issue["ratio"] >= _EXTREME or state == "hidden":
            drop.update(int(index) for index in issue["indices"])
    if not drop:
        return rows, swapped
    kept = [item for item in rows if int(item.get("index", -1)) not in drop]
    return kept, swapped


def ask_limbs(settings: Settings, image: bytes, mime_type: str, prior: str | None) -> dict[str, str]:
    """手足が見えているか、上がっているかだけを聞く。"""
    if not image or not settings.gemini_model:
        return {}
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.exception("limb sdk missing")
        return {}
    try:
        from app.facing import _shrink
    except Exception:
        _shrink = None  # type: ignore[assignment]
    payload, mime = (image, mime_type)
    if _shrink is not None:
        payload, mime = _shrink(image, mime_type)
    try:
        client = genai.Client(http_options=types.HttpOptions(timeout=20_000))
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[types.Part.from_bytes(data=payload, mime_type=mime), _prompt(prior)],
            config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
        )
        return limbs_from_text(response.text or "")
    except Exception:
        logger.exception("limb gemini failed model=%s", settings.gemini_model)
        return {}


def limbs_from_text(text: str) -> dict[str, str]:
    """モデル出力から4つの状態だけを残す。座標は捨てる。"""
    raw = text or ""
    fenced = _FENCE.search(raw)
    if fenced:
        raw = fenced.group(1)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    found: dict[str, str] = {}
    for key in ("left_arm", "right_arm", "left_leg", "right_leg"):
        value = str(data.get(key) or "").strip().lower()
        if value in _STATES:
            found[key] = value
    return found


def arm_pose(landmarks: list[dict[str, Any]], side: str) -> str:
    """画像の上下で、腕が上がっているかを見る。y は下が正。"""
    points = _index(landmarks)
    shoulder = 11 if side == "left" else 12
    wrist = 15 if side == "left" else 16
    if shoulder not in points or wrist not in points:
        return "hidden"
    if float(points[wrist]["y"]) < float(points[shoulder]["y"]) - 0.03:
        return "raised"
    return "down"


def _arms_are_reversed(landmarks: list[dict[str, Any]], view: dict[str, str]) -> bool:
    left = view.get("left_arm")
    right = view.get("right_arm")
    if left not in ("raised", "down") or right not in ("raised", "down") or left == right:
        return False
    return arm_pose(landmarks, "left") == right and arm_pose(landmarks, "right") == left


def _swap_arms(landmarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(item) for item in landmarks]
    by_index = {int(item["index"]): item for item in rows if "index" in item}
    for left, right in zip(_ARM_INDEXES["left"], _ARM_INDEXES["right"], strict=True):
        first = by_index.get(left)
        second = by_index.get(right)
        if first is None or second is None:
            continue
        for key in ("x", "y", "z", "visibility"):
            if key in first or key in second:
                first[key], second[key] = second.get(key), first.get(key)
    return rows


def _prompt(prior: str | None) -> str:
    text = (
        "写真でいちばん大きい人の手足が、どうなっているかだけを答えてください。"
        "JSON だけ。座標や角度は返さないでください。"
        '{"left_arm":"down","right_arm":"down","left_leg":"down","right_leg":"down"}'
        "値は down, raised, hidden だけです。"
        "left は本人の左、right は本人の右です。"
        "raised は肩や腰より上に上がっている。hidden は写っていない。down は体の横か下にある。"
        "人がいなければ4つとも hidden。"
    )
    if prior:
        text += "前の返答が読めませんでした。同じ形式でもう一度返してください。"
    return text


def _torso(points: dict[int, dict[str, Any]]) -> float:
    if not all(index in points for index in (11, 12, 23, 24)):
        return 0.0
    shoulder = {
        "x": (float(points[11]["x"]) + float(points[12]["x"])) / 2,
        "y": (float(points[11]["y"]) + float(points[12]["y"])) / 2,
    }
    hip = {
        "x": (float(points[23]["x"]) + float(points[24]["x"])) / 2,
        "y": (float(points[23]["y"]) + float(points[24]["y"])) / 2,
    }
    return _distance(shoulder, hip)


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def _index(landmarks: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    for item in landmarks:
        try:
            found[int(item["index"])] = item
        except (KeyError, TypeError, ValueError):
            continue
    return found


def _dropped(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[int]:
    kept = {int(item["index"]) for item in after if "index" in item}
    return sorted(int(item["index"]) for item in before if "index" in item and int(item["index"]) not in kept)


def _report(dropped: list[int], swapped: bool, source: str) -> dict[str, Any]:
    logger.info("limbs dropped=%s swapped_arms=%s source=%s", dropped, swapped, source)
    return {"dropped": dropped, "swapped_arms": swapped, "source": source}
