"""作業のメモ・チャット文言・出典記録を、質問の語で拾う。人の中だけ。"""

from __future__ import annotations

import re

from app.project_store import list_projects

_SKIP = set("のはがをにでとへもやねよ、。")
_CHUNK = 800


def retrieve_project_memory(
    owner_id: str,
    query: str,
    active_project_id: str = "",
    limit: int = 4,
) -> list[dict[str, str]]:
    """質問と重なる抜粋を最大 limit 件。選んでいる作業を先にする。"""
    if not owner_id.strip() or not query.strip() or limit <= 0:
        return []
    need = 1 if len(_compact(query)) <= 2 else 2
    active_id = active_project_id.strip()
    active: list[tuple[int, dict[str, str]]] = []
    others: list[tuple[int, dict[str, str]]] = []
    for project in list_projects(owner_id):
        if str(project.get("owner_id") or "") != owner_id:
            continue
        project_id = str(project.get("project_id") or "")
        name = str(project.get("name") or "")
        bucket = active if project_id and project_id == active_id else others
        for card in _cards(project, name, project_id):
            score = _score(query, card["text"])
            if score >= need:
                bucket.append((score, card))
    active.sort(key=lambda item: item[0], reverse=True)
    others.sort(key=lambda item: item[0], reverse=True)
    picked: list[dict[str, str]] = []
    for _score_value, card in active + others:
        public = dict(card)
        public.pop("key", None)
        picked.append(public)
        if len(picked) >= limit:
            break
    return picked


def _cards(project: dict, name: str, project_id: str) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for index, chunk in enumerate(_chunks(str(project.get("memo") or ""))):
        cards.append(_card("memo", name, project_id, "メモ", chunk, index))
    for index, prompt in enumerate(list(project.get("prompts") or [])):
        if not isinstance(prompt, dict):
            continue
        text = f"{prompt.get('message') or ''}\n{prompt.get('answer') or ''}".strip()
        if not text:
            continue
        label = str(prompt.get("label") or "チャット")
        cards.append(_card("prompt", name, project_id, label, text[:_CHUNK], index))
    for index, citation in enumerate(list(project.get("citations") or [])):
        if not isinstance(citation, dict):
            continue
        lines = [str(citation.get("title") or ""), str(citation.get("term") or "")]
        for source in list(citation.get("sources") or [])[:4]:
            if not isinstance(source, dict):
                continue
            lines.append(
                " ".join(
                    part
                    for part in (
                        str(source.get("title") or ""),
                        str(source.get("license") or ""),
                        str(source.get("copyright") or ""),
                        str(source.get("created") or ""),
                    )
                    if part and part != "unknown"
                )
            )
        text = "\n".join(line for line in lines if line.strip())
        if text.strip():
            cards.append(_card("citation", name, project_id, str(citation.get("title") or "出典"), text[:_CHUNK], index))
    return cards


def _card(source: str, name: str, project_id: str, title: str, text: str, index: int) -> dict[str, str]:
    return {
        "source": source,
        "project_id": project_id,
        "project_name": name,
        "title": title[:180],
        "text": text[:_CHUNK],
        "key": f"{project_id}:{source}:{index}",
    }


def _chunks(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    for part in parts:
        for start in range(0, len(part), _CHUNK):
            chunks.append(part[start : start + _CHUNK])
    return chunks


def _score(query: str, text: str) -> int:
    left = _pieces(query)
    if not left:
        return 0
    return len(left & _pieces(text))


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _pieces(text: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9]{2,}", text.lower()))
    body = "".join(
        char
        for char in text.lower()
        if char.isalnum() or "\u3040" <= char <= "\u30ff" or "\u4e00" <= char <= "\u9fff"
    )
    grams = set(words)
    for index in range(len(body) - 1):
        pair = body[index : index + 2]
        if pair[0] in _SKIP and pair[1] in _SKIP:
            continue
        grams.add(pair)
    if len(body) <= 2:
        for char in body:
            if char not in _SKIP:
                grams.add(char)
    return grams
