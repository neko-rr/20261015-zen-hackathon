"""選んだ物体をウェブで調べ、出典に書いてある範囲だけ残す。"""

import logging
from typing import Any

from app.errors import system_error
from app.settings import Settings
from app.verify import verify_sources

logger = logging.getLogger(__name__)

_MAX_LINKS = 4


def lookup_object(settings: Settings, label: str) -> dict[str, Any]:
    """画像から選んだ物体の自動検索。まとめと出典 URL だけ返す。"""
    summary, chunks, suggestions = _search(settings, _summary_prompt(label))
    sources = _links(chunks)
    logger.info("search model=%s source_count=%s", settings.gemini_model, len(sources))
    return {
        "summary": summary,
        "sources": sources,
        "search_suggestions_html": suggestions,
    }


def answer_question(settings: Settings, label: str, message: str) -> dict[str, Any]:
    """チャットの質問を検索し、出典本文にある権利だけを Jev で判断する。"""
    if not label.strip() or not message.strip():
        raise system_error("lookup_failed", "調べものに失敗しました。")

    summary, chunks, _suggestions = _search(settings, _question_prompt(label, message))
    sources = verify_sources(label, chunks, message)
    logger.info(
        "chat model=%s source_count=%s",
        settings.gemini_model,
        len(sources),
    )
    return {"answer": summary, "sources": sources}


def _summary_prompt(label: str) -> str:
    return (
        f"絵の資料として「{label}」を短く説明してください。"
        "説明は検索結果に基づくこと。ライセンス、作成時期、著作権は書かないこと。"
        "本のダウンロードはしないこと。"
    )


def _question_prompt(label: str, message: str) -> str:
    return (
        f"絵の資料として、物体「{label}」について次の質問に短く答えてください。\n"
        f"質問: {message}\n"
        "答えは検索結果にあることだけ。無いことは未確認と書くこと。"
        "ライセンス名、作成時期、著作権者は断定しないこと。"
        "本のダウンロードはしないこと。"
    )


def _search(settings: Settings, prompt: str) -> tuple[str, list[dict[str, str]], str]:
    if not prompt.strip():
        raise system_error("lookup_failed", "調べものに失敗しました。")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        logger.exception("gemini sdk missing")
        raise system_error("lookup_failed", "調べものに失敗しました。") from exc

    try:
        client = genai.Client(http_options=types.HttpOptions(timeout=60_000))
        grounded = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
    except Exception as exc:
        logger.exception("lookup search failed model=%s", settings.gemini_model)
        raise system_error("lookup_failed", "調べものに失敗しました。") from exc

    summary = (grounded.text or "").strip()
    return summary, _chunk_records(grounded), _suggestions_html(grounded)


def _links(chunks: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    links: list[dict[str, str]] = []
    for chunk in chunks:
        url = chunk.get("url", "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        if len(links) >= _MAX_LINKS:
            break
        links.append({"url": url, "title": chunk.get("title", "")})
    return links


def _chunk_records(response: Any) -> list[dict[str, str]]:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    metadata = getattr(candidates[0], "grounding_metadata", None)
    chunks = getattr(metadata, "grounding_chunks", None) or []
    records: list[dict[str, str]] = []
    for chunk in chunks:
        web = getattr(chunk, "web", None)
        retrieved = getattr(chunk, "retrieved_context", None)
        url = str(getattr(web, "uri", "") or getattr(retrieved, "uri", "") or "")
        title = str(getattr(web, "title", "") or getattr(retrieved, "title", "") or "")
        text = str(getattr(retrieved, "text", "") or "")
        if not url and not text:
            continue
        records.append({"url": url, "title": title, "text": text})
    supports = getattr(metadata, "grounding_supports", None) or []
    for support in supports:
        segment = getattr(support, "segment", None)
        text = str(getattr(segment, "text", "") or "").strip()
        if not text:
            continue
        indices = getattr(support, "grounding_chunk_indices", None) or [0]
        for index in indices:
            position = int(index)
            if position < 0 or position >= len(records):
                continue
            current = records[position]["text"]
            if text not in current:
                records[position]["text"] = f"{current}\n{text}".strip()
    return records


def _suggestions_html(response: Any) -> str:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return ""
    metadata = getattr(candidates[0], "grounding_metadata", None)
    entry = getattr(metadata, "search_entry_point", None)
    return str(getattr(entry, "rendered_content", "") or "")


