"""姿勢まわりの単体テスト（MediaPipe 本体は呼ばない）。"""

from app.pose import empty_pose, _muscle_labels


def test_empty_pose_shape():
    pose = empty_pose()
    assert pose["landmarks"] == []
    assert pose["edges"] == []
    assert pose["muscles"] == []


def test_muscle_labels_from_landmarks():
    by_index = {
        11: {"index": 11, "name": "left_shoulder", "x": 0.4, "y": 0.3, "z": 0.0, "visibility": 1.0},
        12: {"index": 12, "name": "right_shoulder", "x": 0.6, "y": 0.3, "z": 0.0, "visibility": 1.0},
        13: {"index": 13, "name": "left_elbow", "x": 0.35, "y": 0.45, "z": 0.0, "visibility": 1.0},
        14: {"index": 14, "name": "right_elbow", "x": 0.65, "y": 0.45, "z": 0.0, "visibility": 1.0},
        23: {"index": 23, "name": "left_hip", "x": 0.42, "y": 0.6, "z": 0.0, "visibility": 1.0},
        24: {"index": 24, "name": "right_hip", "x": 0.58, "y": 0.6, "z": 0.0, "visibility": 1.0},
        25: {"index": 25, "name": "left_knee", "x": 0.42, "y": 0.75, "z": 0.0, "visibility": 1.0},
        26: {"index": 26, "name": "right_knee", "x": 0.58, "y": 0.75, "z": 0.0, "visibility": 1.0},
        27: {"index": 27, "name": "left_ankle", "x": 0.42, "y": 0.9, "z": 0.0, "visibility": 1.0},
        28: {"index": 28, "name": "right_ankle", "x": 0.58, "y": 0.9, "z": 0.0, "visibility": 1.0},
    }
    muscles = _muscle_labels(by_index)
    names = {item["name"] for item in muscles}
    assert "左三角筋" in names
    assert "腹直筋" in names
    assert "左大腿四頭筋" in names
