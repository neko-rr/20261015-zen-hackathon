"""写真の関節からデッサン人形を組む。見えない節は補完し、inferred を付ける。"""

from __future__ import annotations

import math
from typing import Any

_PAIRS = (
    (11, 12),
    (13, 14),
    (15, 16),
    (23, 24),
    (25, 26),
    (27, 28),
    (29, 30),
    (31, 32),
)

# 子、親、胴の長さに対する比率、外側への x 成分（画像は y が下）
_LIMBS = (
    (13, 11, 0.70, 0.35),
    (15, 13, 0.65, 0.35),
    (14, 12, 0.70, -0.35),
    (16, 14, 0.65, -0.35),
    (25, 23, 0.95, 0.12),
    (27, 25, 0.90, 0.12),
    (26, 24, 0.95, -0.12),
    (28, 26, 0.90, -0.12),
    (31, 27, 0.32, 0.0),
    (32, 28, 0.32, 0.0),
)

_FINGERS = (
    ("thumb", (1, 2, 3, 4)),
    ("index", (5, 6, 7, 8)),
    ("middle", (9, 10, 11, 12)),
    ("ring", (13, 14, 15, 16)),
    ("pinky", (17, 18, 19, 20)),
)

_PART_RADIUS = {
    "torso": 0.42,
    "pelvis": 0.28,
    "clavicle": 0.10,
    "neck": 0.11,
    "upper_arm": 0.15,
    "forearm": 0.12,
    "thigh": 0.18,
    "shin": 0.13,
    "foot": 0.08,
    "finger": 0.04,
    "thumb": 0.048,
}


class _Pt:
    def __init__(self, x: float, y: float, z: float, inferred: bool) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.inferred = inferred


def empty_mannequin() -> dict[str, Any]:
    return {"joints": [], "bones": [], "head": None}


def build_mannequin(
    landmarks: list[dict[str, Any]],
    hands: list[dict[str, Any]] | None = None,
    aspect: float = 1.0,
) -> dict[str, Any]:
    """観測点と手検出から、関節と骨を返す。入力が無ければ空。

    aspect は写真の幅÷高さ。縦長の写真を正方形として扱うと、頭や胴が歪む。
    """
    if not landmarks:
        return empty_mannequin()

    raw = {}
    for item in landmarks:
        try:
            raw[int(item["index"])] = item
        except (KeyError, TypeError, ValueError):
            continue
    points = _scale_observed(raw)
    if not points:
        return empty_mannequin()

    _complete_body(points)
    if 11 not in points or 12 not in points or 23 not in points or 24 not in points:
        return empty_mannequin()

    placed = _assign_hands(points, hands or [])
    safe_aspect = aspect if aspect > 0 else 1.0
    return _assemble(points, placed, safe_aspect)


def _scale_observed(raw: dict[int, dict[str, Any]]) -> dict[int, _Pt]:
    if not raw:
        return {}
    left = raw.get(11)
    right = raw.get(12)
    if left and right:
        shoulder = math.hypot(float(left["x"]) - float(right["x"]), float(left["y"]) - float(right["y"]))
    else:
        shoulder = 0.18
    shoulder = max(shoulder, 0.05)
    zs = [float(item["z"]) for item in raw.values()]
    z_mid = sum(zs) / len(zs)
    z_reach = max(max(abs(value - z_mid) for value in zs), 0.001)
    z_scale = (shoulder * 0.9) / z_reach
    points: dict[int, _Pt] = {}
    for index, item in raw.items():
        points[index] = _Pt(
            float(item["x"]),
            float(item["y"]),
            (float(item["z"]) - z_mid) * z_scale,
            False,
        )
    return points


def _complete_body(points: dict[int, _Pt]) -> None:
    _mirror_pairs(points)
    torso = _ensure_torso(points)
    _mirror_pairs(points)
    if torso <= 0:
        return
    for child, parent, ratio, outward in _LIMBS:
        if child in points or parent not in points:
            continue
        points[child] = _extend(points, child, parent, torso * ratio, outward)
    _mirror_pairs(points)
    _ensure_head(points, torso)


def _ensure_torso(points: dict[int, _Pt]) -> float:
    shoulder = _pair_span(points, 11, 12)
    torso = _torso_length(points, shoulder)
    if 11 not in points and 12 not in points:
        origin = _first(points, (23, 24, 0, 13, 14, 15, 16))
        if origin is None:
            return 0.0
        center_x = origin.x
        top_y = origin.y + (0.12 if 0 in points else 0.0)
        half = max(shoulder, 0.08) / 2
        points[11] = _Pt(center_x - half, top_y, origin.z, True)
        points[12] = _Pt(center_x + half, top_y, origin.z, True)
    _mirror_pairs(points)
    if 23 not in points and 24 not in points and 11 in points and 12 in points:
        for src, dst in ((11, 23), (12, 24)):
            src_pt = points[src]
            points[dst] = _Pt(src_pt.x, src_pt.y + torso, src_pt.z, True)
    _mirror_pairs(points)
    return _torso_length(points, _pair_span(points, 11, 12))


def _ensure_head(points: dict[int, _Pt], torso: float) -> None:
    if any(index in points for index in (0, 7, 8)):
        return
    if 11 not in points or 12 not in points:
        return
    chest = _mid(points[11], points[12])
    lift = max(torso * 0.45, 0.08)
    points[0] = _Pt(chest.x, chest.y - lift, chest.z, True)


def _extend(points: dict[int, _Pt], child: int, parent: int, length: float, outward: float) -> _Pt:
    parent_pt = points[parent]
    grand = _grandparent(parent)
    if grand in points:
        direction = _sub(parent_pt, points[grand])
    else:
        direction = (outward, 1.0, 0.15 if child in (31, 32) else 0.0)
    if child in (31, 32):
        direction = (outward, 0.35, 0.9)
    toward = _normalize(direction, (0.0, 1.0, 0.0))
    return _Pt(
        parent_pt.x + toward[0] * length,
        parent_pt.y + toward[1] * length,
        parent_pt.z + toward[2] * length,
        True,
    )


def _grandparent(index: int) -> int:
    return {
        13: 11,
        15: 13,
        14: 12,
        16: 14,
        25: 23,
        27: 25,
        26: 24,
        28: 26,
        31: 27,
        32: 28,
    }.get(index, -1)


def _assign_hands(points: dict[int, _Pt], hands: list[dict[str, Any]]) -> dict[int, dict[int, _Pt]]:
    candidates: list[tuple[float, int, int]] = []
    parsed: list[dict[int, dict[str, Any]]] = []
    for hand_index, hand in enumerate(hands):
        landmarks = hand.get("landmarks") or []
        by_index = {}
        for item in landmarks:
            try:
                by_index[int(item["index"])] = item
            except (KeyError, TypeError, ValueError):
                continue
        parsed.append(by_index)
        if 0 not in by_index:
            continue
        origin = by_index[0]
        for wrist_index in (15, 16):
            wrist = points.get(wrist_index)
            if wrist is None:
                continue
            distance = math.hypot(wrist.x - float(origin["x"]), wrist.y - float(origin["y"]))
            candidates.append((distance, hand_index, wrist_index))
    candidates.sort()
    used_hands: set[int] = set()
    used_wrists: set[int] = set()
    assigned: dict[int, dict[int, _Pt]] = {}
    for distance, hand_index, wrist_index in candidates:
        if distance > 0.35 or hand_index in used_hands or wrist_index in used_wrists:
            continue
        placed = _translate_hand(points[wrist_index], parsed[hand_index])
        if not placed:
            continue
        used_hands.add(hand_index)
        used_wrists.add(wrist_index)
        assigned[wrist_index] = placed
    return assigned


def _translate_hand(wrist: _Pt, landmarks: dict[int, dict[str, Any]]) -> dict[int, _Pt]:
    if 0 not in landmarks:
        return {}
    origin = landmarks[0]
    dx = wrist.x - float(origin["x"])
    dy = wrist.y - float(origin["y"])
    origin_z = float(origin["z"])
    placed: dict[int, _Pt] = {}
    for index, item in landmarks.items():
        placed[index] = _Pt(
            float(item["x"]) + dx,
            float(item["y"]) + dy,
            wrist.z + (float(item["z"]) - origin_z),
            False,
        )
    return placed


def _assemble(points: dict[int, _Pt], hands: dict[int, dict[int, _Pt]], aspect: float) -> dict[str, Any]:
    sw = max(_pair_span(points, 11, 12), 0.08)
    joints: dict[str, _Pt] = {
        "pelvis": _mid(points[23], points[24], both=True),
        "chest": _mid(points[11], points[12], both=True),
        "hip_l": points[23],
        "hip_r": points[24],
        "shoulder_l": points[11],
        "shoulder_r": points[12],
        "elbow_l": points[13],
        "elbow_r": points[14],
        "wrist_l": points[15],
        "wrist_r": points[16],
        "knee_l": points[25],
        "knee_r": points[26],
        "ankle_l": points[27],
        "ankle_r": points[28],
        "foot_l": points[31],
        "foot_r": points[32],
    }
    head_pt, head_radius = _head(points, sw)
    neck_pt = _Pt(
        joints["chest"].x * 0.62 + head_pt.x * 0.38,
        joints["chest"].y * 0.62 + head_pt.y * 0.38,
        joints["chest"].z * 0.62 + head_pt.z * 0.38,
        head_pt.inferred,
    )
    joints["neck"] = neck_pt
    joints["head"] = head_pt

    for wrist_index, side in ((15, "l"), (16, "r")):
        observed = hands.get(wrist_index)
        if observed:
            _add_observed_fingers(joints, observed, side)
        else:
            _add_synth_fingers(joints, side)

    if aspect != 1.0:
        for point in joints.values():
            point.x *= aspect
            point.z *= aspect
        head_radius *= aspect

    parents = _parents(joints)
    order = _order(parents)
    hinge = _hinges(joints, parents)
    joint_rows = [
        {
            "id": joint_id,
            "parent": parents[joint_id],
            "x": _round(joints[joint_id].x),
            "y": _round(joints[joint_id].y),
            "z": _round(joints[joint_id].z),
            "inferred": joints[joint_id].inferred,
            "hinge": [_round(value) for value in hinge[joint_id]],
        }
        for joint_id in order
    ]
    sw = max(_xy_distance(joints["shoulder_l"], joints["shoulder_r"]), 0.08 * aspect)
    bones = _bones(joints, sw)
    return {
        "joints": joint_rows,
        "bones": bones,
        "head": {
            "joint_id": "head",
            "radius": _round(head_radius),
            "inferred": head_pt.inferred,
        },
        "aspect": _round(aspect),
    }


def _add_observed_fingers(joints: dict[str, _Pt], hand: dict[int, _Pt], side: str) -> None:
    for name, indices in _FINGERS:
        for step, index in enumerate(indices, start=1):
            point = hand.get(index)
            if point is None:
                continue
            joints[f"{side}_{name}_{step}"] = point


def _add_synth_fingers(joints: dict[str, _Pt], side: str) -> None:
    wrist = joints[f"wrist_{side}"]
    elbow = joints[f"elbow_{side}"]
    direction = _normalize(_sub(wrist, elbow), (0.0, 1.0, 0.0))
    length = max(_distance(wrist, elbow), 0.05)
    palm = length * 0.36
    side_axis = _normalize(_cross(direction, (0.0, 0.0, 1.0)), (1.0, 0.0, 0.0))
    sign = -1.0 if side == "l" else 1.0
    spreads = {
        "thumb": sign * 0.9,
        "index": sign * 0.42,
        "middle": sign * 0.14,
        "ring": sign * -0.14,
        "pinky": sign * -0.42,
    }
    for name, spread in spreads.items():
        if name == "thumb":
            forward = _normalize(
                (
                    side_axis[0] * sign * 0.85 + direction[0] * 0.4,
                    side_axis[1] * sign * 0.85 + direction[1] * 0.4,
                    side_axis[2] * sign * 0.85 + direction[2] * 0.4,
                ),
                direction,
            )
        else:
            forward = _normalize(
                (
                    direction[0] + side_axis[0] * spread * 0.45,
                    direction[1] + side_axis[1] * spread * 0.45,
                    direction[2] + side_axis[2] * spread * 0.45,
                ),
                direction,
            )
        cursor = (
            wrist.x + side_axis[0] * spread * palm * 0.18,
            wrist.y + side_axis[1] * spread * palm * 0.18,
            wrist.z + side_axis[2] * spread * palm * 0.18,
        )
        seg = palm * (0.4 if name == "thumb" else 0.32)
        for step in range(1, 5):
            scale = 1.0 if step == 1 else 0.82 if step == 2 else 0.7
            cursor = (
                cursor[0] + forward[0] * seg * scale,
                cursor[1] + forward[1] * seg * scale,
                cursor[2] + forward[2] * seg * scale,
            )
            joints[f"{side}_{name}_{step}"] = _Pt(cursor[0], cursor[1], cursor[2], True)


def _parents(joints: dict[str, _Pt]) -> dict[str, str | None]:
    parents: dict[str, str | None] = {
        "pelvis": None,
        "chest": "pelvis",
        "neck": "chest",
        "head": "neck",
        "hip_l": "pelvis",
        "hip_r": "pelvis",
        "knee_l": "hip_l",
        "knee_r": "hip_r",
        "ankle_l": "knee_l",
        "ankle_r": "knee_r",
        "foot_l": "ankle_l",
        "foot_r": "ankle_r",
        "shoulder_l": "chest",
        "shoulder_r": "chest",
        "elbow_l": "shoulder_l",
        "elbow_r": "shoulder_r",
        "wrist_l": "elbow_l",
        "wrist_r": "elbow_r",
    }
    for side in ("l", "r"):
        wrist_id = f"wrist_{side}"
        for name, _indices in _FINGERS:
            previous = wrist_id
            for step in range(1, 5):
                joint_id = f"{side}_{name}_{step}"
                if joint_id not in joints:
                    continue
                parents[joint_id] = previous
                previous = joint_id
    return {key: value for key, value in parents.items() if key in joints}


def _order(parents: dict[str, str | None]) -> list[str]:
    ordered: list[str] = []
    pending = set(parents)
    while pending:
        ready = [joint_id for joint_id in pending if parents[joint_id] is None or parents[joint_id] in ordered]
        if not ready:
            ordered.extend(sorted(pending))
            break
        ready.sort()
        ordered.extend(ready)
        pending -= set(ready)
    return ordered


def _hinges(joints: dict[str, _Pt], parents: dict[str, str | None]) -> dict[str, tuple[float, float, float]]:
    children: dict[str, list[str]] = {joint_id: [] for joint_id in joints}
    for joint_id, parent in parents.items():
        if parent and parent in children:
            children[parent].append(joint_id)
    hinges: dict[str, tuple[float, float, float]] = {}
    for joint_id, parent in parents.items():
        if parent is None or parent not in joints:
            hinges[joint_id] = (0.0, 0.0, 1.0)
            continue
        child_id = children.get(joint_id, [None])[0] if children.get(joint_id) else None
        bone = _sub(joints[joint_id], joints[parent])
        if child_id and child_id in joints:
            bend = _sub(joints[child_id], joints[joint_id])
        else:
            bend = (0.0, 0.0, 1.0)
        axis = _cross(bone, bend)
        if _length(axis) < 1e-6:
            axis = _cross(bone, (0.0, 0.0, 1.0))
        if _length(axis) < 1e-6:
            axis = (1.0, 0.0, 0.0)
        hinges[joint_id] = _normalize(axis, (0.0, 0.0, 1.0))
    return hinges


def _bones(joints: dict[str, _Pt], sw: float) -> list[dict[str, Any]]:
    specs = (
        ("torso", "pelvis", "chest", "torso"),
        ("pelvis_l", "pelvis", "hip_l", "pelvis"),
        ("pelvis_r", "pelvis", "hip_r", "pelvis"),
        ("neck", "chest", "neck", "neck"),
        ("clav_l", "chest", "shoulder_l", "clavicle"),
        ("clav_r", "chest", "shoulder_r", "clavicle"),
        ("arm_l", "shoulder_l", "elbow_l", "upper_arm"),
        ("arm_r", "shoulder_r", "elbow_r", "upper_arm"),
        ("fore_l", "elbow_l", "wrist_l", "forearm"),
        ("fore_r", "elbow_r", "wrist_r", "forearm"),
        ("thigh_l", "hip_l", "knee_l", "thigh"),
        ("thigh_r", "hip_r", "knee_r", "thigh"),
        ("shin_l", "knee_l", "ankle_l", "shin"),
        ("shin_r", "knee_r", "ankle_r", "shin"),
        ("foot_l", "ankle_l", "foot_l", "foot"),
        ("foot_r", "ankle_r", "foot_r", "foot"),
    )
    rows: list[dict[str, Any]] = []
    for bone_id, start, end, part in specs:
        if start not in joints or end not in joints:
            continue
        rows.append(_bone(bone_id, start, end, part, joints[end].inferred, sw))
    for side in ("l", "r"):
        previous = f"wrist_{side}"
        for name, _indices in _FINGERS:
            for step in range(1, 5):
                joint_id = f"{side}_{name}_{step}"
                if joint_id not in joints or previous not in joints:
                    previous = joint_id if joint_id in joints else previous
                    continue
                part = "thumb" if name == "thumb" else "finger"
                rows.append(
                    _bone(
                        f"{side}_{name}_{step}",
                        previous,
                        joint_id,
                        part,
                        joints[joint_id].inferred,
                        sw,
                    )
                )
                previous = joint_id
    return rows


def _bone(bone_id: str, start: str, end: str, part: str, inferred: bool, sw: float) -> dict[str, Any]:
    return {
        "id": bone_id,
        "start": start,
        "end": end,
        "part": part,
        "inferred": inferred,
        "radius": _round(sw * _PART_RADIUS[part]),
    }


def _head(points: dict[int, _Pt], sw: float) -> tuple[_Pt, float]:
    face = [points[index] for index in (0, 7, 8) if index in points]
    if not face:
        chest = _mid(points[11], points[12])
        radius = sw * 0.42
        return _Pt(chest.x, chest.y - radius * 2.2, chest.z, True), radius
    center = _Pt(
        sum(item.x for item in face) / len(face),
        sum(item.y for item in face) / len(face),
        sum(item.z for item in face) / len(face),
        all(item.inferred for item in face),
    )
    if 7 in points and 8 in points:
        radius = max(_distance(points[7], points[8]) * 0.55, sw * 0.28)
    else:
        radius = sw * 0.42
    radius = min(max(radius, sw * 0.28), sw * 0.7)
    return center, radius


def _mirror_pairs(points: dict[int, _Pt]) -> None:
    midline = _midline(points)
    for left, right in _PAIRS:
        if left in points and right not in points:
            points[right] = _mirrored(points[left], midline)
        elif right in points and left not in points:
            points[left] = _mirrored(points[right], midline)


def _mirrored(point: _Pt, midline: float) -> _Pt:
    return _Pt(midline * 2 - point.x, point.y, point.z, True)


def _midline(points: dict[int, _Pt]) -> float:
    xs = [points[index].x for index in (11, 12, 23, 24) if index in points]
    if not xs:
        return 0.5
    return sum(xs) / len(xs)


def _torso_length(points: dict[int, _Pt], shoulder: float) -> float:
    if 11 in points and 12 in points and 23 in points and 24 in points:
        return max(_distance(_mid(points[11], points[12]), _mid(points[23], points[24])), 0.08)
    return max(shoulder * 1.35, 0.2)


def _pair_span(points: dict[int, _Pt], left: int, right: int) -> float:
    if left in points and right in points:
        return max(_distance(points[left], points[right]), 0.08)
    return 0.18


def _first(points: dict[int, _Pt], indices: tuple[int, ...]) -> _Pt | None:
    for index in indices:
        if index in points:
            return points[index]
    return None


def _mid(a: _Pt, b: _Pt, both: bool = False) -> _Pt:
    inferred = a.inferred and b.inferred if both else a.inferred or b.inferred
    return _Pt((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2, inferred)


def _sub(a: _Pt, b: _Pt) -> tuple[float, float, float]:
    return (a.x - b.x, a.y - b.y, a.z - b.z)


def _distance(a: _Pt, b: _Pt) -> float:
    return _length(_sub(a, b))


def _xy_distance(a: _Pt, b: _Pt) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _length(value: tuple[float, float, float]) -> float:
    return math.sqrt(value[0] ** 2 + value[1] ** 2 + value[2] ** 2)


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalize(value: tuple[float, float, float], fallback: tuple[float, float, float]) -> tuple[float, float, float]:
    length = _length(value)
    if length < 1e-6:
        return _normalize(fallback, (0.0, 1.0, 0.0)) if fallback != value else (0.0, 1.0, 0.0)
    return (value[0] / length, value[1] / length, value[2] / length)


def _round(value: float) -> float:
    return round(float(value), 5)
