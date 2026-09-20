"""検める。Gemini の JSON だけを見て、枠と関節を出すか決める。"""

import logging
from typing import Any

from app.jev_client import ACT_THRESHOLD, ask, jev_available, read_choice, read_noul

logger = logging.getLogger(__name__)

_MAX_OBJECTS = 8


def review_objects(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Jev が使えない、または失敗したときは Gemini の結果をそのまま返す。"""
    if not objects:
        return objects
    if not jev_available():
        logger.info("review skipped reason=config_missing")
        return objects

    sample = objects[:_MAX_OBJECTS]
    try:
        from typesafe_sdk import Choice, Noul
    except ImportError:
        logger.exception("review skipped reason=sdk_missing")
        return objects

    try:
        response = ask(_state(sample), _questions(sample, Choice, Noul))
    except Exception:
        logger.exception("review skipped reason=jev_failed")
        return objects

    _apply(objects, response)
    logger.info("review model=jev objects=%s", len(sample))
    return objects


def _state(objects: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "objects": [
            {
                "object_id": item["object_id"],
                "label": item["label"],
                "kind": item["kind"],
                "box": item["box"],
                "joint_names": [joint["name"] for joint in item["joints"]],
            }
            for item in objects
        ]
    }


def _questions(objects: list[dict[str, Any]], choice_type: Any, noul_type: Any) -> dict[str, Any]:
    criteria = {item["object_id"]: item["label"] for item in objects}
    criteria["none"] = "No clear person or animal subject"
    questions: dict[str, Any] = {
        "primary": choice_type(
            instructions=(
                "Which object_id is the main person or animal? "
                "Choose none when there is no clear main subject."
            ),
            criteria=criteria,
        )
    }
    for item in objects:
        object_id = item["object_id"]
        if item["box"] is not None:
            questions[f"{object_id}_draw_box"] = noul_type(
                instructions=(
                    f"The box for `{object_id}` is reliable enough to draw. "
                    "False means show the name only."
                ),
            )
        if item["joints"]:
            questions[f"{object_id}_draw_joints"] = noul_type(
                instructions=(
                    f"The joint names for `{object_id}` form one coherent body and should be drawn."
                ),
            )
    return questions


def _apply(objects: list[dict[str, Any]], response: Any) -> None:
    chosen = read_choice(response, "primary")
    if chosen is not None:
        object_id, confidence = chosen
        if object_id != "none" and confidence >= ACT_THRESHOLD:
            known = {item["object_id"] for item in objects}
            if object_id in known:
                for item in objects:
                    item["is_primary"] = item["object_id"] == object_id

    for item in objects:
        object_id = item["object_id"]
        draw_box = read_noul(response, f"{object_id}_draw_box")
        if draw_box is not None and draw_box < ACT_THRESHOLD:
            item["box"] = None
        draw_joints = read_noul(response, f"{object_id}_draw_joints")
        if draw_joints is not None and draw_joints < ACT_THRESHOLD:
            item["joints"] = []
