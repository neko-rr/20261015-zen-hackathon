from app.facing import decide, facing_from_text, judge_landmarks, needs_swap, swap_sides


def _point(index: int, x: float, y: float, z: float) -> dict:
    return {"index": index, "x": x, "y": y, "z": z, "visibility": 1}


def _front() -> list[dict]:
    # カメラに正対。左肩は画像の右。鼻は肩より手前（z が小さい）。
    return [
        _point(0, 0.5, 0.2, -0.2),
        _point(11, 0.62, 0.35, 0.0),
        _point(12, 0.38, 0.35, 0.0),
        _point(23, 0.58, 0.6, 0.0),
        _point(24, 0.42, 0.6, 0.0),
    ]


def _back() -> list[dict]:
    return [
        _point(0, 0.5, 0.2, 0.25),
        _point(11, 0.38, 0.35, 0.0),
        _point(12, 0.62, 0.35, 0.0),
    ]


def test_front_is_mechanical_and_not_swapped():
    judged = judge_landmarks(_front())
    assert judged["facing"] == "front"
    assert judged["confidence"] >= 0.72
    corrected, report = decide(judged, [], _front())
    assert report["source"] == "mechanical"
    assert report["swapped"] is False
    assert corrected[1]["x"] == 0.62


def test_back_uses_shoulder_order():
    judged = judge_landmarks(_back())
    assert judged["facing"] == "back"
    assert needs_swap(_back(), "back") is False


def test_gemini_front_swaps_mirrored_shoulders():
    mirrored = _back()
    mechanical = {"facing": "back", "confidence": 0.4, "source": "mechanical", "swapped": False}
    corrected, report = decide(mechanical, [{"facing": "front"}, {"facing": "front"}], mirrored)
    assert report["facing"] == "front"
    assert report["source"] == "gemini"
    assert report["swapped"] is True
    by_index = {item["index"]: item for item in corrected}
    assert by_index[11]["x"] > by_index[12]["x"]


def test_second_vote_returns_to_mechanical():
    mechanical = {"facing": "front", "confidence": 0.4, "source": "mechanical", "swapped": False}
    _, report = decide(mechanical, [{"facing": "back"}, {"facing": "front"}], _front())
    assert report["facing"] == "front"
    assert report["source"] == "agree"


def test_text_keeps_facing_and_drops_coordinates():
    parsed = facing_from_text('{"facing":"left","x":0.2,"y":0.4,"z":1}')
    assert parsed["facing"] == "left"
    assert "x" not in parsed


def test_closer_left_shoulder_faces_image_left():
    landmarks = [
        _point(11, 0.48, 0.35, -0.2),
        _point(12, 0.52, 0.35, 0.05),
    ]
    assert judge_landmarks(landmarks)["facing"] == "left"


def test_swap_keeps_indexes():
    swapped = swap_sides(_front())
    assert {item["index"] for item in swapped} == {item["index"] for item in _front()}
