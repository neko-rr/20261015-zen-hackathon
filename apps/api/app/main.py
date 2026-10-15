"""絵描き資料 API。Gemini はここからだけ呼ぶ。"""

import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, File, Form, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.accounts import authenticate, register_account, seed_reviewer, suggest_username, username_for_owner
from app.analyze import analyze_image, apply_names
from app.auth import (
    attach_session_cookie,
    clear_session_cookie,
    principal_from_request,
    require_account,
    require_signing_secret,
)
from app.errors import business_error, register_error_handlers, unauthorized_error
from app.file_facts import read_file_facts
from app.label import name_subjects
from app.lookup import answer_question, cite_material, lookup_object
from app.web_detect import detect_web
from app.materials import (
    delete_material,
    list_owner_materials,
    list_owner_tags,
    patch_material,
    register_material,
    read_material,
)
from app.material_store import count_materials_in_project
from app.owner_prefs import account_preferences, update_preferences
from app.project_store import (
    create_project,
    delete_project,
    list_projects,
    note_library_call,
    note_photo,
    save_memo,
)
from app.photo_prepare import prepare_photo
from app.settings import load_settings, require_gemini
from app.speech import transcribe_pose
from app.spoken_pose import instruct_pose
from app.store import add_lookup, add_question, create_photo, finish_labels, get_photo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = load_settings()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    try:
        seed_reviewer()
    except Exception:
        logger.exception("reviewer seed failed")
    _warm_vision()
    yield


def _warm_vision() -> None:
    """姿勢・手・輪郭を起動時に読む。ログインの応答は待たせない。"""
    if os.getenv("VISION_WARM", "1").strip() == "0":
        logger.info("vision warm skipped")
        return
    threading.Thread(target=_warm_vision_now, name="vision-warm", daemon=True).start()


def _warm_vision_now() -> None:
    try:
        from app.hands import warm as warm_hands
        from app.pose import warm as warm_pose
        from app.segment import warm as warm_segment

        warm_pose()
        warm_hands()
        warm_segment()
        logger.info("vision models warmed")
    except Exception:
        logger.exception("vision warm failed")


app = FastAPI(title="draw-reference-api", lifespan=_lifespan)
try:
    seed_reviewer()
except Exception:
    logger.exception("reviewer seed failed")
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
    query: str = Field(default="", max_length=80)


class PreferencePatch(BaseModel):
    citation_refresh_days: int | None = None
    locale: str | None = None
    theme_id: str | None = None


class MaterialCiteRequest(BaseModel):
    query: str = Field(default="", max_length=80)
    project_id: str = ""


class ProjectLibraryCall(BaseModel):
    doc_id: str


class ProjectMemoPatch(BaseModel):
    memo: str = Field(default="", max_length=20000)


class QuestionRequest(BaseModel):
    object_id: str
    message: str
    tags: list[str] = []
    project_id: str = ""


class SpokenPoseRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class ProjectCreate(BaseModel):
    name: str


class AccountRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=200)


class MaterialPatch(BaseModel):
    tags: list[str] | None = None
    project_id: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sessions")
def create_or_resume_session(request: Request, response: Response) -> dict:
    """ログイン済みの Cookie を継続する。ゲストの新規 ID は発行しない。"""
    require_signing_secret(settings.session_signing_secret)
    existing = principal_from_request(request, settings.session_signing_secret)
    if existing is None or existing.kind != "account":
        raise unauthorized_error(
            "session_required",
            "ログインがありません。アカウントで入ってください。",
        )
    attach_session_cookie(
        response,
        existing.id,
        settings.session_signing_secret,
        secure=settings.session_cookie_secure,
        kind="account",
    )
    return {
        "session_id": existing.id,
        "kind": "account",
        "username": username_for_owner(existing.id),
    }


def _open_account(response: Response, owner_id: str, username: str) -> dict:
    attach_session_cookie(
        response,
        owner_id,
        settings.session_signing_secret,
        secure=settings.session_cookie_secure,
        kind="account",
    )
    return {"session_id": owner_id, "kind": "account", "username": username}


@app.post("/accounts/suggestions")
def suggest_account_name() -> dict:
    return {"username": suggest_username()}


@app.post("/accounts")
def create_account(body: AccountRequest, response: Response) -> dict:
    require_signing_secret(settings.session_signing_secret)
    account = register_account(body.username, body.password)
    logger.info("account_created")
    return _open_account(response, account.owner_id, account.username)


@app.post("/accounts/logout")
def logout_account(response: Response) -> dict:
    clear_session_cookie(response, secure=settings.session_cookie_secure)
    return {"ok": True}


@app.post("/accounts/login")
def login_account(body: AccountRequest, response: Response) -> dict:
    require_signing_secret(settings.session_signing_secret)
    account = authenticate(body.username, body.password)
    if account is None:
        raise unauthorized_error("invalid_login", "ユーザー名かパスワードが違います。")
    logger.info("account_login")
    return _open_account(response, account.owner_id, account.username)


@app.get("/sessions/me")
def current_session(request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    username = ""
    if principal.kind == "account":
        username = username_for_owner(principal.id)
    return {"session_id": principal.id, "kind": principal.kind, "username": username}


@app.post("/photos")
async def create_photo_analysis(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = Form(""),
) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    mime_type = (file.content_type or "").split(";")[0].strip().lower()
    image = await file.read()
    image, mime_type = prepare_photo(image, mime_type)

    analysis = analyze_image(settings, image, mime_type)
    objects = analysis["objects"]
    pose = analysis.get("pose") or {"landmarks": [], "edges": [], "muscles": []}
    labels_pending = bool(settings.gemini_model)
    file_facts = read_file_facts(image)
    web = detect_web(image)
    web_pages = web["pages"]
    web_images = web["images"]
    photo_id = create_photo(
        objects,
        principal.id,
        pose=pose,
        labels_pending=labels_pending,
        file_facts=file_facts,
        web_pages=web_pages,
        web_images=web_images,
        image=image,
        content_type=mime_type,
    )
    if labels_pending:
        background.add_task(_attach_labels, photo_id, principal.id, image, mime_type)
    if project_id.strip():
        note_photo(principal.id, project_id.strip(), photo_id)
    logger.info(
        "decide photo_id=%s object_count=%s pose_landmarks=%s labels_pending=%s",
        photo_id,
        len(objects),
        len(pose.get("landmarks") or []),
        labels_pending,
    )
    return {
        "photo_id": photo_id,
        "objects": objects,
        "pose": pose,
        "labels_pending": labels_pending,
        "file_facts": file_facts,
        "web_pages": web_pages,
        "web_images": web_images,
    }


@app.get("/photos/{photo_id}")
def read_photo(photo_id: str, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    if not photo_id.strip():
        raise business_error("object_not_found", "写真が見つかりません。")
    photo = get_photo(photo_id, principal.id)
    if photo is None:
        raise business_error("object_not_found", "写真が見つかりません。")
    return {
        "photo_id": photo_id,
        "objects": photo["objects"],
        "pose": photo["pose"],
        "labels_pending": photo["labels_pending"],
        "file_facts": photo.get("file_facts") or {},
        "web_pages": photo.get("web_pages") or [],
        "web_images": photo.get("web_images") or [],
    }


def _attach_labels(photo_id: str, owner_id: str, image: bytes, mime_type: str) -> None:
    """人形を返したあとで呼び方だけ足す。失敗しても姿勢は残す。"""
    try:
        named = name_subjects(settings, image, mime_type)
        photo = get_photo(photo_id, owner_id)
        if photo is None:
            return
        finish_labels(photo_id, owner_id, apply_names(list(photo["objects"]), named))
        logger.info("label attached photo_id=%s", photo_id)
    except Exception:
        logger.exception("label attach failed photo_id=%s", photo_id)
        photo = get_photo(photo_id, owner_id)
        if photo is not None:
            finish_labels(photo_id, owner_id, list(photo["objects"]))


@app.post("/photos/{photo_id}/lookups")
def create_lookup(photo_id: str, body: LookupRequest, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
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
        public_name=str(target.get("public_name") or ""),
        work_title=str(target.get("work_title") or ""),
        query=body.query,
    )
    lookup = {
        "object_id": body.object_id,
        "web_images": list(photo.get("web_images") or []),
        **result,
    }
    if not add_lookup(photo_id, principal.id, lookup):
        raise business_error("object_not_found", "写真が見つかりません。")
    return lookup


@app.get("/photos/{photo_id}/lookups")
def list_lookups(photo_id: str, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    if not photo_id.strip():
        raise business_error("object_not_found", "写真が見つかりません。")
    photo = get_photo(photo_id, principal.id)
    if photo is None:
        raise business_error("object_not_found", "写真が見つかりません。")
    return {"lookups": photo["lookups"]}


@app.post("/poses")
def create_spoken_pose(body: SpokenPoseRequest, request: Request) -> dict:
    require_account(request, settings.session_signing_secret)
    return instruct_pose(body.message, settings)


@app.post("/poses/speech")
async def create_pose_speech(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("ja"),
) -> dict:
    """マイクの短い録音を、ポーズ用の言葉にする。関節は作らない。"""
    require_account(request, settings.session_signing_secret)
    audio = await file.read()
    text = transcribe_pose(audio, language)
    if not text:
        raise business_error("speech_empty", "言葉を聞き取れませんでした。もう一度話すか、入力してください。")
    logger.info("speech chars=%s language=%s", len(text), language)
    return {"text": text}


@app.post("/photos/{photo_id}/questions")
def create_question(photo_id: str, body: QuestionRequest, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
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
        history=list(photo.get("questions") or []),
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
    principal = require_account(request, settings.session_signing_secret)
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
    principal = require_account(request, settings.session_signing_secret)
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


@app.get("/preferences")
def get_preferences(request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    return account_preferences(principal.id)


@app.patch("/preferences")
def patch_preferences(body: PreferencePatch, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    return update_preferences(
        principal.id,
        citation_refresh_days=body.citation_refresh_days,
        locale=body.locale,
        theme_id=body.theme_id,
    )


@app.get("/materials")
def get_materials(request: Request, project_id: str = "") -> dict:
    principal = require_account(request, settings.session_signing_secret)
    return {
        "materials": list_owner_materials(principal.id, project_id=project_id),
        "tags": list_owner_tags(principal.id),
    }


@app.get("/materials/{doc_id}")
def get_material_route(doc_id: str, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    return {"material": read_material(principal.id, doc_id)}


@app.post("/materials/{doc_id}/lookups")
def cite_material_route(doc_id: str, body: MaterialCiteRequest, request: Request) -> dict:
    """資料庫の1件について、題名か作者だけを外へ出す。"""
    principal = require_account(request, settings.session_signing_secret)
    require_gemini(settings)
    return cite_material(
        settings,
        principal.id,
        doc_id,
        query=body.query,
        project_id=body.project_id,
    )


@app.patch("/materials/{doc_id}")
def patch_material_route(doc_id: str, body: MaterialPatch, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    item = patch_material(
        principal.id,
        doc_id,
        tags=body.tags,
        project_id=body.project_id,
    )
    return {"material": item}


@app.delete("/materials/{doc_id}")
def remove_material_route(doc_id: str, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    delete_material(principal.id, doc_id)
    return {"ok": True}


@app.get("/projects")
def get_projects(request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    return {"projects": list_projects(principal.id)}


@app.post("/projects")
def post_project(body: ProjectCreate, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    name = body.name.strip()
    if not name:
        raise business_error("invalid_project", "案件名を入力してください。")
    return {"project": create_project(principal.id, name)}


@app.post("/projects/{project_id}/library-calls")
def post_project_library_call(
    project_id: str,
    body: ProjectLibraryCall,
    request: Request,
) -> dict:
    """手で開いた資料を、その作業の記録に残す。"""
    principal = require_account(request, settings.session_signing_secret)
    item = read_material(principal.id, body.doc_id)
    recorded = note_library_call(
        principal.id,
        project_id,
        body.doc_id,
        str(item.get("title") or ""),
        "open",
    )
    if recorded is None:
        raise business_error("object_not_found", "案件が見つかりません。")
    return {"project": recorded}


@app.patch("/projects/{project_id}")
def patch_project(project_id: str, body: ProjectMemoPatch, request: Request) -> dict:
    """作業の自由メモを残す。本文はマークダウンのまま。"""
    principal = require_account(request, settings.session_signing_secret)
    recorded = save_memo(principal.id, project_id, body.memo)
    if recorded is None:
        raise business_error("object_not_found", "案件が見つかりません。")
    return {"project": recorded}


@app.delete("/projects/{project_id}")
def remove_project(project_id: str, request: Request) -> dict:
    principal = require_account(request, settings.session_signing_secret)
    if count_materials_in_project(principal.id, project_id) > 0:
        raise business_error("project_not_empty", "資料が残っている案件は削除できません。")
    if not delete_project(principal.id, project_id):
        raise business_error("object_not_found", "案件が見つかりません。")
    return {"ok": True}
