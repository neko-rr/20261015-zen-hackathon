"""人マスク輪郭の単体テスト。"""

import numpy as np

from app.segment import contour_from_mask


def test_contour_follows_blob_not_full_frame():
    mask = np.zeros((80, 100), dtype=bool)
    mask[20:60, 30:70] = True
    contour = contour_from_mask(mask)
    assert len(contour) >= 4
    xs = [point["x"] for point in contour]
    ys = [point["y"] for point in contour]
    assert min(xs) > 0.15
    assert max(xs) < 0.85
    assert min(ys) > 0.1
    assert max(ys) < 0.9


def test_empty_mask_has_no_contour():
    assert contour_from_mask(np.zeros((20, 20), dtype=bool)) == []
