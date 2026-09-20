"""絵描き資料 API。Gemini はここからだけ呼ぶ。"""

import logging

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.analyze import analyze_image
from app.errors import business_error, register_error_handlers
from app.lookup import answer_question, lookup_object
from app.settings import ALLOWED_IMAGE_TYPES, MAX_IMAGE_BYTES, load_settings, require_gemini
from app.store import add_lookup, create_photo, get_photo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = load_settings()
app = FastAPI(title="draw-reference-api")
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class LookupRequest(BaseModel):
    object_id: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/photos")
async def create_photo_analysis(file: UploadFile = File(...)) -> dict:
    mime_type = (file.content_type or "").split(";")[0].strip().lower()
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise business_error("unsupported_type", "JPEG、PNG、WebP のいずれかを上げてください。")

    image = await file.read()
    if not image:
        raise business_error("invalid_image", "写真が空です。")
    if len(image) > MAX_IMAGE_BYTES:
        raise business_error("image_too_large", "写真は 10MB 以下にしてください。")

    require_gemini(settings)
    objects = analyze_image(settings, image, mime_type)
    photo_id = create_photo(objects)
    logger.info("decide photo_id=%s object_count=%s", photo_id, len(objects))
    return {"photo_id": photo_id, "objects": objects}


@app.post("/photos/{photo_id}/lookups")
def create_lookup(photo_id: str, body: LookupRequest) -> dict:
    if not photo_id.strip() or not body.object_id.strip():
        raise business_error("object_not_found", "物体が見つかりません。")

    photo = get_photo(photo_id)
    if photo is None:
        raise business_error("object_not_found", "写真が見つかりません。")

    target = next(
        (item for item in photo["objects"] if item["object_id"] == body.object_id),
        None,
    )
    if target is None:
        raise business_error("object_not_found", "物体が見つかりません。")

    require_gemini(settings)
    result = lookup_object(settings, target["label"])
    lookup = {"object_id": body.object_id, **result}
    add_lookup(photo_id, lookup)
    return lookup


@app.get("/photos/{photo_id}/lookups")
def list_lookups(photo_id: str) -> dict:
    if not photo_id.strip():
        raise business_error("object_not_found", "写真が見つかりません。")
    photo = get_photo(photo_id)
    if photo is None:
        raise business_error("object_not_found", "写真が見つかりません。")
    return {"lookups": photo["lookups"]}
