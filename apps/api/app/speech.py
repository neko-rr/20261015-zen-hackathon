"""短いポーズの言葉を Cloud Speech-to-Text で文字にする。座標は作らない。"""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from typing import Any

from app.errors import business_error

logger = logging.getLogger(__name__)

_RECOGNIZE_URL = "https://speech.googleapis.com/v1/speech:recognize"
_TIMEOUT_SECONDS = 20
_MAX_AUDIO_BYTES = 1_500_000
_MAX_TEXT = 500


def transcribe_pose(audio: bytes, language: str) -> str:
    """WAV の録音を、ポーズ用の短い文にする。失敗は業務エラー。"""
    if not audio:
        raise business_error("speech_empty", "録音が空です。もう一度話すか、言葉を入力してください。")
    if len(audio) > _MAX_AUDIO_BYTES:
        raise business_error("audio_too_large", "録音が長すぎます。短く話してください。")
    pcm, rate = pcm_from_wav(audio)
    primary, alternate = _languages(language)
    try:
        payload = _recognize(pcm, rate, primary, alternate)
    except Exception:
        logger.exception("speech recognize failed")
        raise business_error(
            "speech_unavailable",
            "音声認識を使えませんでした。言葉を入力してください。",
        ) from None
    return text_from_response(payload)[:_MAX_TEXT]


def text_from_response(payload: Any) -> str:
    """認識結果の本文だけを繋ぐ。"""
    if not isinstance(payload, dict):
        return ""
    parts: list[str] = []
    for result in payload.get("results") or []:
        if not isinstance(result, dict):
            continue
        alternatives = result.get("alternatives") or []
        if not alternatives or not isinstance(alternatives[0], dict):
            continue
        text = " ".join(str(alternatives[0].get("transcript") or "").split())
        if text:
            parts.append(text)
    return " ".join(parts)


def pcm_from_wav(audio: bytes) -> tuple[bytes, int]:
    """16bit PCM の WAV から、モノラルの中身とサンプルレートを取る。"""
    if len(audio) < 44 or audio[0:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise business_error("unsupported_audio", "録音の形式を読めませんでした。")
    offset = 12
    rate = 0
    channels = 0
    bits = 0
    data = b""
    while offset + 8 <= len(audio):
        chunk = audio[offset : offset + 4]
        size = int.from_bytes(audio[offset + 4 : offset + 8], "little")
        body = audio[offset + 8 : offset + 8 + size]
        if chunk == b"fmt " and len(body) >= 16:
            audio_format = int.from_bytes(body[0:2], "little")
            channels = int.from_bytes(body[2:4], "little")
            rate = int.from_bytes(body[4:8], "little")
            bits = int.from_bytes(body[14:16], "little")
            if audio_format != 1 or bits != 16 or channels not in (1, 2):
                raise business_error("unsupported_audio", "録音の形式を読めませんでした。")
        elif chunk == b"data":
            data = body
            break
        offset += 8 + size + (size % 2)
    if not data or rate < 8000 or rate > 48000:
        raise business_error("unsupported_audio", "録音の形式を読めませんでした。")
    if channels == 2:
        data = _left_channel(data)
    return data, rate


def _left_channel(data: bytes) -> bytes:
    samples = memoryview(data)
    mono = bytearray()
    for index in range(0, len(samples) - 3, 4):
        mono.extend(samples[index : index + 2])
    return bytes(mono)


def _languages(language: str) -> tuple[str, str]:
    if (language or "").strip().lower().startswith("en"):
        return "en-US", "ja-JP"
    return "ja-JP", "en-US"


def _recognize(pcm: bytes, rate: int, primary: str, alternate: str) -> Any:
    import google.auth
    from google.auth.transport.requests import Request

    credentials, _project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(Request())
    token = getattr(credentials, "token", "")
    if not token:
        raise RuntimeError("speech token missing")
    body = {
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": rate,
            "languageCode": primary,
            "alternativeLanguageCodes": [alternate],
            "model": "latest_short",
            "maxAlternatives": 1,
        },
        "audio": {"content": base64.b64encode(pcm).decode("ascii")},
    }
    request = urllib.request.Request(
        _RECOGNIZE_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"speech http {exc.code}") from None
