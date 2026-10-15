"""MediaPipe Pose で姿勢ランドマークを取る。失敗時は空を返す。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# MediaPipe Pose Landmarker の標準接続（インデックス）
POSE_EDGES: list[tuple[int, int]] = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 7),
    (0, 4),
    (4, 5),
    (5, 6),
    (6, 8),
    (9, 10),
    (11, 12),
    (11, 13),
    (13, 15),
    (15, 17),
    (15, 19),
    (15, 21),
    (17, 19),
    (12, 14),
    (14, 16),
    (16, 18),
    (16, 20),
    (16, 22),
    (18, 20),
    (11, 23),
    (12, 24),
    (23, 24),
    (23, 25),
    (25, 27),
    (27, 29),
    (27, 31),
    (29, 31),
    (24, 26),
    (26, 28),
    (28, 30),
    (28, 32),
    (30, 32),
]

_LANDMARK_NAMES: list[str] = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]

# デッサン補助用の筋肉ラベル（ランドマーク中点）。医学的正確さは保証しない。
_MUSCLE_DEFS: list[tuple[str, int, int]] = [
    ("僧帽筋", 11, 12),
    ("大胸筋", 11, 12),
    ("左三角筋", 11, 13),
    ("右三角筋", 12, 14),
    ("左上腕二頭筋", 11, 13),
    ("右上腕二頭筋", 12, 14),
    ("腹直筋", 11, 23),
    ("左大腿四頭筋", 23, 25),
    ("右大腿四頭筋", 24, 26),
    ("左腓腹筋", 25, 27),
    ("右腓腹筋", 26, 28),
]

_MODEL_CANDIDATES = [
    Path(__file__).resolve().parent / "models" / "pose_landmarker_full.task",
    Path(__file__).resolve().parent / "models" / "pose_landmarker_lite.task",
]

_detector = None
_detector_failed = False
MAX_POSES = 4
# これより小さい人は、元画像から切り出して関節を取り直す
_SMALL_SPAN = 0.45
_CROP_MARGIN = 0.45


def empty_pose() -> dict[str, Any]:
    return {"landmarks": [], "edges": [], "muscles": [], "people": []}


def estimate_pose(image: bytes, mime_type: str, pixels: Any | None = None) -> dict[str, Any]:
    """画像から姿勢を推定する。取れなければ空。pixels があれば再デコードしない。"""
    if not image and pixels is None:
        return empty_pose()
    detector = _get_detector()
    if detector is None:
        return empty_pose()

    try:
        import mediapipe as mp
    except ImportError:
        logger.exception("pose skipped reason=mediapipe_missing")
        return empty_pose()

    try:
        if pixels is None:
            pixels = _decode_pixels(image)
        people = _detect_people(detector, mp, pixels)
        if _scene_is_distant(people):
            people = _merge_people(people, _detect_tiles(detector, mp, pixels))
        people = [_refine_small(detector, mp, pixels, person) for person in people]
        people = order_people(_dedupe(people))[:MAX_POSES]
    except Exception:
        logger.exception("pose detect failed")
        return empty_pose()

    if not people:
        return empty_pose()
    first = people[0]
    logger.info("pose people=%s landmarks=%s", len(people), len(first["landmarks"]))
    return {
        "landmarks": first["landmarks"],
        "edges": first["edges"],
        "muscles": first["muscles"],
        "people": people,
    }


def map_person_from_crop(
    person: dict[str, Any],
    left: int,
    top: int,
    right: int,
    bottom: int,
    width: int,
    height: int,
) -> dict[str, Any]:
    """切り出し画像の関節を、元画像の 0〜1 に戻す。"""
    if width <= 0 or height <= 0:
        return person
    crop_w = max(right - left, 1)
    crop_h = max(bottom - top, 1)
    landmarks: list[dict[str, float | str]] = []
    for item in person.get("landmarks") or []:
        mapped = dict(item)
        mapped["x"] = _unit(left / width + float(item["x"]) * crop_w / width)
        mapped["y"] = _unit(top / height + float(item["y"]) * crop_h / height)
        landmarks.append(mapped)
    return _pack(landmarks)


def order_people(people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """左から右。肩の中点、無ければ関節の平均。"""
    return sorted(people, key=_anchor_x)


def _one_pose(raw: Any) -> dict[str, Any]:
    landmarks: list[dict[str, float | str]] = []
    for index, point in enumerate(raw):
        name = _LANDMARK_NAMES[index] if index < len(_LANDMARK_NAMES) else f"pt_{index}"
        visibility = float(getattr(point, "visibility", 1.0) or 0.0)
        if visibility < 0.35:
            continue
        landmarks.append(
            {
                "index": index,
                "name": name,
                "x": _unit(float(point.x)),
                "y": _unit(float(point.y)),
                "z": float(point.z),
                "visibility": visibility,
            }
        )
    return _pack(landmarks)


def _pack(landmarks: list[dict[str, float | str]]) -> dict[str, Any]:
    by_index = {int(item["index"]): item for item in landmarks if "index" in item}
    edges: list[dict[str, float | int]] = []
    for start, end in POSE_EDGES:
        if start not in by_index or end not in by_index:
            continue
        a = by_index[start]
        b = by_index[end]
        edges.append(
            {
                "start": start,
                "end": end,
                "x1": a["x"],
                "y1": a["y"],
                "x2": b["x"],
                "y2": b["y"],
            }
        )
    return {"landmarks": landmarks, "edges": edges, "muscles": _muscle_labels(by_index)}


def parts_from_landmarks(landmarks: list[dict[str, Any]]) -> dict[str, Any]:
    """向きや左右を直したあと、骨格の線と筋肉の位置を作り直す。"""
    packed = _pack(landmarks)
    return {"edges": packed["edges"], "muscles": packed["muscles"]}


def _detect_people(detector: Any, mp: Any, pixels: Any) -> list[dict[str, Any]]:
    if pixels is None or getattr(pixels, "size", 0) == 0:
        return []
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=pixels)
    result = detector.detect(image)
    if not result.pose_landmarks:
        return []
    return [item for item in (_one_pose(raw) for raw in result.pose_landmarks[:MAX_POSES]) if item["landmarks"]]


def _scene_is_distant(people: list[dict[str, Any]]) -> bool:
    """誰もいない、または写っている人が枠より小さい。"""
    if not people:
        return True
    return max(_span_y(person) for person in people) < _SMALL_SPAN


def _span_y(person: dict[str, Any]) -> float:
    ys = [float(item["y"]) for item in person.get("landmarks") or []]
    if len(ys) < 2:
        return 0.0
    return max(ys) - min(ys)


def _detect_tiles(detector: Any, mp: Any, pixels: Any) -> list[dict[str, Any]]:
    """全体で小さい人を、重なる4区画で探す。"""
    height, width = pixels.shape[:2]
    found: list[dict[str, Any]] = []
    span = 0.62
    for row in (0.0, 0.38):
        for col in (0.0, 0.38):
            left = int(col * width)
            top = int(row * height)
            right = min(width, int((col + span) * width))
            bottom = min(height, int((row + span) * height))
            crop = _contiguous(pixels[top:bottom, left:right])
            for person in _detect_people(detector, mp, crop):
                found.append(map_person_from_crop(person, left, top, right, bottom, width, height))
    return found


def _refine_small(detector: Any, mp: Any, pixels: Any, person: dict[str, Any]) -> dict[str, Any]:
    """小さい人だけ、余裕を付けた範囲を元画像から切り出して取り直す。"""
    if _span_y(person) >= _SMALL_SPAN:
        return person
    height, width = pixels.shape[:2]
    box = _crop_box(person, width, height)
    if box is None:
        return person
    left, top, right, bottom = box
    if (right - left) * (bottom - top) > 0.8 * width * height:
        return person
    crop = _contiguous(pixels[top:bottom, left:right])
    found = _detect_people(detector, mp, crop)
    if not found:
        return person
    best = max(found, key=lambda item: len(item["landmarks"]))
    mapped = map_person_from_crop(best, left, top, right, bottom, width, height)
    if len(mapped["landmarks"]) < max(4, len(person["landmarks"]) // 2):
        return person
    return mapped


def _crop_box(person: dict[str, Any], width: int, height: int) -> tuple[int, int, int, int] | None:
    landmarks = person.get("landmarks") or []
    if not landmarks or width <= 0 or height <= 0:
        return None
    xs = [float(item["x"]) for item in landmarks]
    ys = [float(item["y"]) for item in landmarks]
    pad_x = max(max(xs) - min(xs), 0.08) * _CROP_MARGIN
    pad_y = max(max(ys) - min(ys), 0.08) * _CROP_MARGIN
    left = max(0, int((min(xs) - pad_x) * width))
    top = max(0, int((min(ys) - pad_y) * height))
    right = min(width, int((max(xs) + pad_x) * width))
    bottom = min(height, int((max(ys) + pad_y) * height))
    if right - left < 32 or bottom - top < 32:
        return None
    return left, top, right, bottom


def _merge_people(primary: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _dedupe(primary + extra)


def _dedupe(people: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for person in people:
        if not person.get("landmarks"):
            continue
        anchor = _anchor_x(person)
        mid_y = _anchor_y(person)
        if any(abs(anchor - _anchor_x(item)) < 0.12 and abs(mid_y - _anchor_y(item)) < 0.12 for item in kept):
            continue
        kept.append(person)
    return kept


def _anchor_y(person: dict[str, Any]) -> float:
    landmarks = person.get("landmarks") or []
    if not landmarks:
        return 0.0
    return sum(float(item["y"]) for item in landmarks) / len(landmarks)


def _contiguous(pixels: Any) -> Any:
    import numpy as np

    return np.ascontiguousarray(pixels)


def _anchor_x(person: dict[str, Any]) -> float:
    landmarks = person.get("landmarks") or []
    by_index = {int(item["index"]): item for item in landmarks if "index" in item}
    if 11 in by_index and 12 in by_index:
        return (float(by_index[11]["x"]) + float(by_index[12]["x"])) / 2
    if not landmarks:
        return 0.0
    return sum(float(item["x"]) for item in landmarks) / len(landmarks)


def _muscle_labels(by_index: dict[int, dict[str, float | str | int]]) -> list[dict[str, float | str]]:
    labels: list[dict[str, float | str]] = []
    for name, a, b in _MUSCLE_DEFS:
        if a not in by_index or b not in by_index:
            continue
        pa = by_index[a]
        pb = by_index[b]
        # 大胸筋は肩の中点を少し下げる
        y_nudge = 0.03 if name == "大胸筋" else 0.0
        if name == "僧帽筋":
            y_nudge = -0.02
        labels.append(
            {
                "name": name,
                "x": _unit((float(pa["x"]) + float(pb["x"])) / 2),
                "y": _unit((float(pa["y"]) + float(pb["y"])) / 2 + y_nudge),
            }
        )
    # 左右の上腕二頭は肘寄りにずらす（三角筋と重なりすぎないように）
    adjusted: list[dict[str, float | str]] = []
    for item in labels:
        if item["name"] in {"左上腕二頭筋", "右上腕二頭筋"}:
            # 三角筋定義と同じ中点なので、肘側へ 60%
            pair = (11, 13) if item["name"].startswith("左") else (12, 14)
            if pair[0] in by_index and pair[1] in by_index:
                pa = by_index[pair[0]]
                pb = by_index[pair[1]]
                adjusted.append(
                    {
                        "name": item["name"],
                        "x": _unit(float(pa["x"]) * 0.4 + float(pb["x"]) * 0.6),
                        "y": _unit(float(pa["y"]) * 0.4 + float(pb["y"]) * 0.6),
                    }
                )
                continue
        if item["name"] in {"左三角筋", "右三角筋"}:
            pair = (11, 13) if item["name"].startswith("左") else (12, 14)
            if pair[0] in by_index and pair[1] in by_index:
                pa = by_index[pair[0]]
                pb = by_index[pair[1]]
                adjusted.append(
                    {
                        "name": item["name"],
                        "x": _unit(float(pa["x"]) * 0.7 + float(pb["x"]) * 0.3),
                        "y": _unit(float(pa["y"]) * 0.7 + float(pb["y"]) * 0.3),
                    }
                )
                continue
        adjusted.append(item)
    return adjusted


def warm() -> None:
    """起動時にモデルを読む。失敗しても解析は続けられる。"""
    _get_detector()


def _get_detector() -> Any:
    global _detector, _detector_failed
    if _detector_failed:
        return None
    if _detector is not None:
        return _detector

    model_path = next((path for path in _MODEL_CANDIDATES if path.is_file()), None)
    if model_path is None:
        logger.warning("pose skipped reason=model_missing")
        _detector_failed = True
        return None

    try:
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode
    except ImportError:
        logger.exception("pose skipped reason=mediapipe_missing")
        _detector_failed = True
        return None

    try:
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.IMAGE,
            num_poses=MAX_POSES,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
        )
        _detector = PoseLandmarker.create_from_options(options)
        logger.info("pose model loaded path=%s", model_path.name)
        return _detector
    except Exception:
        logger.exception("pose model load failed")
        _detector_failed = True
        return None


def _decode_pixels(image: bytes) -> Any:
    import io

    import numpy as np
    from PIL import Image

    with Image.open(io.BytesIO(image)) as pil:
        rgb = pil.convert("RGB")
        return np.asarray(rgb)


def _unit(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value
