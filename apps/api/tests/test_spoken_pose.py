import math

from app.mannequin import standing_mannequin
from app.pose_catalog import catalog_size, lookup_catalog
from app.spoken_pose import ensure_pose_options, instruct_pose, pose_from_text, poses_from_text


def test_words_become_known_joint_angles() -> None:
    parsed = pose_from_text(
        '{"summary":"右腕を上げる","bends":{"shoulder_r":90,"elbow_r":200,"nose":10},"upper_deg":80}'
    )
    assert "shoulder_r" in parsed["bends"]
    assert "nose" not in parsed["bends"]
    assert parsed["bends"]["elbow_r"] <= 2.62
    assert parsed["upper_deg"] == 70
    assert parsed["summary"] == "右腕を上げる"


def test_three_pose_choices() -> None:
    raw = """{"options":[
      {"summary":"右手","bends":{"shoulder_r":140}},
      {"summary":"左手","bends":{"shoulder_l":140}},
      {"summary":"右手","bends":{"shoulder_r":140}},
      {"summary":"両手","bends":{"shoulder_l":150,"shoulder_r":150}}
    ]}"""
    options = poses_from_text(raw)
    assert len(options) == 3
    assert options[0]["summary"] == "右手"
    assert options[2]["summary"] == "両手"


def test_sitting_words_get_three_sits_when_model_stands() -> None:
    standing = [{"summary": "立ち", "mirrored": False, "upper_deg": 0, "lower_deg": 0, "bends": {}}]
    options = ensure_pose_options("座っている人", standing)
    assert len(options) == 3
    assert all(item["bends"].get("knee_l", 0) >= math.radians(60) for item in options)


def test_raised_model_pose_is_kept() -> None:
    raised = pose_from_text('{"summary":"右手を挙げる","bends":{"shoulder_r":140}}')
    options = ensure_pose_options("手を挙げている人", [raised])
    assert options[0]["summary"] == "右手を挙げる"


def test_catalog_has_about_ten_poses() -> None:
    assert catalog_size() >= 10


def test_sitting_words_use_the_catalog() -> None:
    class _Settings:
        def require_gemini(self) -> None:
            raise AssertionError("登録にある言葉で Gemini を呼ばない")

    result = instruct_pose("座っている人", _Settings())  # type: ignore[arg-type]
    assert result["pose_source"] == "catalog"
    assert result["options"][0]["summary"] == "椅子に座る"
    assert len(result["options"]) == 3


def test_floor_and_left_hand_win_their_words() -> None:
    floor = lookup_catalog("床に座っている人")
    left = lookup_catalog("左手を挙げている人")
    assert floor is not None and floor[0]["summary"] == "床に座る"
    assert left is not None and left[0]["summary"] == "左手を挙げる"


def test_two_pose_families_are_not_forced() -> None:
    assert lookup_catalog("座って手を挙げる") is None
    assert lookup_catalog("ジャンプする人") is None


def test_standing_doll_has_elbows() -> None:
    doll = standing_mannequin()
    ids = {item["id"]: item for item in doll["joints"]}
    assert "elbow_l" in ids
    assert ids["hip_l"]["hinge"] == [1.0, 0.0, 0.0]
    assert ids["knee_l"]["hinge"] == [-1.0, 0.0, 0.0]
