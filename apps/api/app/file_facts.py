"""写真ファイルに書いてある作者・著作権・画像 ID・C2PA だけを読む。"""

import io
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_MAX_TEXT = 160
_CLAIM_GENERATOR = re.compile(br'"claim_generator"\s*:\s*"([^"\\]{1,120})"')
_XMP_ATTR = re.compile(
    r"(?:dc:rights|xmpRights:WebStatement|plus:ImageSupplierImageID|photoshop:Credit|photoshop:Copyright)"
    r'\s*=\s*"([^"]{1,300})"',
    re.IGNORECASE,
)
_XMP_CREATOR = re.compile(
    r"<dc:creator\b[^>]*>[\s\S]{0,400}?<rdf:li[^>]*>([^<]{1,160})</rdf:li>",
    re.IGNORECASE,
)


def empty_file_facts() -> dict[str, str]:
    """無い項目は unknown。C2PA がバイト列に無ければ absent。"""
    return {
        "artist": "unknown",
        "copyright": "unknown",
        "copyright_url": "unknown",
        "image_id": "unknown",
        "credit": "unknown",
        "c2pa": "absent",
        "c2pa_generator": "unknown",
    }


def read_file_facts(image: bytes) -> dict[str, str]:
    """壊れたファイルでも unknown を返す。位置情報は読まない。"""
    facts = empty_file_facts()
    if not image:
        return facts
    try:
        found = _read(image)
    except Exception:
        logger.exception("file facts failed")
        return facts
    for key in ("artist", "copyright", "copyright_url", "image_id", "credit"):
        if found.get(key):
            facts[key] = found[key]
    if found.get("c2pa") == "present":
        facts["c2pa"] = "present"
        if found.get("c2pa_generator"):
            facts["c2pa_generator"] = found["c2pa_generator"]
    return facts


def _read(image: bytes) -> dict[str, str]:
    found: dict[str, str] = {}
    _put(found, "artist", _pillow_text(image, "artist"))
    _put(found, "copyright", _pillow_text(image, "copyright"))
    unique_id = _pillow_text(image, "image_id")
    iptc = _iptc(image)
    xmp = _xmp(image)
    for key, value in iptc.items():
        if key == "image_id":
            continue
        _put(found, key, value)
    for key, value in xmp.items():
        if key == "image_id":
            continue
        _put(found, key, value)
    image_id = xmp.get("image_id") or iptc.get("image_id") or unique_id
    if image_id:
        found["image_id"] = image_id
    comment = _jpeg_comment(image)
    _put(found, "credit", comment)
    status, generator = _c2pa(image)
    if status == "present":
        found["c2pa"] = "present"
        if generator:
            found["c2pa_generator"] = generator
    return found


def _pillow_text(image: bytes, field: str) -> str:
    try:
        from PIL import Image
    except ImportError:
        logger.exception("pillow missing")
        return ""
    try:
        with Image.open(io.BytesIO(image)) as picture:
            exif = picture.getexif()
            if field == "artist":
                return _text(exif.get(315) if exif else "") or _png_value(picture, ("Author", "Artist"))
            if field == "copyright":
                return _text(exif.get(33432) if exif else "") or _png_value(
                    picture, ("Copyright", "CopyrightNotice")
                )
            sub = exif.get_ifd(0x8769) if exif else {}
            return _text(sub.get(0xA420) if sub else "")
    except Exception:
        logger.exception("exif read skipped")
        return ""


def _png_value(picture: Any, keys: tuple[str, ...]) -> str:
    info = getattr(picture, "info", {}) or {}
    for key in keys:
        value = _text(info.get(key))
        if value:
            return value
    return ""


def _iptc(image: bytes) -> dict[str, str]:
    found: dict[str, str] = {}
    for segment in _jpeg_payloads(image, 0xED):
        if b"Photoshop 3.0" not in segment:
            continue
        for dataset, raw in _iptc_datasets(segment):
            value = _text(raw)
            if dataset == 80:
                _put(found, "artist", value)
            elif dataset == 116:
                _put(found, "copyright", value)
            elif dataset == 110:
                _put(found, "credit", value)
            elif dataset == 103:
                _put(found, "image_id", value)
    return found


def _iptc_datasets(segment: bytes) -> list[tuple[int, bytes]]:
    rows: list[tuple[int, bytes]] = []
    index = 0
    while index + 5 <= len(segment):
        if segment[index] != 0x1C:
            index += 1
            continue
        record = segment[index + 1]
        dataset = segment[index + 2]
        length = int.from_bytes(segment[index + 3 : index + 5], "big")
        start = index + 5
        end = start + length
        if end > len(segment):
            break
        if record == 2:
            rows.append((dataset, segment[start:end]))
        index = end
    return rows


def _xmp(image: bytes) -> dict[str, str]:
    found: dict[str, str] = {}
    packets = []
    for segment in _jpeg_payloads(image, 0xE1):
        if segment.startswith(b"http://ns.adobe.com/xap/1.0/"):
            packets.append(segment.split(b"\x00", 1)[-1])
    packets.extend(_png_xmp(image))
    for raw in packets:
        xml = raw.decode("utf-8", "ignore")
        creator = _XMP_CREATOR.search(xml)
        if creator:
            _put(found, "artist", creator.group(1))
        for match in _XMP_ATTR.finditer(xml):
            token = match.group(0).split("=", 1)[0].lower()
            value = match.group(1)
            if "webstatement" in token:
                _put(found, "copyright_url", _http_url(value))
            elif "imagesupplierimageid" in token:
                _put(found, "image_id", value)
            elif token.endswith("credit"):
                _put(found, "credit", value)
            elif "copyright" in token or token.endswith("rights"):
                _put(found, "copyright", value)
    return found


def _png_xmp(image: bytes) -> list[bytes]:
    packets: list[bytes] = []
    if not image.startswith(b"\x89PNG\r\n\x1a\n"):
        return packets
    index = 8
    while index + 12 <= len(image):
        length = int.from_bytes(image[index : index + 4], "big")
        kind = image[index + 4 : index + 8]
        start = index + 8
        end = start + length
        if end + 4 > len(image):
            break
        chunk = image[start:end]
        if kind in (b"iTXt", b"tEXt") and b"xmp" in chunk[:40].lower():
            packets.append(chunk.split(b"\x00", 1)[-1])
        index = end + 4
    return packets


def _jpeg_comment(image: bytes) -> str:
    for segment in _jpeg_payloads(image, 0xFE):
        text = _text(segment)
        if text:
            return text
    return ""


def _c2pa(image: bytes) -> tuple[str, str]:
    if b"c2pa" not in image:
        return "absent", ""
    if b"claim_generator" not in image and b"urn:c2pa" not in image and b"c2pa.claim" not in image:
        return "absent", ""
    match = _CLAIM_GENERATOR.search(image)
    if not match:
        return "present", ""
    return "present", _text(match.group(1))


def _jpeg_payloads(image: bytes, marker: int) -> list[bytes]:
    if len(image) < 4 or not image.startswith(b"\xff\xd8"):
        return []
    payloads: list[bytes] = []
    index = 2
    while index + 4 <= len(image):
        if image[index] != 0xFF:
            break
        kind = image[index + 1]
        if kind == 0xDA or kind == 0xD9:
            break
        if kind == 0x01 or 0xD0 <= kind <= 0xD7:
            index += 2
            continue
        length = int.from_bytes(image[index + 2 : index + 4], "big")
        if length < 2 or index + 2 + length > len(image):
            break
        if kind == marker:
            payloads.append(image[index + 4 : index + 2 + length])
        index += 2 + length
    return payloads


def _put(found: dict[str, str], key: str, value: str) -> None:
    cleaned = _text(value)
    if cleaned and not found.get(key):
        found[key] = cleaned


def _http_url(value: str) -> str:
    text = _text(value)
    if text.startswith("https://") or text.startswith("http://"):
        return text[:300]
    return ""


def _text(value: object) -> str:
    if isinstance(value, bytes):
        raw = value.decode("utf-8", "ignore")
    elif isinstance(value, str):
        raw = value
    else:
        return ""
    text = " ".join(raw.replace("\x00", " ").split())
    if not text:
        return ""
    text = text[:_MAX_TEXT]
    printable = sum(character.isprintable() for character in text)
    if printable < len(text) * 0.8:
        return ""
    return text
