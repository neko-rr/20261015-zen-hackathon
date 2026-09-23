"""環境変数を読む。値はログに出さない。"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

def _load_local_env() -> None:
    """ローカルは見つかった .env を読む。Cloud Run は環境変数だけ。"""
    here = Path(__file__).resolve()
    for parent in here.parents:
        env_file = parent / ".env"
        if env_file.is_file():
            load_dotenv(env_file)
            return
    load_dotenv()


_load_local_env()

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
# これ未満の枠と関節は画面に出さない
MIN_CONFIDENCE = 0.5


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str]
    gemini_model: str
    cloud_project: str
    use_enterprise: bool
    session_signing_secret: str
    session_cookie_secure: bool


def load_settings() -> Settings:
    raw_origins = os.getenv("CORS_ORIGINS", "http://127.0.0.1:3000")
    origins = [item.strip() for item in raw_origins.split(",") if item.strip()]
    local_origins = ["http://127.0.0.1:3000", "http://localhost:3000"]
    if any(item in local_origins for item in origins):
        for item in local_origins:
            if item not in origins:
                origins.append(item)
    secure_raw = os.getenv("SESSION_COOKIE_SECURE", "").strip().lower()
    return Settings(
        cors_origins=origins,
        gemini_model=os.getenv("GEMINI_MODEL", "").strip(),
        cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT", "").strip(),
        use_enterprise=os.getenv("GOOGLE_GENAI_USE_ENTERPRISE", "").strip().lower()
        == "true",
        session_signing_secret=os.getenv("SESSION_SIGNING_SECRET", "").strip(),
        session_cookie_secure=secure_raw == "true",
    )


def require_gemini(settings: Settings) -> None:
    from app.errors import business_error

    if not settings.gemini_model:
        raise business_error(
            "config_missing",
            "GEMINI_MODEL が未設定です。公式のモデル一覧から ID を選び、.env に書いてください。",
        )
    if settings.use_enterprise and not settings.cloud_project:
        raise business_error(
            "config_missing",
            "GOOGLE_CLOUD_PROJECT が未設定です。",
        )
