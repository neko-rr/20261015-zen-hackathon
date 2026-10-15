"""向き判定の試行。正解つきの画像を作り、MediaPipe と Gemini の一致を採点する。

画像が無ければ Gemini の画像生成で足す。キーはログに出さない。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.facing import judge_landmarks, orient_person
from app.pose import estimate_pose
from app.settings import load_settings

FIXTURE = ROOT / "tests" / "fixtures" / "facing"
CASES = (
    ("front", "正面を向いて立っている成人一人。全身が写る。無地の灰色の背景。文字や透かしは無し。"),
    ("back", "背中をカメラに向けて立っている成人一人。後頭部が見える。全身が写る。無地の灰色の背景。文字は無し。"),
    ("left", "カメラに向かって左向きの横顔で立っている成人一人。顔は画像の左を向く。全身が写る。無地の灰色の背景。文字は無し。"),
    ("right", "カメラに向かって右向きの横顔で立っている成人一人。顔は画像の右を向く。全身が写る。無地の灰色の背景。文字は無し。"),
    ("front", "椅子に座って正面を向いている成人一人。全身が写る。無地の灰色の背景。文字は無し。"),
    ("front", "正面を向いて両手を上げて立っている成人一人。全身が写る。無地の灰色の背景。文字は無し。"),
)
_IMAGE_MODELS = (
    "gemini-2.5-flash-image",
    "gemini-2.0-flash-preview-image-generation",
)


def main() -> int:
    FIXTURE.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    _ensure_images(settings)
    rows = []
    passed = 0
    for index, (expected, _prompt) in enumerate(CASES, start=1):
        path = FIXTURE / f"{index:02d}-{expected}.png"
        if not path.is_file():
            rows.append({"file": path.name, "expected": expected, "error": "missing"})
            continue
        image = path.read_bytes()
        pose = estimate_pose(image, "image/png")
        landmarks = list(pose.get("landmarks") or [])
        mechanical = judge_landmarks(landmarks) if landmarks else {"facing": "unknown", "confidence": 0}
        _corrected, report = orient_person(settings, image, "image/png", landmarks)
        ok = report["facing"] == expected
        passed += int(ok)
        rows.append(
            {
                "file": path.name,
                "expected": expected,
                "mechanical": mechanical.get("facing"),
                "decided": report["facing"],
                "source": report["source"],
                "swapped": report["swapped"],
                "confidence": report["confidence"],
                "landmarks": len(landmarks),
                "ok": ok,
            }
        )
    summary = {"passed": passed, "total": len(rows), "rows": rows}
    (FIXTURE / "score.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed == len(rows) and rows else 1


def _ensure_images(settings) -> None:
    missing = [item for item in _paths() if not item[0].is_file()]
    if not missing:
        return
    if not settings.gemini_model:
        print("skip image generation: model unset")
        return
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("skip image generation: sdk missing")
        return
    client = genai.Client(http_options=types.HttpOptions(timeout=60_000))
    for path, prompt in missing:
        data = _generate(client, types, prompt)
        if not data:
            print(f"image failed file={path.name}")
            continue
        path.write_bytes(data)
        print(f"image wrote file={path.name} bytes={len(data)}")


def _paths() -> list[tuple[Path, str]]:
    rows = []
    for index, (expected, prompt) in enumerate(CASES, start=1):
        rows.append((FIXTURE / f"{index:02d}-{expected}.png", prompt))
    return rows


def _generate(client, types, prompt: str) -> bytes:
    for model in _IMAGE_MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
            )
        except Exception:
            continue
        data = _first_image(response)
        if data:
            return data
    return b""


def _first_image(response) -> bytes:
    candidates = getattr(response, "candidates", None) or []
    parts = []
    if candidates:
        content = getattr(candidates[0], "content", None)
        parts = list(getattr(content, "parts", None) or [])
    parts.extend(list(getattr(response, "parts", None) or []))
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is None:
            continue
        data = getattr(inline, "data", None)
        if isinstance(data, bytes) and data:
            return data
        if isinstance(data, str) and data:
            import base64

            try:
                return base64.b64decode(data)
            except Exception:
                continue
    return b""


if __name__ == "__main__":
    raise SystemExit(main())
