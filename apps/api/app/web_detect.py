"""Cloud Vision の Web Detection。この画像が載っているページだけを返す。"""

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


def detect_pages(image: bytes) -> list[dict[str, str]]:
    """掲載ページ。失敗しても空。権利者の断定はしない。"""
    if not image:
        return []
    try:
        payload = _annotate(_shrink(image))
    except Exception:
        logger.exception("vision web detection failed")
        return []
    return pages_from_response(payload)


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
                "features": [{"type": "WEB_DETECTION", "maxResults": _MAX_PAGES}],
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
