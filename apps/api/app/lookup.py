"""出典検索はウェブだけ。資料庫の取り寄せはチャット側で、混ぜない。"""

import copy
import logging
import re
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.errors import system_error
from app.editor_assist import enrich_turn
from app.jpsearch import search_rights
from app.rag import retrieve
from app.rights_query import rights_query
from app.settings import Settings
from app.verify import quoted_rights

logger = logging.getLogger(__name__)

_CACHE_LIMIT = 32
_web_cache: dict[str, dict[str, Any]] = {}
_cache_lock = Lock()


def clear_lookup_cache() -> None:
    """テスト用。覚えているウェブ検索を捨てる。"""
    with _cache_lock:
        _web_cache.clear()


_SKIP_SUMMARY = "この呼び方では著作物を特定できません。題名か作者が分かるときは入力してください。"


def lookup_object(
    settings: Settings,
    label: str,
    owner_id: str = "",
    tags: list[str] | None = None,
    project_id: str = "",
    public_name: str = "",
    work_title: str = "",
    query: str = "",
) -> dict[str, Any]:
    """題名か作者でウェブを調べる。資料庫は混ぜない。"""
    del owner_id, tags, project_id
    term = rights_query(public_name, work_title, query)
    if not term:
        logger.info("search skipped label_len=%s", len(label))
        return enrich_turn(
            {
                "summary": _SKIP_SUMMARY,
                "sources": [],
                "search_suggestions_html": "",
                "cached": False,
                "search_skipped": True,
            },
            label,
        )
    web, cached = _web_for_label(settings, term)
    sources = list(web["sources"])
    logger.info(
        "search model=%s web=%s cache=%s",
        settings.gemini_model,
        len(sources),
        "hit" if cached else "miss",
    )
    return enrich_turn(
        {
            "summary": web["summary"],
            "sources": sources,
            "search_suggestions_html": web["search_suggestions_html"],
            "cached": cached,
            "search_skipped": False,
        },
        label,
    )


def _web_for_label(settings: Settings, label: str) -> tuple[dict[str, Any], bool]:
    key = " ".join(label.split()).casefold()
    if not key:
        summary, chunks, suggestions = _search(settings, _summary_prompt(label))
        return _web_payload(summary, chunks, suggestions), False
    with _cache_lock:
        hit = _web_cache.get(key)
        if hit is not None:
            return copy.deepcopy(hit), True
    summary, chunks, suggestions = _search(settings, _summary_prompt(label))
    payload = _web_payload(summary, chunks, suggestions)
    payload["sources"] = _merge_unique(payload["sources"], search_rights(label))
    with _cache_lock:
        _web_cache[key] = copy.deepcopy(payload)
        while len(_web_cache) > _CACHE_LIMIT:
            _web_cache.pop(next(iter(_web_cache)))
    return payload, False


def _web_payload(summary: str, chunks: list[dict[str, str]], suggestions: str) -> dict[str, Any]:
    for chunk in chunks:
        chunk["material_kind"] = "web"
    return {
        "summary": summary,
        "sources": quoted_rights(chunks),
        "search_suggestions_html": suggestions,
    }


def answer_question(
    settings: Settings,
    label: str,
    message: str,
    owner_id: str = "",
    tags: list[str] | None = None,
    project_id: str = "",
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """資料庫・作業の記録・直近の会話から答える。ウェブ検索はしない。"""
    if not label.strip() or not message.strip():
        raise system_error("lookup_failed", "調べものに失敗しました。")
    hits = (
        retrieve(owner_id, _rag_query(label, message, tags), limit=4, project_id="")
        if owner_id
        else []
    )
    materials = [_library_card(hit) for hit in hits]
    from app.project_memory import retrieve_project_memory

    memory = retrieve_project_memory(owner_id, message, project_id) if owner_id else []
    dialogue = _recent_dialogue(history)
    if project_id.strip() and owner_id:
        _note_library(owner_id, project_id, materials, "chat")
    memo_updated = False
    if _wants_memo(message):
        answer, memo_updated = _save_requested_memo(
            settings,
            owner_id,
            project_id,
            label,
            message,
            materials,
            memory,
            dialogue,
        )
    elif not materials and not memory and not dialogue:
        logger.info("library empty owner=%s", owner_id[:8] if owner_id else "-")
        answer = "手元の資料には、この質問に当たるものがありません。"
    else:
        answer = _library_answer(settings, label, message, materials, memory, dialogue)
        logger.info("library chat hits=%s memory=%s turns=%s", len(materials), len(memory), len(dialogue))
    if project_id.strip() and owner_id:
        from app.project_store import note_prompt

        note_prompt(owner_id, project_id, label, message, answer)
    return {
        "answer": answer,
        "sources": [],
        "materials": materials,
        "memory": memory,
        "memo_updated": memo_updated,
        "search_suggestions_html": "",
    }


def cite_material(
    settings: Settings,
    owner_id: str,
    doc_id: str,
    query: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    """指定した資料の題名か作者だけを、外の出典検索に出す。"""
    from app.errors import business_error
    from app.material_store import get_material

    item = get_material(owner_id, doc_id)
    if item is None:
        raise business_error("object_not_found", "資料が見つかりません。")
    term = rights_query(user_query=query) or _term_from_text(str(item.get("index_text") or ""))
    if not term:
        return enrich_turn(
            {
                "doc_id": doc_id,
                "summary": _SKIP_SUMMARY,
                "sources": [],
                "search_suggestions_html": "",
                "cached": False,
                "search_skipped": True,
                "searched_at": "",
            },
            str(item.get("title") or ""),
        )
    from app.owner_prefs import citation_refresh_days

    stored = item.get("citation") if isinstance(item.get("citation"), dict) else {}
    if _citation_fresh(stored, term, citation_refresh_days(owner_id)):
        logger.info("citation stored owner=%s", owner_id[:8])
        payload = _stored_payload(doc_id, stored)
        _note_citation(owner_id, project_id, doc_id, str(item.get("title") or ""), term, payload)
        return enrich_turn(payload, term)
    web, _process_cached = _web_for_label(settings, term)
    searched_at = datetime.now(timezone.utc).isoformat()
    citation = _slim_citation(term, searched_at, web)
    from app.material_store import update_material

    update_material(owner_id, doc_id, {"citation": citation})
    payload = {
        "doc_id": doc_id,
        "summary": web["summary"],
        "sources": citation["sources"],
        "search_suggestions_html": web["search_suggestions_html"],
        "cached": False,
        "search_skipped": False,
        "searched_at": searched_at,
    }
    _note_citation(owner_id, project_id, doc_id, str(item.get("title") or ""), term, payload)
    return enrich_turn(payload, term)


def _note_library(
    owner_id: str,
    project_id: str,
    materials: list[dict[str, str]],
    via: str,
) -> None:
    from app.project_store import note_library_call

    for card in materials:
        note_library_call(owner_id, project_id, card["doc_id"], card["title"], via)


def _note_citation(
    owner_id: str,
    project_id: str,
    doc_id: str,
    title: str,
    term: str,
    payload: dict[str, Any],
) -> None:
    if not project_id.strip():
        return
    from app.project_store import note_citation

    note_citation(
        owner_id,
        project_id,
        doc_id,
        title,
        term,
        str(payload.get("searched_at") or ""),
        list(payload.get("sources") or []),
        bool(payload.get("cached")),
    )


def _citation_fresh(citation: dict[str, Any], term: str, days: int) -> bool:
    if str(citation.get("term") or "") != term:
        return False
    raw = str(citation.get("searched_at") or "")
    try:
        at = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - at
    return age.total_seconds() < days * 24 * 60 * 60


def _slim_citation(term: str, searched_at: str, web: dict[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, str]] = []
    for item in list(web.get("sources") or [])[:8]:
        sources.append(
            {
                "url": str(item.get("url") or ""),
                "title": str(item.get("title") or ""),
                "material_kind": str(item.get("material_kind") or "web"),
                "license": str(item.get("license") or ""),
                "created": str(item.get("created") or ""),
                "copyright": str(item.get("copyright") or ""),
                "rights_code": str(item.get("rights_code") or ""),
            }
        )
    return {
        "term": term,
        "searched_at": searched_at,
        "summary": str(web.get("summary") or "")[:2000],
        "sources": sources,
    }


def _stored_payload(doc_id: str, citation: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "summary": str(citation.get("summary") or ""),
        "sources": list(citation.get("sources") or []),
        "search_suggestions_html": "",
        "cached": True,
        "search_skipped": False,
        "searched_at": str(citation.get("searched_at") or ""),
    }


def _rag_query(label: str, message: str, tags: list[str] | None) -> str:
    parts = [label.strip()]
    if message.strip():
        parts.append(message.strip())
    for tag in tags or []:
        cleaned = str(tag).strip()
        if cleaned:
            parts.append(cleaned)
    return " ".join(parts)


def _summary_prompt(label: str) -> str:
    return (
        f"絵の資料として「{label}」そのものを短く説明してください。"
        "この呼び方より広い語には広げないこと。"
        "説明は検索結果に基づくこと。ライセンス、作成時期、著作権は書かないこと。"
        "本のダウンロードはしないこと。"
    )


def _library_card(hit: dict[str, Any]) -> dict[str, str]:
    return {
        "doc_id": str(hit.get("doc_id") or ""),
        "title": str(hit.get("title") or ""),
        "material_kind": str(hit.get("material_kind") or "third_party"),
        "text": str(hit.get("text") or "")[:1200],
    }


def _wants_memo(message: str) -> bool:
    """メモ作成の依頼だけを受ける。内容を尋ねる文では書かない。"""
    text = message.strip()
    if re.search(r"メモ(してある|してた|に何|の内容|は何|を見|を読|を検索|を探)", text):
        return False
    if re.search(r"メモを書(いてある|いてた|いた)", text):
        return False
    return bool(
        re.search(
            r"(メモにして|メモにしと|メモに残して|メモを作|メモを書|メモを生成|メモをまとめ|メモとして残|メモを追記|メモを更新|メモお願い|メモして|write a memo|make a memo)",
            text,
            re.IGNORECASE,
        )
    )


def _save_requested_memo(
    settings: Settings,
    owner_id: str,
    project_id: str,
    label: str,
    message: str,
    materials: list[dict[str, str]],
    memory: list[dict[str, str]],
    dialogue: list[dict[str, str]],
) -> tuple[str, bool]:
    if not project_id.strip() or not owner_id.strip():
        return "作業の記録を選ぶと、メモに足せます。", False
    if not materials and not memory and not dialogue:
        return "メモに残す抜粋がまだありません。", False
    section = _compose_memo(settings, label, message, materials, memory, dialogue)
    if not section.strip():
        return "メモを作れませんでした。", False
    if not _append_memo(owner_id, project_id, section):
        return "メモが一杯で足せませんでした。", False
    logger.info("memo appended owner=%s", owner_id[:8])
    return f"作業のメモに足しました。\n\n{section}", True


def _append_memo(owner_id: str, project_id: str, section: str) -> bool:
    from app.project_store import get_project, save_memo

    current = get_project(owner_id, project_id)
    if current is None:
        return False
    existing = str(current.get("memo") or "")
    block = f"## チャットからのメモ\n\n{section.strip()}"
    if existing.strip():
        joined = existing.rstrip() + "\n\n" + block
    else:
        joined = block
    if len(joined) > 20000:
        room = 20000 - len(existing.rstrip()) - 2
        if room < 40:
            return False
        joined = (existing.rstrip() + "\n\n" + block)[:20000]
    return save_memo(owner_id, project_id, joined) is not None


def _compose_memo(
    settings: Settings,
    label: str,
    message: str,
    materials: list[dict[str, str]],
    memory: list[dict[str, str]],
    dialogue: list[dict[str, str]],
) -> str:
    fallback = _memo_fallback(message, materials, memory, dialogue)
    packed = _context_pack(materials, memory, dialogue)
    if not settings.gemini_model or not packed.strip():
        return fallback
    prompt = (
        f"物体「{label}」の作業メモを、マークダウンの箇条書きで書いてください。\n"
        "下の会話と抜粋に無いことは書かないこと。権利は抜粋に書いてある文だけ。使ってよいかは書かないこと。\n"
        "絵は生成しないこと。ウェブ検索はしないこと。先頭に大見出しは付けないこと。\n"
        f"{packed}\n依頼: {message}"
    )
    text = _generate_text(settings, prompt, 1024)
    return text or fallback


def _memo_fallback(
    message: str,
    materials: list[dict[str, str]],
    memory: list[dict[str, str]],
    dialogue: list[dict[str, str]],
) -> str:
    lines = [f"- 依頼: {message.strip()[:400]}"]
    for item in dialogue[-3:]:
        lines.append(f"- 質問: {item['message']}")
        if item["answer"]:
            lines.append(f"  - 返答: {item['answer']}")
    for item in memory:
        lines.append(f"- {item.get('project_name') or ''} / {item.get('title') or ''}: {(item.get('text') or '')[:400]}")
    for item in materials:
        lines.append(f"- {item.get('title') or item.get('doc_id')}: {(item.get('text') or '')[:400]}")
    return "\n".join(lines)[:4000]


def _context_pack(
    materials: list[dict[str, str]],
    memory: list[dict[str, str]],
    dialogue: list[dict[str, str]],
) -> str:
    turns = "\n".join(f"質問: {item['message']}\n返答: {item['answer']}" for item in dialogue)
    notes = "\n\n".join(
        f"[{item.get('project_name') or ''} / {item.get('title') or ''}]\n{item.get('text') or ''}"
        for item in memory
        if item.get("text")
    )
    library = "\n\n".join(
        f"[{item['title']}]\n{item['text'][:800]}" for item in materials if item.get("text")
    )
    return f"直近の会話:\n{turns or 'なし'}\n\n作業の記録:\n{notes or 'なし'}\n\n資料庫:\n{library or 'なし'}"


def _generate_text(settings: Settings, prompt: str, max_tokens: int) -> str:
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(http_options=types.HttpOptions(timeout=30_000))
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=max_tokens),
        )
    except Exception:
        logger.exception("library answer failed model=%s", settings.gemini_model)
        return ""
    return (response.text or "").strip()


def _recent_dialogue(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in list(history or [])[-6:]:
        message = str(item.get("message") or "").strip()[:400]
        answer = str(item.get("answer") or "").strip()[:400]
        if message:
            rows.append({"message": message, "answer": answer})
    return rows


def _library_answer(
    settings: Settings,
    label: str,
    message: str,
    materials: list[dict[str, str]],
    memory: list[dict[str, str]] | None = None,
    dialogue: list[dict[str, str]] | None = None,
) -> str:
    notes = list(memory or [])
    turns = list(dialogue or [])
    titles = "、".join(
        [item["title"] or item["doc_id"] for item in materials]
        + [f"{item.get('project_name') or ''}/{item.get('title') or ''}" for item in notes]
    )
    fallback = f"手元の資料を開きました: {titles}" if titles else "直前の会話を参照してください。"
    packed_notes = "\n\n".join(
        f"[{item.get('project_name') or ''} / {item.get('title') or ''}]\n{item.get('text') or ''}"
        for item in notes
        if item.get("text")
    )
    packed_library = "\n\n".join(
        f"[{item['title']}]\n{item['text'][:800]}" for item in materials if item["text"]
    )
    packed_turns = "\n".join(
        f"質問: {item['message']}\n返答: {item['answer']}" for item in turns
    )
    if not settings.gemini_model or not (packed_notes or packed_library or packed_turns):
        return fallback
    prompt = (
        f"物体「{label}」について、下の会話と抜粋だけで短く答えてください。\n"
        "権利は抜粋に書いてある文だけを残してください。使ってよいかは判断しないこと。\n"
        "抜粋に無いことは書かないこと。絵は生成しないこと。ウェブ検索はしないこと。\n"
        f"直近の会話:\n{packed_turns or 'なし'}\n\n"
        f"作業の記録:\n{packed_notes or 'なし'}\n\n"
        f"資料庫:\n{packed_library or 'なし'}\n\n"
        f"質問: {message}"
    )
    text = _generate_text(settings, prompt, 256)
    return text or fallback


def _term_from_text(text: str) -> str:
    """本文の題名か作者の行だけを取り出す。本文全体は外に出さない。"""
    for line in text.splitlines():
        body = line.strip()
        lower = body.casefold()
        for prefix in ("題名:", "題名：", "作者:", "作者：", "title:", "author:"):
            if lower.startswith(prefix):
                return rights_query(user_query=body.split(":", 1)[-1].split("：", 1)[-1])
    return ""


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


def _merge_unique(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in primary + secondary:
        key = item.get("url") or item.get("title") or ""
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


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
        records.append({"url": url, "title": title, "text": text, "material_kind": "web"})
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
