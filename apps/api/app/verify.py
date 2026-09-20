"""確かめる。引用の中に語句があるときだけ、ライセンス・時期・著作権を残す。"""

import logging
import re
from typing import Any

from app.jev_client import ACT_THRESHOLD, ask, jev_available, read_noul

logger = logging.getLogger(__name__)

_MAX_SOURCES = 4
_MAX_TEXT = 1200

_LICENSE = re.compile(
    r"(CC0|CC[-\s]?BY(?:[-\s]?(?:SA|NC|ND)){0,3}|Creative Commons|All rights reserved|"
    r"Public Domain|パブリックドメイン|クリエイティブ・コモンズ[^。\n]{0,40})",
    re.IGNORECASE,
)
_CREATED = re.compile(r"((?:19|20)\d{2}年?)")
_COPYRIGHT = re.compile(r"((?:©|\(c\)|Copyright|著作権)[^\n。]{0,80})", re.IGNORECASE)


def verify_sources(
    label: str,
    chunks: list[dict[str, str]],
    question: str = "",
) -> list[dict[str, Any]]:
    """権利は引用からのコピーだけ。Jev が文を作ることはない。"""
    if not label.strip():
        return []

    sources = _group(chunks)
    if not jev_available():
        logger.info("verify skipped reason=config_missing")
        return [_blank(item) for item in sources]
    if not any(item["spans"].values() for item in sources):
        logger.info("verify skipped reason=no_spans")
        return [_blank(item) for item in sources]

    try:
        from typesafe_sdk import Noul
    except ImportError:
        logger.exception("verify skipped reason=sdk_missing")
        return [_blank(item) for item in sources]

    try:
        response = ask(_state(label, sources), _questions(sources, Noul))
    except Exception:
        logger.exception("verify skipped reason=jev_failed")
        return [_blank(item) for item in sources]

    checked = [_apply(index, item, response) for index, item in enumerate(sources)]
    logger.info("verify model=jev source_count=%s", len(checked))
    return checked


def _group(chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
    order: list[str] = []
    grouped: dict[str, dict[str, str]] = {}
    for chunk in chunks:
        url = chunk.get("url", "").strip()
        if not url:
            continue
        if url not in grouped:
            if len(order) >= _MAX_SOURCES:
                continue
            order.append(url)
            grouped[url] = {"url": url, "title": chunk.get("title", ""), "text": ""}
        item = grouped[url]
        if not item["title"]:
            item["title"] = chunk.get("title", "")
        extra = chunk.get("text", "").strip()
        if extra and extra not in item["text"]:
            item["text"] = f"{item['text']}\n{extra}".strip()[:_MAX_TEXT]

    ready: list[dict[str, Any]] = []
    for url in order:
        item = grouped[url]
        text = item["text"]
        ready.append(
            {
                "url": url,
                "title": item["title"],
                "text": text,
                "spans": {
                    "license": _first(_LICENSE, text),
                    "created": _first(_CREATED, text),
                    "copyright": _first(_COPYRIGHT, text),
                },
            }
        )
    return ready


def _first(pattern: re.Pattern[str], text: str) -> str:
    found = pattern.search(text)
    if found is None:
        return ""
    return found.group(1).strip()


def _state(label: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "object_label": label,
        "sources": [
            {
                "source_id": f"src_{index}",
                "title": item["title"],
                "text": item["text"],
                "license_span": item["spans"]["license"],
                "created_span": item["spans"]["created"],
                "copyright_span": item["spans"]["copyright"],
            }
            for index, item in enumerate(sources)
        ],
    }


def _questions(sources: list[dict[str, Any]], noul_type: Any) -> dict[str, Any]:
    questions: dict[str, Any] = {}
    for index, item in enumerate(sources):
        source_id = f"src_{index}"
        questions[f"{source_id}_about"] = noul_type(
            instructions=(
                f"`{source_id}` text is about object_label. "
                "False when the page is unrelated."
            ),
        )
        for field in ("license", "created", "copyright"):
            if not item["spans"][field]:
                continue
            questions[f"{source_id}_{field}"] = noul_type(
                instructions=(
                    f"`{source_id}` {field}_span is copied from text and states that field. "
                    "False when the span is absent, unrelated, or only implied."
                ),
            )
    return questions


def _apply(index: int, item: dict[str, Any], response: Any) -> dict[str, str]:
    source_id = f"src_{index}"
    about = read_noul(response, f"{source_id}_about")
    relevant = about is not None and about >= ACT_THRESHOLD
    result = _blank(item)
    if not relevant:
        return result
    for field in ("license", "created", "copyright"):
        span = item["spans"][field]
        score = read_noul(response, f"{source_id}_{field}")
        if span and span in item["text"] and score is not None and score >= ACT_THRESHOLD:
            result[field] = span
    return result


def _blank(item: dict[str, Any]) -> dict[str, str]:
    return {
        "url": item["url"],
        "title": item["title"],
        "license": "unknown",
        "created": "unknown",
        "copyright": "unknown",
    }
