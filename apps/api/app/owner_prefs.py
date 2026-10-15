"""利用者ごとの設定。出典の再検索までの日数、言語、テーマ色。"""

from __future__ import annotations

from threading import Lock

from app.cloud_config import cloud_persistence_enabled
from app.errors import business_error

DEFAULT_CITATION_REFRESH_DAYS = 30
DEFAULT_LOCALE = "ja"
DEFAULT_THEME_ID = "default"
_MIN_DAYS = 1
_MAX_DAYS = 365
_LOCALES = {"ja", "en"}
_THEME_IDS = {
    "default",
    "lime-right",
    "lime-dark",
    "emerald-dark",
    "sky-dark",
    "blue-dark",
    "pink-dark",
    "purple-dark",
    "orange-dark",
    "red-dark",
    "yellow-dark",
}

_lock = Lock()
_days: dict[str, int] = {}
_locales: dict[str, str] = {}
_themes: dict[str, str] = {}


def citation_refresh_days(owner_id: str) -> int:
    if not owner_id.strip():
        return DEFAULT_CITATION_REFRESH_DAYS
    if cloud_persistence_enabled():
        from app.record_store import load_citation_refresh_days

        stored = load_citation_refresh_days(owner_id)
        return stored if stored is not None else DEFAULT_CITATION_REFRESH_DAYS
    with _lock:
        return _days.get(owner_id, DEFAULT_CITATION_REFRESH_DAYS)


def set_citation_refresh_days(owner_id: str, days: int) -> int:
    if not owner_id.strip():
        raise business_error("session_required", "先にログインしてください。")
    if isinstance(days, bool) or not isinstance(days, int):
        raise business_error("invalid_refresh", "再検索までの日数は 1 から 365 の整数です。")
    if days < _MIN_DAYS or days > _MAX_DAYS:
        raise business_error("invalid_refresh", "再検索までの日数は 1 から 365 です。")
    if cloud_persistence_enabled():
        from app.record_store import save_citation_refresh_days

        save_citation_refresh_days(owner_id, days)
        return days
    with _lock:
        _days[owner_id] = days
    return days


def account_locale(owner_id: str) -> str:
    if not owner_id.strip():
        return DEFAULT_LOCALE
    if cloud_persistence_enabled():
        from app.record_store import load_preference_text

        stored = load_preference_text(owner_id, "locale")
        return stored if stored in _LOCALES else DEFAULT_LOCALE
    with _lock:
        return _locales.get(owner_id, DEFAULT_LOCALE)


def account_theme_id(owner_id: str) -> str:
    if not owner_id.strip():
        return DEFAULT_THEME_ID
    if cloud_persistence_enabled():
        from app.record_store import load_preference_text

        stored = load_preference_text(owner_id, "theme_id")
        return stored if stored in _THEME_IDS else DEFAULT_THEME_ID
    with _lock:
        return _themes.get(owner_id, DEFAULT_THEME_ID)


def account_preferences(owner_id: str) -> dict[str, str | int]:
    return {
        "citation_refresh_days": citation_refresh_days(owner_id),
        "locale": account_locale(owner_id),
        "theme_id": account_theme_id(owner_id),
    }


def update_preferences(
    owner_id: str,
    *,
    citation_refresh_days: int | None = None,
    locale: str | None = None,
    theme_id: str | None = None,
) -> dict[str, str | int]:
    if citation_refresh_days is None and locale is None and theme_id is None:
        raise business_error("invalid_preference", "変更する設定がありません。")
    if citation_refresh_days is not None:
        set_citation_refresh_days(owner_id, citation_refresh_days)
    if locale is not None:
        _set_locale(owner_id, locale)
    if theme_id is not None:
        _set_theme_id(owner_id, theme_id)
    return account_preferences(owner_id)


def _set_locale(owner_id: str, locale: str) -> None:
    if not owner_id.strip():
        raise business_error("session_required", "先にログインしてください。")
    if locale not in _LOCALES:
        raise business_error("invalid_preference", "言語は日本語か英語です。")
    if cloud_persistence_enabled():
        from app.record_store import save_preference_text

        save_preference_text(owner_id, "locale", locale)
        return
    with _lock:
        _locales[owner_id] = locale


def _set_theme_id(owner_id: str, theme_id: str) -> None:
    if not owner_id.strip():
        raise business_error("session_required", "先にログインしてください。")
    if theme_id not in _THEME_IDS:
        raise business_error("invalid_preference", "そのテーマ色は選べません。")
    if cloud_persistence_enabled():
        from app.record_store import save_preference_text

        save_preference_text(owner_id, "theme_id", theme_id)
        return
    with _lock:
        _themes[owner_id] = theme_id
