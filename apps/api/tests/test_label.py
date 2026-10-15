"""物体の呼び方。モデルは呼ばない。"""

from app.analyze import _assign_hands, _objects, _person_label, apply_names
from app.label import labels_from_text


def test_person_label_keeps_visible_traits_and_public_name() -> None:
    named = labels_from_text(
        '{"person_label":"成人の女性、白いシャツ","public_name":"例の公開人物","others":[]}'
    )
    assert _person_label(named) == "成人の女性、白いシャツ（例の公開人物）"


def test_uncertain_public_name_is_dropped() -> None:
    named = labels_from_text(
        '{"person_label":"成人の男性","public_name":"不明","others":[{"label":"駅のホーム","kind":"object"}]}'
    )
    assert named["public_name"] == ""
    assert _person_label(named) == "成人の男性"
    assert named["others"] == [{"label": "駅のホーム", "kind": "object", "work_title": ""}]


def test_fallback_label_is_person_when_naming_is_empty() -> None:
    segment = {"contour": [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2]], "box": {"x": 0, "y": 0, "w": 1, "h": 1}}
    pose = {
        "landmarks": [{"name": "nose", "x": 0.5, "y": 0.2}],
        "muscles": [],
    }
    rows = _objects(
        segment,
        [{"object_id": "obj_1", "landmarks": pose["landmarks"], "muscles": []}],
        {"person_label": "", "public_name": "", "people": [], "others": []},
    )
    assert rows[0]["label"] == "人"
    assert rows[0]["kind"] == "person"
    assert rows[0]["joints"][0]["name"] == "nose"


def test_other_subjects_are_separate_objects() -> None:
    rows = _objects(
        {"contour": [], "box": None},
        [],
        {
            "person_label": "",
            "public_name": "",
            "others": [
                {"label": "駅のホーム", "kind": "object"},
                {"label": "座る猫", "kind": "animal"},
            ],
        },
    )
    assert [item["label"] for item in rows] == ["駅のホーム", "座る猫"]
    assert rows[0]["is_primary"] is True
    assert rows[0]["joints"] == []
    assert rows[1]["kind"] == "animal"


def test_invalid_kind_and_duplicate_label_are_dropped() -> None:
    named = labels_from_text(
        '{"person_label":"白いシャツ","public_name":"","others":['
        '{"label":"白いシャツ","kind":"object"},'
        '{"label":"何か","kind":"person"},'
        '{"label":"赤い自転車","kind":"object"}]}'
    )
    assert named["others"] == [{"label": "赤い自転車", "kind": "object", "work_title": ""}]


def test_two_people_are_separate_dolls_from_the_left() -> None:
    rows = _objects(
        {"contour": [[0, 0], [1, 0], [1, 1]], "box": {"x": 0, "y": 0, "width": 1, "height": 1}},
        [
            {"object_id": "obj_1", "landmarks": [{"name": "nose", "x": 0.2, "y": 0.2}], "muscles": []},
            {"object_id": "obj_2", "landmarks": [{"name": "nose", "x": 0.8, "y": 0.2}], "muscles": []},
        ],
        {
            "people": [
                {"label": "成人の女性、白いシャツ", "public_name": ""},
                {"label": "成人の男性、黒い服", "public_name": ""},
            ],
            "others": [],
        },
    )
    assert [item["label"] for item in rows] == ["成人の女性、白いシャツ", "成人の男性、黒い服"]
    assert rows[0]["contour"]
    assert rows[1]["contour"] == []
    assert rows[1]["box"]["x"] == 0.8


def test_names_arrive_without_moving_joints() -> None:
    before = [
        {
            "object_id": "obj_1",
            "label": "人",
            "kind": "person",
            "is_primary": True,
            "box": None,
            "joints": [{"name": "nose", "x": 0.2, "y": 0.3}],
            "muscles": [],
            "contour": [],
        }
    ]
    after = apply_names(
        before,
        {"people": [{"label": "成人の女性、白いシャツ", "public_name": ""}], "others": [{"label": "駅のホーム", "kind": "object"}]},
    )
    assert after[0]["label"] == "成人の女性、白いシャツ"
    assert after[0]["joints"] == before[0]["joints"]
    assert after[1]["label"] == "駅のホーム"


def test_hands_follow_the_nearest_wrist() -> None:
    people = [
        {"landmarks": [{"index": 15, "x": 0.2, "y": 0.4}, {"index": 16, "x": 0.3, "y": 0.4}]},
        {"landmarks": [{"index": 15, "x": 0.7, "y": 0.4}, {"index": 16, "x": 0.8, "y": 0.4}]},
    ]
    hands = [
        {"side": "left", "landmarks": [{"x": 0.72, "y": 0.41}]},
        {"side": "right", "landmarks": [{"x": 0.21, "y": 0.4}]},
        {"side": "left", "landmarks": [{"x": 0.05, "y": 0.9}]},
    ]
    assigned = _assign_hands(people, hands)
    assert [hand["side"] for hand in assigned[0]] == ["right"]
    assert [hand["side"] for hand in assigned[1]] == ["left"]
