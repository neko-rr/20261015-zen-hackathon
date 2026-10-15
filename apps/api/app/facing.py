"""体の向き。関節で機械的に決め、自信が低いときだけ Gemini に正面・背面・左右を聞く。

Gemini には座標を返させない。左右が向きと矛盾するときだけ、左右の関節を入れ替える。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.settings import Settings

logger = logging.getLogger(__name__)

_ALLOWED = {"front", "back", "left", "right", "unknown"}
_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
# 自信がこれ未満なら、画像を Gemini に見せて最大2回聞く。
_ASK_BELOW = 0.72
_PAIRS = (
    (1, 4),
    (2, 5),
    (3, 6),
    (7, 8),
    (9, 10),
    (11, 12),
    (13, 14),
    (15, 16),
    (17, 18),
    (19, 20),
    (21, 22),
    (23, 24),
    (25, 26),
    (27, 28),
    (29, 30),
    (31, 32),
)


def orient_person(
    settings: Settings,
    image: bytes,
    mime_type: str,
    landmarks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """向きを決め、必要なら左右を入れ替えた関節を返す。失敗しても元の関節を返す。"""
    if not landmarks:
        return landmarks, _report("unknown", 0.0, "mechanical", False)
    try:
        mechanical = judge_landmarks(landmarks)
        votes: list[dict[str, Any]] = []
        if image and settings.gemini_model and mechanical["confidence"] < _ASK_BELOW:
            first = ask_gemini(settings, image, mime_type, prior=None)
            votes.append(first)
            if first["facing"] not in ("unknown", mechanical["facing"]):
                votes.append(ask_gemini(settings, image, mime_type, prior=mechanical["facing"]))
        corrected, report = decide(mechanical, votes, landmarks)
    except Exception:
        logger.exception("facing failed")
        return landmarks, _report("unknown", 0.0, "mechanical", False)
    logger.info(
        "facing result=%s source=%s swapped=%s confidence=%.2f",
        report["facing"],
        report["source"],
        report["swapped"],
        report["confidence"],
    )
    return corrected, report


def judge_landmarks(landmarks: list[dict[str, Any]]) -> dict[str, Any]:
    """鼻の前後と肩の左右だけで向きを決める。座標は作らない。"""
    points = _index(landmarks)
    left = points.get(11)
    right = points.get(12)
    if left is None or right is None:
        return _report("unknown", 0.0, "mechanical", False)
    order = float(left["x"]) - float(right["x"])
    shoulder_z = (float(left["z"]) + float(right["z"])) / 2
    nose = points.get(0)
    scores = {"front": 0.0, "back": 0.0, "left": 0.0, "right": 0.0}
    if nose is not None:
        nose_delta = float(nose["z"]) - shoulder_z
        if nose_delta < -0.02:
            scores["front"] += min(1.0, abs(nose_delta) / 0.12)
        elif nose_delta > 0.02:
            scores["back"] += min(1.0, abs(nose_delta) / 0.12)
    if order > 0.02:
        scores["front"] += 0.7
    elif order < -0.02:
        scores["back"] += 0.7
    depth = float(left["z"]) - float(right["z"])
    if abs(depth) > 0.08 and abs(order) < 0.1:
        # 左肩が手前なら、顔は画像の左を向いている。生成画像の採点で確認した。
        side = "left" if depth < 0 else "right"
        scores[side] += min(1.0, abs(depth) / 0.2)
    facing = max(scores, key=scores.get)
    best = scores[facing]
    second = sorted(scores.values())[-2]
    confidence = max(0.0, min(1.0, best - second))
    if best < 0.35:
        return _report("unknown", confidence, "mechanical", False)
    return _report(facing, confidence, "mechanical", False)


def decide(
    mechanical: dict[str, Any],
    votes: list[dict[str, Any]],
    landmarks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """機械と Gemini が割れたら、同意が取れた側を採用する。"""
    facing = str(mechanical.get("facing") or "unknown")
    source = "mechanical"
    known = [str(item.get("facing") or "unknown") for item in votes if item.get("facing") in _ALLOWED]
    known = [item for item in known if item != "unknown"]
    if known and facing in known:
        source = "agree"
    elif known and float(mechanical.get("confidence") or 0) < _ASK_BELOW:
        facing = max(set(known), key=lambda item: (known.count(item), item == mechanical.get("facing")))
        source = "gemini"
        if len(votes) >= 2 and known.count(facing) == 1 and facing != mechanical.get("facing"):
            # 2回目が機械に戻ったら、機械を優先する。
            if votes[-1].get("facing") == mechanical.get("facing"):
                facing = str(mechanical.get("facing") or "unknown")
                source = "mechanical"
    swapped = needs_swap(landmarks, facing)
    corrected = swap_sides(landmarks) if swapped else landmarks
    return corrected, _report(facing, float(mechanical.get("confidence") or 0), source, swapped)


def needs_swap(landmarks: list[dict[str, Any]], facing: str) -> bool:
    """正面なのに左肩が画像の左にあるなど、左右が向きと逆のとき。"""
    order = _shoulder_order(landmarks)
    if order is None or facing not in ("front", "back"):
        return False
    if facing == "front" and order < -0.03:
        return True
    if facing == "back" and order > 0.03:
        return True
    return False


def swap_sides(landmarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """左右の番号は残し、座標だけを入れ替える。"""
    rows = [dict(item) for item in landmarks]
    by_index = {int(item["index"]): item for item in rows if "index" in item}
    for left, right in _PAIRS:
        first = by_index.get(left)
        second = by_index.get(right)
        if first is None or second is None:
            continue
        for key in ("x", "y", "z", "visibility"):
            if key in first or key in second:
                first[key], second[key] = second.get(key), first.get(key)
    return rows


def ask_gemini(settings: Settings, image: bytes, mime_type: str, prior: str | None) -> dict[str, Any]:
    """画像から向きの単語だけを取る。失敗時は unknown。"""
    if not image or not settings.gemini_model:
        return _report("unknown", 0.0, "gemini", False)
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.exception("facing sdk missing")
        return _report("unknown", 0.0, "gemini", False)
    shrunk, mime = _shrink(image, mime_type)
    try:
        client = genai.Client(http_options=types.HttpOptions(timeout=20_000))
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[types.Part.from_bytes(data=shrunk, mime_type=mime), _prompt(prior)],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        return facing_from_text(response.text or "")
    except Exception:
        logger.exception("facing gemini failed model=%s", settings.gemini_model)
        return _report("unknown", 0.0, "gemini", False)


def facing_from_text(text: str) -> dict[str, Any]:
    """モデル出力から facing だけを残す。座標のキーは捨てる。"""
    raw = text or ""
    fenced = _FENCE.search(raw)
    if fenced:
        raw = fenced.group(1)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return _report("unknown", 0.0, "gemini", False)
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return _report("unknown", 0.0, "gemini", False)
    if not isinstance(data, dict):
        return _report("unknown", 0.0, "gemini", False)
    facing = str(data.get("facing") or "unknown").strip().lower()
    if facing not in _ALLOWED:
        facing = "unknown"
    return _report(facing, 0.0, "gemini", False)


def _prompt(prior: str | None) -> str:
    text = (
        "写真にいちばん大きく写る人について、カメラに対する体の向きだけを判定してください。"
        "JSON だけを返してください。座標、角度、説明文は返さないでください。"
        '{"facing":"front"}'
        "facing は front, back, left, right, unknown のいずれか一つです。"
        "front は胸と顔がカメラを向いている。"
        "back は背中がカメラを向いている。"
        "left は顔が画像の左を向いている。"
        "right は顔が画像の右を向いている。"
        "人がいなければ unknown。"
    )
    if prior in _ALLOWED and prior != "unknown":
        text += f"別の手順は {prior} と見ています。画像と違うなら正しい値にしてください。"
    return text


def _shoulder_order(landmarks: list[dict[str, Any]]) -> float | None:
    points = _index(landmarks)
    left = points.get(11)
    right = points.get(12)
    if left is None or right is None:
        return None
    return float(left["x"]) - float(right["x"])


def _index(landmarks: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    for item in landmarks:
        try:
            found[int(item["index"])] = item
        except (KeyError, TypeError, ValueError):
            continue
    return found


def _report(facing: str, confidence: float, source: str, swapped: bool) -> dict[str, Any]:
    if facing not in _ALLOWED:
        facing = "unknown"
    return {
        "facing": facing,
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "source": source,
        "swapped": swapped,
    }


def _shrink(image: bytes, mime_type: str) -> tuple[bytes, str]:
    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(image)) as picture:
            rgb = picture.convert("RGB")
            rgb.thumbnail((768, 768))
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=80)
            return buffer.getvalue(), "image/jpeg"
    except Exception:
        logger.exception("facing shrink skipped")
        return image, mime_type or "image/jpeg"
