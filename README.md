# DrawRef（絵描き向け資料補助）

第5回 [Agentic AI Hackathon with Google Cloud](https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol5) 向けに作った Web アプリです。

**絵を生成するアプリではありません。** 写真資料を層と関節に分け、出典とライセンスの履歴を残し、手元資料を探しやすくする「机の横の資料係」です。

応募プロジェクト（Zenn）:  
https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol5/projects/4de1e0f4af6bcd

## いまの公開状態

ハッカソン審査終了後、**課金停止のため Cloud Run へのデプロイは止めています**（請求 unlink、サービス削除、保存データの空化）。  
本番 URL はありません。動かす場合は下のローカル手順を使ってください。再デプロイ手順は [docs/deploy/status.md](docs/deploy/status.md) を参照。

## 何ができるか

- ユーザー名とパスワードでアカウント作成（メール／ソーシャルログインなし）
- 写真1枚をアップロードし、物体の層を切り替え表示（元画像／マスク／骨格／筋肉／回転 3D）
- 人の輪郭・姿勢は MediaPipe。呼び方や出典探しはサーバー側の Gemini
- 題名や作者が分かるときだけ出典 URL を探し、ページに書いてある権利情報だけ履歴に残す（無ければ未確認）
- 手元資料庫（自作／他者）とチャット。データはアカウント（`owner_id`）単位で隔離
- 同じセッションで写真やポーズをやり直せる（前回の試しを消してから次を開始）

詳細な MVP と「やらないこと」は [docs/idea.md](docs/idea.md)。

## 技術構成（要約）

| 層 | 採用 |
|----|------|
| 画面 | Next.js（`apps/web`） |
| API | FastAPI（`apps/api`）。Gemini / Vision / Speech はここだけ |
| 実行（ハッカソン時） | Cloud Run（大阪 `asia-northeast2`） |
| 保存（任意） | Cloud Storage + Firestore |

設計の正本は [docs/architecture.md](docs/architecture.md)。

## ローカルで動かす

```bash
# 環境変数（.env.example をコピーして編集）
cp .env.example .env

# API（リポジトリ直下）
python -m venv apps/api/.venv
apps/api/.venv/Scripts/python -m pip install -r apps/api/requirements.txt
apps/api/.venv/Scripts/python -m uvicorn app.main:app --app-dir apps/api --port 8000

# 画面（別ターミナル）
cd apps/web
npm install
npm run dev
```

死活確認は `GET http://127.0.0.1:8000/health`。写真解析には `GEMINI_MODEL` と、本番なら ADC、ローカル試作なら API キーが必要です。キー名は [docs/deploy/env-contract.md](docs/deploy/env-contract.md)。**実値は `.env` のみ（Git 禁止）。**

依存の版は `apps/web/package.json` と `apps/api/requirements.txt` に固定。審査終了後に Next.js の 2026-10 / 2026-11 セキュリティ修正（`16.4.5`）などを取り込み済み。

## ドキュメント

| ファイル | 内容 |
|---------|------|
| [docs/idea.md](docs/idea.md) | 採用アイデア・MVP |
| [docs/architecture.md](docs/architecture.md) | クラウド設計 |
| [docs/demo-script.md](docs/demo-script.md) | デモ手順 |
| [docs/deploy/status.md](docs/deploy/status.md) | 公開識別子・ソフト終了後の状態 |
| [docs/google-cloud-japan-ai-hackathon-vol5-summary.md](docs/google-cloud-japan-ai-hackathon-vol5-summary.md) | 大会要約 |
| [docs/submission-draft.md](docs/submission-draft.md) | 提出文案 |

## ディレクトリ

- `apps/web` — 画面（Next.js）
- `apps/api` — 写真解析 API（FastAPI）
- `assets/` — アーキテクチャ図・デモ素材
- `docs/` — アイデア・設計・提出関連

## ライセンス

このリポジトリのソースは [LICENSE](LICENSE)（All Rights Reserved）。  
使う OSS の表記は画面の `/licenses` と [docs/legal/generated/third_party_notices.md](docs/legal/generated/third_party_notices.md)。
