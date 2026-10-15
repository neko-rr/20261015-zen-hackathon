"""解析の前に、写真を JPEG / PNG / WebP の 10MB 以下へ寄せる。

対応形式で 10MB 以下ならそのまま使う。それ以外は JPEG に直す。
100MB を超えるファイルと、画像として読めないファイルだけを断る。
"""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageOps, UnidentifiedImageError

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

from app.errors import business_error
from app.settings import ALLOWED_IMAGE_TYPES, MAX_IMAGE_BYTES, MAX_UPLOAD_BYTES

logger = logging.getLogger(__name__)

_START_EDGE = 4096
_MIN_EDGE = 64


def prepare_photo(
    image: bytes,
    mime_type: str,
    *,
    limit: int = MAX_IMAGE_BYTES,
    upload_limit: int = MAX_UPLOAD_BYTES,
) -> tuple[bytes, str]:
    """解析に渡せるバイトと MIME を返す。直せないときだけ業務エラー。"""
    if not image:
        raise business_error("invalid_image", "写真が空です。")
    if len(image) > upload_limit:
        raise business_error("image_too_large", "写真は 100MB 以下にしてください。")
    declared = (mime_type or "").split(";")[0].strip().lower()
    if declared in ALLOWED_IMAGE_TYPES and len(image) <= limit:
        return image, declared
    try:
        converted = _jpeg_within(image, limit)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        logger.info("photo unreadable bytes=%s mime=%s", len(image), declared or "unknown")
        raise business_error("unsupported_type", "このファイルは画像として読めませんでした。") from None
    logger.info("photo converted bytes_in=%s bytes_out=%s", len(image), len(converted))
    return converted, "image/jpeg"


def _jpeg_within(image: bytes, limit: int) -> bytes:
    with Image.open(io.BytesIO(image)) as picture:
        rgb = _as_rgb(ImageOps.exif_transpose(picture))
    longest = max(rgb.size)
    if longest > _START_EDGE:
        scale = _START_EDGE / longest
        rgb = rgb.resize(
            (max(1, int(rgb.width * scale)), max(1, int(rgb.height * scale))),
            Image.Resampling.LANCZOS,
        )
    quality = 85
    while True:
        data = _encode(rgb, quality)
        if len(data) <= limit:
            return data
        if quality > 45:
            quality -= 15
            continue
        if min(rgb.size) <= _MIN_EDGE:
            break
        rgb = rgb.resize(
            (max(1, int(rgb.width * 0.75)), max(1, int(rgb.height * 0.75))),
            Image.Resampling.LANCZOS,
        )
        quality = 75
    raise business_error("image_too_large", "写真を 10MB 以下にできませんでした。")


def _as_rgb(picture: Image.Image) -> Image.Image:
    if picture.mode in {"RGBA", "LA"} or (picture.mode == "P" and "transparency" in picture.info):
        rgba = picture.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return picture.convert("RGB")


def _encode(picture: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()
