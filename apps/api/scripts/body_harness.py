"""手足の試行。正解つきの写真で、腕の上下と膝の高さを採点する。

既存の向き画像を使い、足りないポーズだけ生成する。キーはログに出さない。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.limbs import arm_pose, refine_limbs
from app.pose import estimate_pose, parts_from_landmarks
from app.settings import load_settings

BODY = ROOT / "tests" / "fixtures" / "body"
FACING = ROOT / "tests" / "fixtures" / "facing"
_IMAGE_MODELS = (
    "gemini-2.5-flash-image",
    "gemini-2.0-flash-preview-image-generation",
)


def main() -> int:
    BODY.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    _ensure_images(settings)
    rows = []
    passed = 0
    for case in _cases():
        path = case["path"]
        if not path.is_file():
            rows.append({"file": path.name, "error": "missing", "ok": False})
            continue
        image = path.read_bytes()
        pose = estimate_pose(image, "image/png")
        landmarks = list(pose.get("landmarks") or [])
        corrected, report = refine_limbs(settings, image, "image/png", landmarks)
        parts = parts_from_landmarks(corrected)
        checks = _checks(case, corrected, parts)
        ok = bool(landmarks) and all(checks.values())
        passed += int(ok)
        rows.append(
            {
                "file": path.name,
                "checks": checks,
                "dropped": report["dropped"],
                "swapped_arms": report["swapped_arms"],
                "source": report["source"],
                "landmarks": len(corrected),
                "ok": ok,
            }
        )
    summary = {"passed": passed, "total": len(rows), "rows": rows}
    (BODY / "score.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed == len(rows) and rows else 1


def _cases() -> list[dict]:
    return [
        {"path": FACING / "01-front.png", "left_arm": "down", "right_arm": "down"},
        {"path": FACING / "06-front.png", "left_arm": "raised", "right_arm": "raised"},
        {"path": BODY / "01-left-arm-up.png", "left_arm": "down", "right_arm": "raised"},
        {"path": BODY / "02-right-arm-up.png", "left_arm": "down", "right_arm": "raised"},
        {"path": BODY / "03-left-knee-up.png", "raised_knee": "right"},
        {"path": BODY / "04-cropped.png", "left_arm": "down", "right_arm": "raised", "knees_absent": True},
    ]


def _checks(case: dict, landmarks: list[dict], parts: dict) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    if "left_arm" in case:
        checks["left_arm"] = arm_pose(landmarks, "left") == case["left_arm"]
    if "right_arm" in case:
        checks["right_arm"] = arm_pose(landmarks, "right") == case["right_arm"]
    if case.get("raised_knee"):
        checks["raised_knee"] = _knee_side(landmarks) == case["raised_knee"]
    if case.get("knees_absent"):
        indexes = {int(item["index"]) for item in landmarks if "index" in item}
        checks["knees_absent"] = 25 not in indexes and 26 not in indexes
    checks["deltoid_near_left_shoulder"] = _deltoid_near_shoulder(landmarks, parts)
    return checks


def _knee_side(landmarks: list[dict]) -> str:
    points = {int(item["index"]): item for item in landmarks if "index" in item}
    if 25 not in points or 26 not in points:
        return "hidden"
    left = float(points[25]["y"])
    right = float(points[26]["y"])
    if left < right - 0.04:
        return "left"
    if right < left - 0.04:
        return "right"
    return "level"


def _deltoid_near_shoulder(landmarks: list[dict], parts: dict) -> bool:
    points = {int(item["index"]): item for item in landmarks if "index" in item}
    left = next((item for item in parts.get("muscles") or [] if item.get("name") == "左三角筋"), None)
    if left is None or 11 not in points or 12 not in points:
        return False
    return abs(float(left["x"]) - float(points[11]["x"])) < abs(float(left["x"]) - float(points[12]["x"]))


def _ensure_images(settings) -> None:
    missing = [item for item in _new_images() if not item[0].is_file()]
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
            data = _generate(client, types, prompt + " 写真。一人だけ。")
        if not data:
            print(f"image failed file={path.name}")
            continue
        path.write_bytes(data)
        print(f"image wrote file={path.name} bytes={len(data)}")


def _new_images() -> list[tuple[Path, str]]:
    return [
        (
            BODY / "01-left-arm-up.png",
            "正面を向いて立っている成人一人。画像の右側の腕だけを頭の上まで上げ、画像の左側の腕は体の横に下ろす。足先まで全身が写る。無地の灰色の背景。文字は無し。",
        ),
        (
            BODY / "02-right-arm-up.png",
            "正面を向いて立っている成人一人。本人の右手だけを頭の上まで上げ、左手は体の横に下ろしている。全身が写る。無地の灰色の背景。文字は無し。",
        ),
        (
            BODY / "03-left-knee-up.png",
            "正面を向いて立っている成人一人。本人の左膝だけを腰の高さまで上げ、右足は地面に着いている。全身が写る。無地の灰色の背景。文字は無し。",
        ),
    ]


def _generate(client, types, prompt: str) -> bytes:
    for model in _IMAGE_MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
            )
        except Exception as exc:
            print(f"image model failed type={type(exc).__name__}")
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
