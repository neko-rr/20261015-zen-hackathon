# 第5回 Agentic AI Hackathon with Google Cloud

ハッカソン用プロジェクト。提出締切は 2026-10-15 23:59。

## ドキュメント

| ファイル | 内容 |
|---------|------|
| [docs/google-cloud-japan-ai-hackathon-vol5-summary.md](docs/google-cloud-japan-ai-hackathon-vol5-summary.md) | 大会要約 |
| [docs/google-cloud-japan-ai-hackathon-vol5-regulation-summary.md](docs/google-cloud-japan-ai-hackathon-vol5-regulation-summary.md) | レギュレーション要約 |
| [docs/idea.md](docs/idea.md) | 採用アイデア |
| [docs/architecture.md](docs/architecture.md) | クラウド設計 |
| [docs/tasks.md](docs/tasks.md) | スケジュールと提出タスク |
| [docs/demo-script.md](docs/demo-script.md) | 審査用デモ確認 |

## セットアップ

```bash
# 環境変数（.env.example をコピーして編集）
cp .env.example .env

# API
python -m venv apps/api/.venv
apps/api/.venv/Scripts/python -m pip install -r apps/api/requirements.txt
apps/api/.venv/Scripts/python -m uvicorn app.main:app --app-dir apps/api --port 8000
```

死活確認は `GET http://127.0.0.1:8000/health`。写真解析には `GEMINI_MODEL` と、本番なら ADC、ローカル試作なら API キーが必要です。

依存の版は、公開から 3 日以上経った安定版に固定している。画面は Next.js 16.4.0、React 19.3.0、TypeScript 7.0.2。API は `apps/api/requirements.txt`。2026-10-14 公開の 16.4.1 と React 19.3.1 は未採用。自動更新は置かない。

OSS と外部サービスの表記は画面の `/licenses`。一覧の再生成は `python scripts/generate_third_party_notices.py`。提出後はデフォルトブランチを凍結するため、依存の自動更新（Renovate 等）は置かない。

このリポジトリのソースは [LICENSE](LICENSE)（All Rights Reserved）。使う OSS のライセンスは [docs/legal/generated/third_party_notices.md](docs/legal/generated/third_party_notices.md)。

## ディレクトリ

- `apps/web` — 画面（Next.js）
- `apps/api` — 写真解析 API（FastAPI）
- `assets/` — 画像・アーキテクチャ図・デモ素材
- `docs/ideas/` — アイデア候補
- `notes/` — 調査メモは非公開（`notes/README.md` のみ）
