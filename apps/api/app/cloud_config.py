"""クラウド保存を使うかの判定。値はログに出さない。"""

from __future__ import annotations

import os


def gcs_bucket() -> str:
    return os.getenv("GCS_BUCKET", "").strip()


def gcp_project() -> str:
    return os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()


def cloud_persistence_enabled() -> bool:
    """GCS_BUCKET があるとき、実体は Cloud Storage、メタデータは Firestore。"""
    return bool(gcs_bucket())
