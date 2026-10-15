from app.limbs import apply_limb_repairs, arm_pose, audit_limbs, limbs_from_text, refine_limbs
from app.pose import parts_from_landmarks
from app.settings import Settings


def _point(index: int, x: float, y: float) -> dict:
    return {"index": index, "x": x, "y": y, "z": 0.0, "visibility": 1.0}


def _body() -> list[dict]:
    return [
        _point(11, 0.40, 0.30),
        _point(12, 0.60, 0.30),
        _point(13, 0.34, 0.45),
        _point(14, 0.66, 0.45),
        _point(15, 0.32, 0.58),
        _point(16, 0.68, 0.58),
        _point(23, 0.44, 0.55),
        _point(24, 0.56, 0.55),
        _point(25, 0.44, 0.72),
        _point(26, 0.56, 0.72),
        _point(27, 0.44, 0.90),
        _point(28, 0.56, 0.90),
    ]


def _settings() -> Settings:
    return Settings(
        cors_origins=["http://127.0.0.1:3000"],
        gemini_model="",
        cloud_project="",
        use_enterprise=False,
        session_signing_secret="test",
        session_cookie_secure=False,
    )


def test_normal_body_drops_nothing() -> None:
    rows = _body()
    kept, report = refine_limbs(_settings(), b"", "image/png", rows)
    assert report["dropped"] == []
    assert report["swapped_arms"] is False
    assert {item["index"] for item in kept} == {item["index"] for item in rows}
    assert audit_limbs(rows) == []


def test_absurd_wrist_is_dropped() -> None:
    rows = _body()
    rows[4] = _point(15, 2.4, 0.30)
    issues = audit_limbs(rows)
    assert any(issue["kind"] == "long" and 15 in issue["indices"] for issue in issues)
    kept, swapped = apply_limb_repairs(rows, issues, None)
    assert swapped is False
    assert 15 not in {item["index"] for item in kept}
    assert 11 in {item["index"] for item in kept}


def test_opposite_arm_states_swap() -> None:
    rows = _body()
    placed = {
        13: (0.64, 0.42),
        14: (0.36, 0.18),
        15: (0.66, 0.55),
        16: (0.34, 0.08),
    }
    for item in rows:
        if item["index"] in placed:
            item["x"], item["y"] = placed[item["index"]]
    assert arm_pose(rows, "left") == "down"
    assert arm_pose(rows, "right") == "raised"
    view = {"left_arm": "raised", "right_arm": "down", "left_leg": "down", "right_leg": "down"}
    kept, swapped = apply_limb_repairs(rows, audit_limbs(rows), view)
    assert swapped is True
    assert arm_pose(kept, "left") == "raised"
    assert arm_pose(kept, "right") == "down"
    muscles = parts_from_landmarks(kept)["muscles"]
    left = next(item for item in muscles if item["name"] == "左三角筋")
    by_index = {item["index"]: item for item in kept}
    assert abs(left["x"] - by_index[11]["x"]) < abs(left["x"] - by_index[12]["x"])


def test_border_knee_is_dropped() -> None:
    rows = _body()
    for item in rows:
        if item["index"] in (25, 26):
            item["y"] = 1.0
            item["visibility"] = 0.64
    kept, _report = refine_limbs(_settings(), b"", "image/png", rows)
    indexes = {item["index"] for item in kept}
    assert 25 not in indexes
    assert 26 not in indexes
    assert 23 in indexes


def test_limb_text_drops_coordinates() -> None:
    found = limbs_from_text('{"left_arm":"raised","right_arm":"down","x":0.2,"left_leg":"hidden","right_leg":"down"}')
    assert found == {"left_arm": "raised", "right_arm": "down", "left_leg": "hidden", "right_leg": "down"}
