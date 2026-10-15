import os

# app.main の import より先に秘密を置く（.env の空文字より優先）
os.environ["SESSION_SIGNING_SECRET"] = "test-session-signing-secret-not-for-production"
os.environ["SESSION_COOKIE_SECURE"] = "false"
os.environ["VISION_WARM"] = "0"
# テストはクラウドへ書かない。.env の GCS_BUCKET より先に空にする
os.environ["GCS_BUCKET"] = ""
# 意味検索の実呼び出しもしない。.env で RAG_ENABLED=true でもテストは単語検索のまま
os.environ["RAG_ENABLED"] = ""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
