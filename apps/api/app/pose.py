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


def empty_pose() -> dict[str, Any]:
    return {"landmarks": [], "edges": [], "muscles": []}


def estimate_pose(image: bytes, mime_type: str) -> dict[str, Any]:
    """画像から姿勢を推定する。取れなければ空。"""
    if not image:
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
        pixels = _decode_pixels(image)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=pixels)
        result = detector.detect(mp_image)
    except Exception:
        logger.exception("pose detect failed")
        return empty_pose()

    if not result.pose_landmarks:
        return empty_pose()

    raw = result.pose_landmarks[0]
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

    by_index = {int(item["index"]): item for item in landmarks}
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

    muscles = _muscle_labels(by_index)
    logger.info("pose landmarks=%s edges=%s muscles=%s", len(landmarks), len(edges), len(muscles))
    return {"landmarks": landmarks, "edges": edges, "muscles": muscles}


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
            num_poses=1,
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
