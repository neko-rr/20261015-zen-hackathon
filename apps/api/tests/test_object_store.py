"""保存パスは owner 配下。クラウドへは接続しない。"""

import pytest

from app.cloud_config import cloud_persistence_enabled
from app.errors import AppError
from app.object_store import material_object_name, photo_object_name


def test_cloud_persistence_is_off_in_tests() -> None:
    assert cloud_persistence_enabled() is False


def test_photo_object_is_under_owner() -> None:
    assert photo_object_name("owner-a", "photo-1") == "owners/owner-a/photos/photo-1/original"


def test_material_object_is_under_owner() -> None:
    name = material_object_name("owner-a", "own_work", "doc-1", "note.txt")
    assert name == "owners/owner-a/materials/own_work/doc-1/note.txt"


def test_photo_object_rejects_traversal() -> None:
    with pytest.raises(AppError) as caught:
        photo_object_name("../other", "photo-1")
    assert caught.value.code == "storage_failed"
