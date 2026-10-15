"""写真から物体の名前だけを取る。座標は返さない。失敗しても解析は続ける。"""

import json
import logging
import re
from typing import Any

from app.settings import Settings

logger = logging.getLogger(__name__)

_MAX_OTHERS = 4
_MAX_LABEL = 80
_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_GENERIC_NAME = {"人", "女性", "男性", "子供", "子ども", "不明", "unknown", "none", "n/a"}


def name_subjects(settings: Settings, image: bytes, mime_type: str) -> dict[str, Any]:
    """見た目の呼び方。公開人物だと分かるときだけ名前。失敗時は空。"""
    if not image or not settings.gemini_model:
        return _empty()
    image, mime_type = _shrink(image, mime_type)

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.exception("label sdk missing")
        return _empty()

    try:
        client = genai.Client(http_options=types.HttpOptions(timeout=30_000))
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                types.Part.from_bytes(data=image, mime_type=mime_type),
                _prompt(),
            ],
            config=types.GenerateContentConfig(temperature=0),
        )
        text = (response.text or "").strip()
    except Exception:
        logger.exception("label naming failed model=%s", settings.gemini_model)
        return _empty()

    parsed = _parse(text)
    logger.info(
        "label named people=%s others=%s",
        len(parsed["people"]),
        len(parsed["others"]),
    )
    return parsed


def labels_from_text(text: str) -> dict[str, Any]:
    """モデル出力の JSON を呼び方に直す。テスト用。"""
    return _parse(text)


def _prompt() -> str:
    return (
        "この写真に写っているものを、絵の資料用に短く名付けてください。"
        "JSON だけを返してください。"
        '{"people":[{"label":"","public_name":"","work_title":""}],"others":[{"label":"","kind":"object","work_title":""}]}'
        "people は写っている人を、左から右へ最大4人です。"
        "label は見た目の一般的な呼び方です。年齢の目安、分かるときだけ女性か男性、目立つ衣服。"
        "例: 成人の女性、白いシャツ。固有名詞は label に入れないでください。"
        "人が写っていなければ people は空にしてください。"
        "public_name は、公開の人物だと自信があるときだけ書いてください。"
        "少しでも迷うなら空です。一般人の名前は書かないでください。"
        "work_title は、写真の中に読める作品名・建物名・看板、または迷わず特定できる有名な作品名だけです。"
        "少しでも迷うなら空です。"
        "others は人以外で絵の資料になるもの。最大4件。"
        "服は person の label に含め、ここでは建物、場所、乗り物、動物、道具にしてください。"
        "kind は animal か object だけ。分からない項目は空にしてください。"
        "著作権者の断定はしないでください。"
    )


def _shrink(image: bytes, mime_type: str) -> tuple[bytes, str]:
    """呼び方用に長辺 768 まで縮める。関節には使わない。"""
    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(image)) as picture:
            rgb = picture.convert("RGB")
            rgb.thumbnail((768, 768))
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=80)
            return buffer.getvalue(), "image/jpeg"
    except Exception:
        logger.exception("label shrink skipped")
        return image, mime_type


def _empty() -> dict[str, Any]:
    return {"person_label": "", "public_name": "", "people": [], "others": []}


def _parse(text: str) -> dict[str, Any]:
    empty = _empty()
    if not text.strip():
        return empty
    fenced = _FENCE.search(text)
    raw = fenced.group(1) if fenced else text
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return empty
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return empty
    if not isinstance(data, dict):
        return empty

    people = _people(data)
    person = people[0]["label"] if people else ""
    public = people[0]["public_name"] if people else ""

    others: list[dict[str, str]] = []
    raw_others = data.get("others")
    if isinstance(raw_others, list):
        for item in raw_others:
            if len(others) >= _MAX_OTHERS or not isinstance(item, dict):
                continue
            label = _clip(str(item.get("label") or ""))
            kind = str(item.get("kind") or "").strip()
            if not label or kind not in ("animal", "object"):
                continue
            if label == person:
                continue
            others.append({"label": label, "kind": kind, "work_title": _specific(str(item.get("work_title") or ""))})
    return {"person_label": person, "public_name": public, "people": people, "others": others}


def _people(data: dict[str, Any]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    raw_people = data.get("people")
    if isinstance(raw_people, list):
        for item in raw_people:
            if len(found) >= 4 or not isinstance(item, dict):
                continue
            label = _clip(str(item.get("label") or ""))
            public = _specific(str(item.get("public_name") or ""))
            work_title = _specific(str(item.get("work_title") or ""))
            if not label and not public and not work_title:
                continue
            found.append({"label": label, "public_name": public, "work_title": work_title})
    if found:
        return found
    label = _clip(str(data.get("person_label") or ""))
    public = _specific(str(data.get("public_name") or ""))
    work_title = _specific(str(data.get("work_title") or ""))
    if not label and not public and not work_title:
        return []
    return [{"label": label, "public_name": public, "work_title": work_title}]


def _specific(value: str) -> str:
    text = _clip(value)
    if text.casefold() in _GENERIC_NAME:
        return ""
    return text


def _clip(value: str) -> str:
    return " ".join(value.split())[:_MAX_LABEL]
