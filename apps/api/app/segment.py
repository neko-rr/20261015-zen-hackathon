"""人の前景マスクから輪郭を取る。失敗時は空。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_CANDIDATES = [
    Path(__file__).resolve().parent / "models" / "selfie_segmenter.tflite",
    Path(__file__).resolve().parents[1] / "models" / "selfie_segmenter.tflite",
]

_segmenter = None
_segmenter_failed = False

_NEIGHBORS = (
    (-1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, -1),
)


def empty_segment() -> dict[str, Any]:
    return {"contour": [], "box": None}


def segment_person(image: bytes, mime_type: str) -> dict[str, Any]:
    """写っている人の輪郭。全身でなくても、マスクにある範囲だけ返す。"""
    if not image:
        return empty_segment()
    segmenter = _get_segmenter()
    if segmenter is None:
        return empty_segment()

    try:
        import mediapipe as mp
    except ImportError:
        logger.exception("segment skipped reason=mediapipe_missing")
        return empty_segment()

    try:
        pixels = _decode_pixels(image)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=pixels)
        result = segmenter.segment(mp_image)
        masks = result.confidence_masks or []
        if not masks:
            return empty_segment()
        mask = np.asarray(masks[0].numpy_view())
        if mask.ndim == 3:
            mask = mask[:, :, 0]
    except Exception:
        logger.exception("segment failed")
        return empty_segment()

    contour = contour_from_mask(mask > 0.5)
    box = _box_from_contour(contour)
    logger.info("segment contour_points=%s", len(contour))
    return {"contour": contour, "box": box}


def contour_from_mask(mask: np.ndarray, max_points: int = 80) -> list[dict[str, float]]:
    """二値マスクの外周を、0〜1 の点列にする。"""
    if mask.ndim != 2 or mask.size == 0 or not np.any(mask):
        return []

    small = _resize_mask(mask.astype(bool), max_edge=200)
    height, width = small.shape
    start = _boundary_start(small)
    if start is None:
        return []

    raw = _trace_boundary(small, start)
    if len(raw) < 8:
        return []

    simplified = _rdp(raw, epsilon=1.5)
    if len(simplified) > max_points:
        step = max(1, len(simplified) // max_points)
        simplified = simplified[::step]
    if len(simplified) < 3:
        return []

    return [
        {"x": _unit(x / width), "y": _unit(y / height)}
        for y, x in simplified
    ]


def _resize_mask(mask: np.ndarray, max_edge: int) -> np.ndarray:
    height, width = mask.shape
    scale = max_edge / max(height, width)
    if scale >= 1:
        return mask
    from PIL import Image

    image = Image.fromarray(mask.astype(np.uint8) * 255)
    resized = image.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.BILINEAR)
    return np.asarray(resized) > 127


def _boundary_start(mask: np.ndarray) -> tuple[int, int] | None:
    height, width = mask.shape
    for y in range(height):
        for x in range(width):
            if mask[y, x] and _touches_outside(mask, y, x):
                return (y, x)
    return None


def _touches_outside(mask: np.ndarray, y: int, x: int) -> bool:
    height, width = mask.shape
    for dy, dx in _NEIGHBORS:
        ny, nx = y + dy, x + dx
        if ny < 0 or nx < 0 or ny >= height or nx >= width or not mask[ny, nx]:
            return True
    return False


def _trace_boundary(mask: np.ndarray, start: tuple[int, int]) -> list[tuple[int, int]]:
    height, width = mask.shape
    points = [start]
    prev_dir = 6
    current = start
    for _ in range(height * width):
        found = None
        for offset in range(8):
            direction = (prev_dir + offset) % 8
            dy, dx = _NEIGHBORS[direction]
            ny, nx = current[0] + dy, current[1] + dx
            if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and _touches_outside(mask, ny, nx):
                found = ((ny, nx), direction)
                break
        if found is None:
            break
        nxt, direction = found
        if nxt == start and len(points) > 8:
            break
        points.append(nxt)
        current = nxt
        prev_dir = (direction + 5) % 8
        if len(points) > 5000:
            break
    return points


def _rdp(points: list[tuple[int, int]], epsilon: float) -> list[tuple[int, int]]:
    if len(points) < 3:
        return points
    start = points[0]
    end = points[-1]
    max_dist = -1.0
    index = 0
    for i in range(1, len(points) - 1):
        dist = _point_line_dist(points[i], start, end)
        if dist > max_dist:
            max_dist = dist
            index = i
    if max_dist > epsilon:
        left = _rdp(points[: index + 1], epsilon)
        right = _rdp(points[index:], epsilon)
        return left[:-1] + right
    return [start, end]


def _point_line_dist(point: tuple[int, int], start: tuple[int, int], end: tuple[int, int]) -> float:
    y, x = point
    y1, x1 = start
    y2, x2 = end
    length = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5
    if length == 0:
        return ((y - y1) ** 2 + (x - x1) ** 2) ** 0.5
    return abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / length


def _box_from_contour(contour: list[dict[str, float]]) -> dict[str, float] | None:
    if len(contour) < 3:
        return None
    xs = [point["x"] for point in contour]
    ys = [point["y"] for point in contour]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return {
        "x": min_x,
        "y": min_y,
        "width": max(max_x - min_x, 0.01),
        "height": max(max_y - min_y, 0.01),
    }


def _get_segmenter() -> Any:
    global _segmenter, _segmenter_failed
    if _segmenter_failed:
        return None
    if _segmenter is not None:
        return _segmenter

    model_path = next((path for path in _MODEL_CANDIDATES if path.is_file()), None)
    if model_path is None:
        logger.warning("segment skipped reason=model_missing")
        _segmenter_failed = True
        return None

    try:
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import ImageSegmenter, ImageSegmenterOptions, RunningMode
    except ImportError:
        logger.exception("segment skipped reason=mediapipe_missing")
        _segmenter_failed = True
        return None

    try:
        options = ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.IMAGE,
            output_confidence_masks=True,
            output_category_mask=False,
        )
        _segmenter = ImageSegmenter.create_from_options(options)
        logger.info("segment model loaded path=%s", model_path.name)
        return _segmenter
    except Exception:
        logger.exception("segment model load failed")
        _segmenter_failed = True
        return None


def _decode_pixels(image: bytes) -> Any:
    import io

    from PIL import Image

    with Image.open(io.BytesIO(image)) as pil:
        return np.asarray(pil.convert("RGB"))


def _unit(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value
