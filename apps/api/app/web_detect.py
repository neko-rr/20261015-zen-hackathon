"""Cloud Vision の Web Detection。掲載ページと、一致・類似画像を返す。"""

import base64
import io
import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_ANNOTATE_URL = "https://vision.googleapis.com/v1/images:annotate"
_TIMEOUT_SECONDS = 20
_MAX_PAGES = 5
_MAX_IMAGES = 8


def detect_web(image: bytes) -> dict[str, list[dict[str, str]]]:
    """掲載ページと画像検索。失敗しても空。権利者の断定はしない。"""
    empty: dict[str, list[dict[str, str]]] = {"pages": [], "images": []}
    if not image:
        return empty
    try:
        payload = _annotate(_shrink(image))
    except Exception:
        logger.exception("vision web detection failed")
        return empty
    return {
        "pages": pages_from_response(payload),
        "images": images_from_response(payload),
    }


def detect_pages(image: bytes) -> list[dict[str, str]]:
    """掲載ページ。失敗しても空。"""
    return detect_web(image)["pages"]


def pages_from_response(payload: Any) -> list[dict[str, str]]:
    """API 応答にあるページ URL だけ。"""
    if not isinstance(payload, dict):
        return []
    responses = payload.get("responses")
    if not isinstance(responses, list) or not responses or not isinstance(responses[0], dict):
        return []
    web = responses[0].get("webDetection")
    if not isinstance(web, dict):
        return []
    pages = web.get("pagesWithMatchingImages")
    if not isinstance(pages, list):
        return []
    found: list[dict[str, str]] = []
    for page in pages:
        if len(found) >= _MAX_PAGES or not isinstance(page, dict):
            continue
        url = str(page.get("url") or "").strip()
        if not url.startswith("https://"):
            continue
        title = " ".join(str(page.get("pageTitle") or "").split()) or url
        found.append({"url": url, "title": title[:200]})
    return found


def images_from_response(payload: Any) -> list[dict[str, str]]:
    """同じ画像、一部一致、見た目が近い画像。https だけ、最大8件。"""
    web = _web(payload)
    if web is None:
        return []
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: object, match: str, page_url: object = "") -> None:
        image_url = str(url or "").strip()
        if len(found) >= _MAX_IMAGES or not image_url.startswith("https://") or image_url in seen:
            return
        page = str(page_url or "").strip()
        seen.add(image_url)
        found.append(
            {
                "url": image_url,
                "page_url": page if page.startswith("https://") else "",
                "match": match,
            }
        )

    for page in web.get("pagesWithMatchingImages") or []:
        if not isinstance(page, dict):
            continue
        page_url = page.get("url")
        for image in page.get("fullMatchingImages") or []:
            if isinstance(image, dict):
                add(image.get("url"), "full", page_url)
        for image in page.get("partialMatchingImages") or []:
            if isinstance(image, dict):
                add(image.get("url"), "partial", page_url)
    for image in web.get("fullMatchingImages") or []:
        if isinstance(image, dict):
            add(image.get("url"), "full")
    for image in web.get("partialMatchingImages") or []:
        if isinstance(image, dict):
            add(image.get("url"), "partial")
    for image in web.get("visuallySimilarImages") or []:
        if isinstance(image, dict):
            add(image.get("url"), "similar")
    return found


def _web(payload: Any) -> dict | None:
    if not isinstance(payload, dict):
        return None
    responses = payload.get("responses")
    if not isinstance(responses, list) or not responses or not isinstance(responses[0], dict):
        return None
    web = responses[0].get("webDetection")
    if not isinstance(web, dict):
        return None
    return web


def _shrink(image: bytes) -> bytes:
    try:
        from PIL import Image

        with Image.open(io.BytesIO(image)) as picture:
            rgb = picture.convert("RGB")
            rgb.thumbnail((1024, 1024))
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=80)
            return buffer.getvalue()
    except Exception:
        logger.exception("vision shrink skipped")
        return image


def _annotate(image: bytes) -> Any:
    import google.auth
    from google.auth.transport.requests import Request

    credentials, _project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-vision"]
    )
    credentials.refresh(Request())
    token = getattr(credentials, "token", "")
    if not token:
        raise RuntimeError("vision token missing")
    body = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image).decode("ascii")},
                "features": [{"type": "WEB_DETECTION", "maxResults": _MAX_IMAGES}],
            }
        ]
    }
    request = urllib.request.Request(
        _ANNOTATE_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"vision http {exc.code}") from None
