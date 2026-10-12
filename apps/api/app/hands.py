"""MediaPipe Hand Landmarker で左右の指関節を取る。失敗時は空。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_MODEL_CANDIDATES = [
    Path(__file__).resolve().parent / "models" / "hand_landmarker.task",
]

_detector = None
_detector_failed = False


def empty_hands() -> list[dict[str, Any]]:
    return []


def estimate_hands(image: bytes, mime_type: str) -> list[dict[str, Any]]:
    """写っている手。モデルが無い、手が無いときは空リスト。"""
    if not image or not mime_type:
        return empty_hands()
    detector = _get_detector()
    if detector is None:
        return empty_hands()

    try:
        import mediapipe as mp
    except ImportError:
        logger.exception("hands skipped reason=mediapipe_missing")
        return empty_hands()

    try:
        pixels = _decode_pixels(image)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=pixels)
        result = detector.detect(mp_image)
    except Exception:
        logger.exception("hands detect failed")
        return empty_hands()

    found: list[dict[str, Any]] = []
    landmarks = result.hand_landmarks or []
    handedness = result.handedness or []
    for index, hand in enumerate(landmarks):
        label = "left"
        score = 0.0
        if index < len(handedness) and handedness[index]:
            category = handedness[index][0]
            raw = str(getattr(category, "category_name", "") or "").lower()
            label = "right" if raw == "right" else "left"
            score = float(getattr(category, "score", 0.0) or 0.0)
        points = [
            {
                "index": point_index,
                "x": _unit(float(point.x)),
                "y": _unit(float(point.y)),
                "z": float(point.z),
            }
            for point_index, point in enumerate(hand)
        ]
        found.append({"side": label, "score": score, "landmarks": points})
    logger.info("hands count=%s", len(found))
    return found


def _get_detector() -> Any:
    global _detector, _detector_failed
    if _detector_failed:
        return None
    if _detector is not None:
        return _detector

    model_path = next((path for path in _MODEL_CANDIDATES if path.is_file()), None)
    if model_path is None:
        logger.warning("hands skipped reason=model_missing")
        _detector_failed = True
        return None

    try:
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
    except ImportError:
        logger.exception("hands skipped reason=mediapipe_missing")
        _detector_failed = True
        return None

    try:
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.IMAGE,
            num_hands=8,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
        )
        _detector = HandLandmarker.create_from_options(options)
        logger.info("hands model loaded path=%s", model_path.name)
        return _detector
    except Exception:
        logger.exception("hands model load failed")
        _detector_failed = True
        return None


def _decode_pixels(image: bytes) -> Any:
    import io

    import numpy as np
    from PIL import Image

    with Image.open(io.BytesIO(image)) as pil:
        return np.asarray(pil.convert("RGB"))


def _unit(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value
