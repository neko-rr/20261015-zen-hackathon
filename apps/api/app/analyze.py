"""写真の人を、マスクと姿勢に分ける。座標は MediaPipe。名前だけ Gemini。"""

from __future__ import annotations

import logging
from typing import Any

from app.errors import system_error
from app.hands import estimate_hands
from app.label import name_subjects
from app.mannequin import build_mannequin
from app.pose import estimate_pose
from app.segment import segment_person
from app.settings import Settings

logger = logging.getLogger(__name__)


def analyze_image(settings: Settings, image: bytes, mime_type: str) -> dict[str, Any]:
    if not image:
        raise system_error("analysis_failed", "解析に失敗しました。")
    if not mime_type:
        raise system_error("analysis_failed", "解析に失敗しました。")
    try:
        pose = estimate_pose(image, mime_type)
        segment = segment_person(image, mime_type)
        hands = estimate_hands(image, mime_type)
    except Exception as exc:
        logger.exception("observe failed vision=mediapipe")
        raise system_error("analysis_failed", "解析に失敗しました。") from exc

    raw_people = list(pose.get("people") or [])
    if not raw_people and pose.get("landmarks"):
        raw_people = [
            {
                "landmarks": pose.get("landmarks") or [],
                "edges": pose.get("edges") or [],
                "muscles": pose.get("muscles") or [],
            }
        ]
    assigned = _assign_hands(raw_people, hands)
    aspect = _image_aspect(image)
    built: list[dict[str, Any]] = []
    for index, person in enumerate(raw_people):
        person_hands = assigned[index] if index < len(assigned) else []
        mannequin = build_mannequin(person.get("landmarks") or [], person_hands, aspect=aspect)
        built.append(
            {
                "object_id": f"obj_{index + 1}",
                "landmarks": person.get("landmarks") or [],
                "edges": person.get("edges") or [],
                "muscles": person.get("muscles") or [],
                "hands": person_hands,
                "mannequin": mannequin,
            }
        )
    named = name_subjects(settings, image, mime_type)
    objects = _objects(segment, built, named)
    first = built[0] if built else None
    muscles: list[dict[str, Any]] = []
    for index, person in enumerate(built):
        for item in person.get("muscles") or []:
            muscles.append({**item, "person_index": index})
    pose_out = {
        "landmarks": (first or {}).get("landmarks") or [],
        "edges": (first or {}).get("edges") or [],
        "muscles": muscles,
        "hands": hands,
        "mannequin": (first or {}).get("mannequin"),
        "people": built,
    }
    inferred = sum(
        1
        for person in built
        for bone in (person.get("mannequin") or {}).get("bones") or []
        if bone.get("inferred")
    )
    logger.info(
        "observe vision=mediapipe object_count=%s people=%s pose_landmarks=%s contour=%s hands=%s inferred_bones=%s",
        len(objects),
        len(built),
        len(pose_out["landmarks"]),
        len(segment.get("contour") or []),
        len(hands),
        inferred,
    )
    return {"objects": objects, "pose": pose_out}


def _assign_hands(
    people: list[dict[str, Any]],
    hands: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """各手を、一番近い手首の人に付ける。遠い手は捨てる。"""
    assigned: list[list[dict[str, Any]]] = [[] for _ in people]
    wrists: list[tuple[int, float, float]] = []
    for index, person in enumerate(people):
        for item in person.get("landmarks") or []:
            if int(item.get("index", -1)) not in (15, 16):
                continue
            wrists.append((index, float(item["x"]), float(item["y"])))
    taken: set[int] = set()
    ranked: list[tuple[float, int, int]] = []
    for hand_index, hand in enumerate(hands):
        points = hand.get("landmarks") or []
        if not points:
            continue
        hx = float(points[0].get("x", 0))
        hy = float(points[0].get("y", 0))
        for person_index, x, y in wrists:
            ranked.append(((hx - x) ** 2 + (hy - y) ** 2, hand_index, person_index))
    ranked.sort(key=lambda item: item[0])
    for distance, hand_index, person_index in ranked:
        if hand_index in taken or distance > 0.12**2:
            continue
        taken.add(hand_index)
        assigned[person_index].append(hands[hand_index])
    return assigned


def _objects(
    segment: dict[str, Any],
    people: list[dict[str, Any]],
    named: dict[str, Any],
) -> list[dict[str, Any]]:
    contour = segment.get("contour") or []
    labels = _people_labels(named, len(people))
    rows: list[dict[str, Any]] = []
    for index, person in enumerate(people):
        landmarks = person.get("landmarks") or []
        muscles = person.get("muscles") or []
        if not landmarks and not (index == 0 and contour):
            continue
        joints = [
            {"name": str(item["name"]), "x": float(item["x"]), "y": float(item["y"])}
            for item in landmarks
        ]
        muscle_points = [
            {"name": str(item["name"]), "x": float(item["x"]), "y": float(item["y"])}
            for item in muscles
        ]
        rows.append(
            {
                "object_id": person.get("object_id") or f"obj_{index + 1}",
                "label": labels[index] if index < len(labels) else "人",
                "kind": "person",
                "is_primary": not rows,
                "box": segment.get("box") if index == 0 else _box_from_landmarks(landmarks),
                "joints": joints,
                "muscles": muscle_points,
                "contour": contour if index == 0 and len(contour) >= 3 else [],
            }
        )
    if not rows and contour:
        rows.append(
            {
                "object_id": "obj_1",
                "label": _people_labels(named, 1)[0],
                "kind": "person",
                "is_primary": True,
                "box": segment.get("box"),
                "joints": [],
                "muscles": [],
                "contour": contour if len(contour) >= 3 else [],
            }
        )
    for item in named.get("others") or []:
        rows.append(
            {
                "object_id": f"obj_{len(rows) + 1}",
                "label": item["label"],
                "kind": item["kind"],
                "is_primary": not rows,
                "box": None,
                "joints": [],
                "muscles": [],
                "contour": [],
            }
        )
    return rows


def _people_labels(named: dict[str, Any], count: int) -> list[str]:
    """左からの呼び方。名前が無い複数人は左から何人目か。"""
    people = list(named.get("people") or [])
    if not people and (named.get("person_label") or named.get("public_name")):
        people = [{"label": named.get("person_label") or "", "public_name": named.get("public_name") or ""}]
    labels: list[str] = []
    for index in range(count):
        item = people[index] if index < len(people) else {}
        label = _person_label(item)
        if label == "人" and count > 1:
            label = f"左から{index + 1}人目"
        labels.append(label)
    return labels


def _person_label(named: dict[str, Any]) -> str:
    """見た目の呼び方。確かな公開人物名だけを足す。無ければ人。"""
    base = str(named.get("label") or named.get("person_label") or "").strip() or "人"
    public = str(named.get("public_name") or "").strip()
    if not public or public in base:
        return base
    return f"{base}（{public}）"


def _box_from_landmarks(landmarks: list[dict[str, Any]]) -> dict[str, float] | None:
    if not landmarks:
        return None
    xs = [float(item["x"]) for item in landmarks]
    ys = [float(item["y"]) for item in landmarks]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return {
        "x": min_x,
        "y": min_y,
        "width": max(max_x - min_x, 0.01),
        "height": max(max_y - min_y, 0.01),
    }


def _image_aspect(image: bytes) -> float:
    """幅÷高さ。読めなければ正方形として扱う。"""
    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(image)) as picture:
            width, height = picture.size
    except Exception:
        return 1.0
    if height <= 0 or width <= 0:
        return 1.0
    return width / height
