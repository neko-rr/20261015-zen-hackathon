"""Jev はテキスト判定だけ。キーと本文はログに出さない。"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# これ未満は未確認、または枠を出さない。実データで後から調整する。
ACT_THRESHOLD = 0.7


def jev_available() -> bool:
    return bool(os.getenv("TYPESAFE_API_KEY", "").strip())


def ask(state: dict[str, Any], questions: dict[str, Any]) -> Any:
    """1 回の system_one。失敗は上位へ送る。"""
    if not state or not questions:
        raise ValueError("empty jev request")
    try:
        from typesafe_sdk import TypeSafeClient, TypeSafeError
    except ImportError:
        logger.exception("jev sdk missing")
        raise

    try:
        with TypeSafeClient() as client:
            return client.system_one(state=state, questions=questions)
    except TypeSafeError:
        logger.exception("jev failed")
        raise


def read_noul(response: Any, key: str) -> float | None:
    item = _answer(response, key, "nouls")
    if item is None:
        return None
    value = item.get("noul") if isinstance(item, dict) else getattr(item, "noul", None)
    if value is None:
        return None
    return float(value)


def read_choice(response: Any, key: str) -> tuple[str, float] | None:
    item = _answer(response, key, "choices")
    if item is None:
        return None
    if isinstance(item, dict):
        choice = str(item.get("choice") or "")
        confidence = item.get("confidence")
    else:
        choice = str(getattr(item, "choice", "") or "")
        confidence = getattr(item, "confidence", None)
    if not choice or confidence is None:
        return None
    return choice, float(confidence)


def _answer(response: Any, key: str, bucket: str) -> Any:
    answers = getattr(response, "answers", None)
    if isinstance(answers, dict) and key in answers:
        return answers[key]
    grouped = getattr(response, bucket, None)
    if isinstance(grouped, dict) and key in grouped:
        return grouped[key]
    return None
