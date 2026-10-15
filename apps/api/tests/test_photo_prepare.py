import io

import pytest
from PIL import Image

from app.errors import AppError
from app.photo_prepare import prepare_photo


def _png(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (20, 40, 60)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_small_png_stays_png() -> None:
    raw = _png(32, 24)
    out, mime = prepare_photo(raw, "image/png")
    assert out == raw
    assert mime == "image/png"


def test_bmp_becomes_jpeg() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), (8, 16, 32)).save(buffer, format="BMP")
    out, mime = prepare_photo(buffer.getvalue(), "image/bmp")
    assert mime == "image/jpeg"
    assert out.startswith(b"\xff\xd8")
    with Image.open(io.BytesIO(out)) as picture:
        assert picture.size == (40, 30)


def test_over_limit_jpeg_is_shrunk() -> None:
    buffer = io.BytesIO()
    Image.effect_noise((480, 360), 80).convert("RGB").save(buffer, format="JPEG", quality=95)
    raw = buffer.getvalue()
    out, mime = prepare_photo(raw, "image/jpeg", limit=12_000)
    assert mime == "image/jpeg"
    assert len(out) <= 12_000
    assert len(out) < len(raw)


def test_over_upload_limit_is_rejected() -> None:
    with pytest.raises(AppError) as caught:
        prepare_photo(b"x" * 80, "image/jpeg", upload_limit=40)
    assert caught.value.code == "image_too_large"


def test_unreadable_file_is_rejected() -> None:
    with pytest.raises(AppError) as caught:
        prepare_photo(b"not-an-image", "application/octet-stream")
    assert caught.value.code == "unsupported_type"
