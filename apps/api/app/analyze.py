"""写真の人を、マスクと姿勢に分ける。座標の推定に Gemini は使わない。"""

from __future__ import annotations

import logging
from typing import Any

from app.errors import system_error
from app.pose import empty_pose, estimate_pose
from app.segment import segment_person
from app.settings import Settings

logger = logging.getLogger(__name__)


def analyze_image(settings: Settings, image: bytes, mime_type: str) -> dict[str, Any]:
    if not image:
        raise system_error("analysis_failed", "解析に失敗しました。")
    if not mime_type:
        raise system_error("analysis_failed", "解析に失敗しました。")
    # 見る段は MediaPipe。settings は呼び出し互換のため受け取る。
    _ = settings

    try:
        pose = estimate_pose(image, mime_type)
        segment = segment_person(image, mime_type)
    except Exception as exc:
        logger.exception("observe failed vision=mediapipe")
        raise system_error("analysis_failed", "解析に失敗しました。") from exc

    objects = _person_object(segment, pose)
    logger.info(
        "observe vision=mediapipe object_count=%s pose_landmarks=%s contour=%s",
        len(objects),
        len(pose.get("landmarks") or []),
        len(segment.get("contour") or []),
    )
    return {"objects": objects, "pose": pose if pose.get("landmarks") else empty_pose()}


def _person_object(segment: dict[str, Any], pose: dict[str, Any]) -> list[dict[str, Any]]:
    contour = segment.get("contour") or []
    landmarks = pose.get("landmarks") or []
    muscles = pose.get("muscles") or []
    if not contour and not landmarks:
        return []

    joints = [
        {"name": str(item["name"]), "x": float(item["x"]), "y": float(item["y"])}
        for item in landmarks
    ]
    muscle_points = [
        {"name": str(item["name"]), "x": float(item["x"]), "y": float(item["y"])}
        for item in muscles
    ]
    return [
        {
            "object_id": "obj_1",
            "label": "人",
            "kind": "person",
            "is_primary": True,
            "box": segment.get("box"),
            "joints": joints,
            "muscles": muscle_points,
            "contour": contour if len(contour) >= 3 else [],
        }
    ]
