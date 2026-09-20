"""写真を物体の層と関節に分ける。"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.errors import system_error
from app.review import review_objects
from app.settings import MIN_CONFIDENCE, Settings

logger = logging.getLogger(__name__)


class Box(BaseModel):
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0


class Joint(BaseModel):
    name: str = ""
    x: float = 0
    y: float = 0
    confidence: float = 0


class Point(BaseModel):
    x: float = 0
    y: float = 0


class RawObject(BaseModel):
    label: str = ""
    kind: str = "other"
    confidence: float = 0
    box: Box = Field(default_factory=Box)
    joints: list[Joint] = Field(default_factory=list)
    muscles: list[Joint] = Field(default_factory=list)
    contour: list[Point] = Field(default_factory=list)


class RawAnalysis(BaseModel):
    objects: list[RawObject] = Field(default_factory=list)


_PROMPT = """絵の資料用に、画像内の物体を列挙してください。
kind は person、animal、other のいずれか。
label は日本語の短い名前。
座標は、画像の幅と高さを 1 とした比率（0 以上 1 以下）。
person と animal には joints（骨格の関節）と muscles（主な筋肉の位置）を入れる。
other には contour（輪郭をたどる点を8個以上）を入れる。
見えない点は入れない。confidence は 0 以上 1 以下。
"""


def analyze_image(settings: Settings, image: bytes, mime_type: str) -> list[dict[str, Any]]:
    if not image:
        raise system_error("analysis_failed", "解析に失敗しました。")
    if not mime_type:
        raise system_error("analysis_failed", "解析に失敗しました。")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        logger.exception("gemini sdk missing")
        raise system_error("analysis_failed", "解析に失敗しました。") from exc

    try:
        client = genai.Client(http_options=types.HttpOptions(timeout=60_000))
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                types.Part.from_bytes(data=image, mime_type=mime_type),
                _PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RawAnalysis,
            ),
        )
        parsed = RawAnalysis.model_validate_json(response.text or "{}")
    except Exception as exc:
        logger.exception("observe failed model=%s", settings.gemini_model)
        raise system_error("analysis_failed", "解析に失敗しました。") from exc

    objects = _select_objects(parsed.objects)
    logger.info(
        "observe model=%s object_count=%s",
        settings.gemini_model,
        len(objects),
    )
    return review_objects(objects)


def _select_objects(raw_objects: list[RawObject]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for index, item in enumerate(raw_objects, start=1):
        label = item.label.strip() or "名称不明"
        box = item.box if item.confidence >= MIN_CONFIDENCE else None
        joints = _named_points(item.joints)
        muscles = _named_points(item.muscles)
        contour = _contour(item.contour)
        cleaned.append(
            {
                "object_id": f"obj_{index}",
                "label": label,
                "kind": item.kind if item.kind in {"person", "animal", "other"} else "other",
                "is_primary": False,
                "box": _box_or_none(box),
                "joints": joints,
                "muscles": muscles,
                "contour": contour,
            }
        )

    primary_index = _primary_index(cleaned)
    if primary_index is not None:
        cleaned[primary_index]["is_primary"] = True
    return cleaned


def _named_points(points: list[Joint]) -> list[dict[str, float | str]]:
    return [
        {"name": point.name.strip(), "x": _unit(point.x), "y": _unit(point.y)}
        for point in points
        if point.name.strip() and point.confidence >= MIN_CONFIDENCE
    ]


def _contour(points: list[Point]) -> list[dict[str, float]]:
    cleaned = [{"x": _unit(point.x), "y": _unit(point.y)} for point in points]
    if len(cleaned) < 3:
        return []
    return cleaned


def _primary_index(objects: list[dict[str, Any]]) -> int | None:
    for kind in ("person", "animal"):
        for index, item in enumerate(objects):
            if item["kind"] == kind:
                return index
    if objects:
        return 0
    return None


def _box_or_none(box: Box | None) -> dict[str, float] | None:
    if box is None:
        return None
    return {
        "x": _unit(box.x),
        "y": _unit(box.y),
        "width": _unit(box.width),
        "height": _unit(box.height),
    }


def _unit(value: float) -> float:
    if value < 0:
        return 0
    if value > 1:
        return 1
    return value
