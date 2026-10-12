"""デッサン人形の補完。見えない側は反転し、指が無いときは補完する。"""

from app.mannequin import build_mannequin, empty_mannequin


def _point(index: int, x: float, y: float, z: float = 0.0) -> dict:
    return {"index": index, "name": "pt", "x": x, "y": y, "z": z, "visibility": 1.0}


def _standing() -> list[dict]:
    return [
        _point(0, 0.50, 0.18),
        _point(7, 0.46, 0.20),
        _point(8, 0.54, 0.20),
        _point(11, 0.42, 0.30),
        _point(12, 0.58, 0.30),
        _point(13, 0.38, 0.42),
        _point(14, 0.62, 0.42),
        _point(15, 0.36, 0.54),
        _point(16, 0.64, 0.54),
        _point(23, 0.44, 0.56),
        _point(24, 0.56, 0.56),
        _point(25, 0.44, 0.72),
        _point(26, 0.56, 0.72),
        _point(27, 0.44, 0.88),
        _point(28, 0.56, 0.88),
    ]


def _bone(mannequin: dict, bone_id: str) -> dict:
    return next(item for item in mannequin["bones"] if item["id"] == bone_id)


def _joint(mannequin: dict, joint_id: str) -> dict:
    return next(item for item in mannequin["joints"] if item["id"] == joint_id)


def test_empty_pose_has_no_doll() -> None:
    assert build_mannequin([]) == empty_mannequin()


def test_visible_arm_stays_observed_and_fingers_are_filled() -> None:
    mannequin = build_mannequin(_standing())
    assert _bone(mannequin, "fore_r")["inferred"] is False
    assert _bone(mannequin, "arm_r")["inferred"] is False
    assert _joint(mannequin, "r_index_4")["inferred"] is True
    assert _bone(mannequin, "r_index_4")["inferred"] is True
    assert mannequin["head"]["inferred"] is False
    assert mannequin["head"]["radius"] > 0


def test_missing_left_arm_is_mirrored_and_marked() -> None:
    landmarks = [item for item in _standing() if item["index"] not in (13, 15)]
    mannequin = build_mannequin(landmarks)
    elbow = _joint(mannequin, "elbow_l")
    wrist = _joint(mannequin, "wrist_l")
    assert elbow["inferred"] is True
    assert wrist["inferred"] is True
    assert elbow["x"] == round(1.0 - 0.62, 5)
    assert wrist["x"] == round(1.0 - 0.64, 5)
    assert _bone(mannequin, "fore_l")["inferred"] is True
    assert _bone(mannequin, "fore_r")["inferred"] is False


def test_detected_hand_fingers_are_not_inferred() -> None:
    hand = {
        "side": "left",
        "score": 0.9,
        "landmarks": [
            {"index": index, "x": 0.36 + (index % 5) * 0.008, "y": 0.54 + (index // 5) * 0.012, "z": 0.0}
            for index in range(21)
        ],
    }
    mannequin = build_mannequin(_standing(), [hand])
    assert _joint(mannequin, "l_index_3")["inferred"] is False
    assert _bone(mannequin, "l_middle_2")["inferred"] is False
    assert _joint(mannequin, "r_index_3")["inferred"] is True


def test_portrait_aspect_keeps_height_and_narrows_width() -> None:
    square = build_mannequin(_standing())
    portrait = build_mannequin(_standing(), aspect=0.5)
    assert portrait["aspect"] == 0.5
    assert _joint(portrait, "elbow_r")["x"] == round(_joint(square, "elbow_r")["x"] * 0.5, 5)
    assert _joint(portrait, "elbow_r")["y"] == _joint(square, "elbow_r")["y"]
