"""確かめる。出典区分（own_work / third_party / web）を Jev に渡し、区分ごとに判定する。"""

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

_KIND_LABEL = {
    "own_work": "uploader-declared own work (illustration or notes by the user)",
    "third_party": "third-party reference material owned by the user but not created by them",
    "web": "web search result page",
}


def verify_sources(
    label: str,
    chunks: list[dict[str, str]],
    question: str = "",
) -> list[dict[str, Any]]:
    """権利文言は引用コピーだけ。Jev は区分を踏まえて確からしさだけ返す。"""
    if not label.strip():
        return []

    sources = _group(chunks)
    if not sources:
        return []

    if not jev_available():
        logger.info("verify skipped reason=config_missing")
        return [_fallback_without_jev(item) for item in sources]

    try:
        from typesafe_sdk import Noul
    except ImportError:
        logger.exception("verify skipped reason=sdk_missing")
        return [_fallback_without_jev(item) for item in sources]

    try:
        response = ask(_state(label, sources, question), _questions(sources, Noul, question))
    except Exception:
        logger.exception("verify skipped reason=jev_failed")
        return [_fallback_without_jev(item) for item in sources]

    checked = [_apply(index, item, response) for index, item in enumerate(sources)]
    logger.info("verify model=jev source_count=%s", len(checked))
    return checked


def _group(chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
    order: list[str] = []
    grouped: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        url = chunk.get("url", "").strip()
        if not url:
            continue
        kind = chunk.get("material_kind") or "web"
        if url not in grouped:
            if len(order) >= _MAX_SOURCES:
                continue
            order.append(url)
            grouped[url] = {
                "url": url,
                "title": chunk.get("title", ""),
                "text": "",
                "material_kind": kind,
            }
        item = grouped[url]
        if not item["title"]:
            item["title"] = chunk.get("title", "")
        if not item.get("material_kind") or item["material_kind"] == "web":
            item["material_kind"] = kind
        extra = chunk.get("text", "").strip()
        if extra and extra not in item["text"]:
            item["text"] = f"{item['text']}\n{extra}".strip()[:_MAX_TEXT]

    ready: list[dict[str, Any]] = []
    for url in order:
        item = grouped[url]
        text = item["text"]
        kind = item.get("material_kind") or "web"
        ready.append(
            {
                "url": url,
                "title": item["title"],
                "text": text,
                "material_kind": kind,
                "spans": {
                    # 自作は第三者ライセンスを拾わない
                    "license": "" if kind == "own_work" else _first(_LICENSE, text),
                    "created": _first(_CREATED, text),
                    "copyright": "" if kind == "own_work" else _first(_COPYRIGHT, text),
                },
            }
        )
    return ready


def _first(pattern: re.Pattern[str], text: str) -> str:
    found = pattern.search(text)
    if found is None:
        return ""
    return found.group(1).strip()


def _state(label: str, sources: list[dict[str, Any]], question: str) -> dict[str, Any]:
    return {
        "object_label": label,
        "user_question": question.strip(),
        "sources": [
            {
                "source_id": f"src_{index}",
                "material_kind": item["material_kind"],
                "material_kind_meaning": _KIND_LABEL.get(
                    item["material_kind"],
                    _KIND_LABEL["web"],
                ),
                "title": item["title"],
                "text": item["text"],
                "license_span": item["spans"]["license"],
                "created_span": item["spans"]["created"],
                "copyright_span": item["spans"]["copyright"],
            }
            for index, item in enumerate(sources)
        ],
    }


def _questions(sources: list[dict[str, Any]], noul_type: Any, question: str) -> dict[str, Any]:
    questions: dict[str, Any] = {}
    has_question = bool(question.strip())
    for index, item in enumerate(sources):
        source_id = f"src_{index}"
        kind = item["material_kind"]
        kind_note = (
            f"`{source_id}` material_kind is `{kind}` "
            f"({_KIND_LABEL.get(kind, kind)}). "
        )
        if kind == "own_work":
            if has_question:
                questions[f"{source_id}_about"] = noul_type(
                    instructions=(
                        kind_note
                        + "Treat as the user's own declared work. "
                        f"`{source_id}` text is useful for answering user_question "
                        "about object_label as the user's own reference. "
                        "False when unrelated or empty of useful content."
                    ),
                )
            else:
                questions[f"{source_id}_about"] = noul_type(
                    instructions=(
                        kind_note
                        + "Treat as the user's own declared work. "
                        f"`{source_id}` text is about object_label as own reference. "
                        "False when unrelated."
                    ),
                )
            # 自作は第三者ライセンス／著作権スパンの採用判定をしない
            continue

        if has_question:
            questions[f"{source_id}_about"] = noul_type(
                instructions=(
                    kind_note
                    + f"`{source_id}` text answers user_question about object_label "
                    "as a third-party or web source. "
                    "False when unrelated or silent on the question."
                ),
            )
        else:
            questions[f"{source_id}_about"] = noul_type(
                instructions=(
                    kind_note
                    + f"`{source_id}` text is about object_label as a third-party "
                    "or web source. False when unrelated."
                ),
            )
        for field in ("license", "created", "copyright"):
            if not item["spans"][field]:
                continue
            questions[f"{source_id}_{field}"] = noul_type(
                instructions=(
                    kind_note
                    + f"`{source_id}` {field}_span is copied from text and states that field "
                    "for this third-party or web source. "
                    "False when the span is absent, unrelated, only implied, "
                    "or would misstate rights for this material_kind."
                ),
            )
    return questions


def _apply(index: int, item: dict[str, Any], response: Any) -> dict[str, Any]:
    source_id = f"src_{index}"
    kind = item.get("material_kind") or "web"
    about = read_noul(response, f"{source_id}_about")

    if kind == "own_work":
        return {
            "url": item["url"],
            "title": item["title"],
            "license": "own_claim",
            "created": item["spans"]["created"] or "unknown",
            "copyright": "own_claim",
            "material_kind": "own_work",
            "jev": {
                "about": _pct(about),
                "license": None,
                "created": None,
                "copyright": None,
            },
        }

    relevant = about is not None and about >= ACT_THRESHOLD
    result = _blank(item)
    result["jev"] = {
        "about": _pct(about),
        "license": None,
        "created": None,
        "copyright": None,
    }
    if not relevant:
        for field in ("license", "created", "copyright"):
            if item["spans"][field]:
                result["jev"][field] = _pct(read_noul(response, f"{source_id}_{field}"))
        return result

    for field in ("license", "created", "copyright"):
        span = item["spans"][field]
        score = read_noul(response, f"{source_id}_{field}") if span else None
        result["jev"][field] = _pct(score) if span else None
        if span and span in item["text"] and score is not None and score >= ACT_THRESHOLD:
            result[field] = span
    return result


def _fallback_without_jev(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("material_kind") == "own_work":
        return {
            "url": item["url"],
            "title": item["title"],
            "license": "own_claim",
            "created": "unknown",
            "copyright": "own_claim",
            "material_kind": "own_work",
            "jev": {
                "about": None,
                "license": None,
                "created": None,
                "copyright": None,
            },
        }
    return _blank(item)


def _pct(value: float | None) -> int | None:
    if value is None:
        return None
    return int(round(max(0.0, min(1.0, float(value))) * 100))


def _blank(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": item["url"],
        "title": item["title"],
        "license": "unknown",
        "created": "unknown",
        "copyright": "unknown",
        "material_kind": item.get("material_kind") or "web",
        "jev": {
            "about": None,
            "license": None,
            "created": None,
            "copyright": None,
        },
    }
