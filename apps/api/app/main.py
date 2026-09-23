"""絵描き資料 API。Gemini はここからだけ呼ぶ。"""

import logging

from fastapi import FastAPI, File, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.analyze import analyze_image
from app.auth import (
    attach_session_cookie,
    mint_session_id,
    principal_from_request,
    require_principal,
    require_signing_secret,
)
from app.errors import business_error, register_error_handlers
from app.lookup import answer_question, lookup_object
from app.materials import (
    delete_material,
    list_owner_materials,
    list_owner_tags,
    patch_material,
    register_material,
)
from app.material_store import count_materials_in_project
from app.project_store import create_project, delete_project, list_projects
from app.settings import ALLOWED_IMAGE_TYPES, MAX_IMAGE_BYTES, load_settings, require_gemini
from app.store import add_lookup, add_question, create_photo, get_photo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = load_settings()
app = FastAPI(title="draw-reference-api")
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["*"],
)


class LookupRequest(BaseModel):
    object_id: str
    tags: list[str] = []
    project_id: str = ""


class QuestionRequest(BaseModel):
    object_id: str
    message: str
    tags: list[str] = []
    project_id: str = ""


class ProjectCreate(BaseModel):
    name: str


class MaterialPatch(BaseModel):
    tags: list[str] | None = None
    project_id: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sessions")
def create_or_resume_session(request: Request, response: Response) -> dict:
    """既存 Cookie があれば継続。無ければ新しい session_id を発行する。"""
    require_signing_secret(settings.session_signing_secret)
    existing = principal_from_request(request, settings.session_signing_secret)
    if existing is not None:
        attach_session_cookie(
            response,
            existing.id,
            settings.session_signing_secret,
            secure=settings.session_cookie_secure,
        )
        return {"session_id": existing.id, "kind": existing.kind}
    session_id = mint_session_id()
    attach_session_cookie(
        response,
        session_id,
        settings.session_signing_secret,
        secure=settings.session_cookie_secure,
    )
    logger.info("session_created")
    return {"session_id": session_id, "kind": "session"}


@app.get("/sessions/me")
def current_session(request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    return {"session_id": principal.id, "kind": principal.kind}


@app.post("/photos")
async def create_photo_analysis(request: Request, file: UploadFile = File(...)) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    mime_type = (file.content_type or "").split(";")[0].strip().lower()
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise business_error("unsupported_type", "JPEG、PNG、WebP のいずれかを上げてください。")

    image = await file.read()
    if not image:
        raise business_error("invalid_image", "写真が空です。")
    if len(image) > MAX_IMAGE_BYTES:
        raise business_error("image_too_large", "写真は 10MB 以下にしてください。")

    analysis = analyze_image(settings, image, mime_type)
    objects = analysis["objects"]
    pose = analysis.get("pose") or {"landmarks": [], "edges": [], "muscles": []}
    photo_id = create_photo(objects, principal.id, pose=pose)
    logger.info(
        "decide photo_id=%s object_count=%s pose_landmarks=%s",
        photo_id,
        len(objects),
        len(pose.get("landmarks") or []),
    )
    return {"photo_id": photo_id, "objects": objects, "pose": pose}


@app.post("/photos/{photo_id}/lookups")
def create_lookup(photo_id: str, body: LookupRequest, request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    if not photo_id.strip() or not body.object_id.strip():
        raise business_error("object_not_found", "物体が見つかりません。")

    photo = get_photo(photo_id, principal.id)
    if photo is None:
        raise business_error("object_not_found", "写真が見つかりません。")

    target = next(
        (item for item in photo["objects"] if item["object_id"] == body.object_id),
        None,
    )
    if target is None:
        raise business_error("object_not_found", "物体が見つかりません。")

    require_gemini(settings)
    result = lookup_object(
        settings,
        target["label"],
        owner_id=principal.id,
        tags=body.tags,
        project_id=body.project_id,
    )
    lookup = {"object_id": body.object_id, **result}
    if not add_lookup(photo_id, principal.id, lookup):
        raise business_error("object_not_found", "写真が見つかりません。")
    return lookup


@app.get("/photos/{photo_id}/lookups")
def list_lookups(photo_id: str, request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    if not photo_id.strip():
        raise business_error("object_not_found", "写真が見つかりません。")
    photo = get_photo(photo_id, principal.id)
    if photo is None:
        raise business_error("object_not_found", "写真が見つかりません。")
    return {"lookups": photo["lookups"]}


@app.post("/photos/{photo_id}/questions")
def create_question(photo_id: str, body: QuestionRequest, request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    if not photo_id.strip() or not body.object_id.strip():
        raise business_error("object_not_found", "物体が見つかりません。")
    message = body.message.strip()
    if not message:
        raise business_error("empty_message", "質問を入力してください。")

    photo = get_photo(photo_id, principal.id)
    if photo is None:
        raise business_error("object_not_found", "写真が見つかりません。")

    target = next(
        (item for item in photo["objects"] if item["object_id"] == body.object_id),
        None,
    )
    if target is None:
        raise business_error("object_not_found", "物体が見つかりません。")

    require_gemini(settings)
    result = answer_question(
        settings,
        target["label"],
        message,
        owner_id=principal.id,
        tags=body.tags,
        project_id=body.project_id,
    )
    question = {
        "object_id": body.object_id,
        "message": message,
        **result,
    }
    if not add_question(photo_id, principal.id, question):
        raise business_error("object_not_found", "写真が見つかりません。")
    return question


@app.get("/photos/{photo_id}/questions")
def list_questions(photo_id: str, request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    if not photo_id.strip():
        raise business_error("object_not_found", "写真が見つかりません。")
    photo = get_photo(photo_id, principal.id)
    if photo is None:
        raise business_error("object_not_found", "写真が見つかりません。")
    return {"questions": photo["questions"]}


@app.post("/materials")
async def create_materials(
    request: Request,
    material_kind: str,
    files: list[UploadFile] = File(...),
    project_id: str = "",
) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    if not files:
        raise business_error("invalid_material", "ファイルを選んでください。")
    created: list[dict] = []
    errors: list[dict] = []
    for upload in files:
        name = upload.filename or "file"
        try:
            raw = await upload.read()
            item = register_material(
                principal.id,
                material_kind,
                name,
                upload.content_type,
                raw,
                project_id=project_id,
            )
            created.append(item)
        except Exception as exc:
            from app.errors import AppError

            if isinstance(exc, AppError):
                errors.append({"filename": name, "code": exc.code, "message": exc.message})
            else:
                logger.exception("material upload failed")
                errors.append(
                    {
                        "filename": name,
                        "code": "material_failed",
                        "message": "資料の保存に失敗しました。",
                    }
                )
    if not created and errors:
        first = errors[0]
        raise business_error(first["code"], first["message"])
    return {"materials": created, "errors": errors}


@app.get("/materials")
def get_materials(request: Request, project_id: str = "") -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    return {
        "materials": list_owner_materials(principal.id, project_id=project_id),
        "tags": list_owner_tags(principal.id),
    }


@app.patch("/materials/{doc_id}")
def patch_material_route(doc_id: str, body: MaterialPatch, request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    item = patch_material(
        principal.id,
        doc_id,
        tags=body.tags,
        project_id=body.project_id,
    )
    return {"material": item}


@app.delete("/materials/{doc_id}")
def remove_material_route(doc_id: str, request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    delete_material(principal.id, doc_id)
    return {"ok": True}


@app.get("/projects")
def get_projects(request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    return {"projects": list_projects(principal.id)}


@app.post("/projects")
def post_project(body: ProjectCreate, request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    name = body.name.strip()
    if not name:
        raise business_error("invalid_project", "案件名を入力してください。")
    return {"project": create_project(principal.id, name)}


@app.delete("/projects/{project_id}")
def remove_project(project_id: str, request: Request) -> dict:
    principal = require_principal(request, settings.session_signing_secret)
    if count_materials_in_project(principal.id, project_id) > 0:
        raise business_error("project_not_empty", "資料が残っている案件は削除できません。")
    if not delete_project(principal.id, project_id):
        raise business_error("object_not_found", "案件が見つかりません。")
    return {"ok": True}
