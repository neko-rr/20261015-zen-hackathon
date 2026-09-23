# AGENTS.md

> ハッカソン開発用の AI エージェント指示書。チーム全員で共有・更新する。

## プロジェクト概要

- **大会**: 第5回 Agentic AI Hackathon with Google Cloud
- **チーム**: {TODO: 個人かチームか、役割}
- **期間**: エントリー 2026-08-20 〜 提出 2026-10-15 23:59。固定の開発時間はない
- **目的**: 絵描き向けに、写真を層と関節に分け、出典とライセンスの履歴を残す。正本は [docs/idea.md](docs/idea.md)
- **詳細**: [docs/google-cloud-japan-ai-hackathon-vol5-summary.md](docs/google-cloud-japan-ai-hackathon-vol5-summary.md)

## 本戦の前提（ミニハッカソン終了後）

- ミニハッカソンの当日制限（14:30 発表・同日の short / panic）は使わない
- 意識する締切は **2026-10-15 23:59** のみ。提出後〜2026-12-01 はデフォルトブランチを提出時点のままにする
- ファイル検索は `.cursorignore` に従い、`node_modules` / `.venv` / `.next` などを対象にしない（詳細は `.cursor/rules/agent-efficiency.mdc`）

## コア価値（MVP）

- 写真1枚 → 物体の層と関節 → 選んだ物体の出典 URL
- 表示は元画像／マスク／骨格／筋肉／回転 3D（人の輪郭と姿勢は MediaPipe。Gemini は出典）
- ライセンス・時期・著作権は本文にあるものだけ。無ければ未確認
- 絵は生成しない
- 「はじめる」で署名セッション開始。データは `owner_id` 単位で隔離（ユーザー間共有しない）
- デモに不要な機能（筋肉の医学シミュレーション、Kindle、画面の装飾の作り込みなど）は足さない

## ハッカソン制約

正本 → [docs/google-cloud-japan-ai-hackathon-vol5-regulation-summary.md](docs/google-cloud-japan-ai-hackathon-vol5-regulation-summary.md)

- 実行に Google Cloud のプロダクトを1つ以上使う（App Engine / Compute Engine / GKE / Cloud Run / Cloud Run functions / Cloud TPU・GPU）
- Google Cloud の AI を1つ以上使う（Gemini Enterprise Agent Platform、Gemini API、Gemma、Nano Banana、ADK、Speech / Vision / Natural Language / Translation）
- Google Cloud にデプロイする。ローカルだけでは提出条件を満たさない
- 提出期限: **2026-10-15 23:59**
- 提出物: GitHub 連携（公開・非公開どちらでも可）、デプロイ URL、説明文、アーキテクチャ図、YouTube のデモ動画（約3分）
- Zenn 記事は任意。書くならカテゴリは Idea
- 認証が必要ならテストアカウントとサンプルデータ。ソーシャルログインと、メール受信が必須のログインは避ける
- 提出後から 2026-12-01 まで、連携リポジトリのデフォルトブランチは提出時点のまま。続きは別ブランチ
- 大会開始前から進捗していたプロジェクトは出さない
- 第4回以前のルール（公開リポジトリ必須、Zenn 記事必須）を適用しない
- 提出審査はリモート。最終ピッチは 2026-12-01（時間は未確認）。スライドや Google Drive 提出は必須ではない
- 説明・図・動画は日本語。OSS を使うなら提出物にライセンスを書く。使えるツールは自分に権利があるものだけ（参加規約。出典は主催者スキル）
- ルール判断は公式ページが正。主催者スキルの古い日程（オフィスアワー 9/29、Summit 日程）は使わない

## チーム運用

- **意思決定**: {TODO}
- **共有**: 候補は `docs/ideas/`、採用後は `docs/idea.md`、進捗は `docs/tasks.md`
- **Git**: {TODO}
- **非公開メモ**: 競合調査・作業ログはリポジトリ外の `20261015-zen-hackathon-private`（Git に入れない）

## ディレクトリ構成

`src/` は無い。画面は `apps/web`、API は `apps/api`。

| パス | 用途 |
|------|------|
| `apps/web` | 画面。Next.js。ポート 3000 |
| `apps/api` | API。FastAPI。ポート 8000。Gemini はここだけ |
| `docs/` | 要約・idea・tasks・demo-script・`deploy/` |
| `assets/` | アーキテクチャ図・デモ素材 |
| `notes/README.md` | 調査メモは非公開フォルダへ。ここは案内のみ |
| `.cursor/rules/` | 秘密・命名・API・デプロイの命令 |
| `.env` | 秘匿情報（Git 管理外） |

読む順: `security` → `docs/idea.md` → `docs/deploy/env-contract.md`。デプロイ時だけ `deploy.mdc`。

## エージェント Skills（目次）

詳細は [`.cursor/skills/README.md`](.cursor/skills/README.md)。AWS / Bedrock 用 skill は置かない。

| 用途 | Skill |
|------|--------|
| 大会ルール・適合・提出前 | `gc-hackathon-vol5` |
| 提出物の作り方（図・動画・ダッシュボード） | `gc-hackathon-vol5-submit` |
| 第5回アイデア壁打ち | `gc-hackathon-vol5-ideation` |
| Cloud Run / Gemini / GCS / Firestore / デプロイ | `cloud-run-gemini` |
| コスト・実用性の実装提案（料金は Web 検索必須） | `cost-practical-proposals` |
| AWS 名で GCP を理解する | `gcp-for-aws-users` |
| テスト（pytest・/health・next build） | `mvp-test` |
| 実装後の docs 同期（他セッション向け） | `impl-docs-sync` |
| Jev（検める・確かめる） | `typesafe-jev` |
| DESIGN.md | `hackathon-design-md` |
| タスク分解・進捗 | `hackathon-tasks-plan` / `hackathon-tasks-sync`（short/panic は明示時のみ） |

## 技術スタック

実行プロダクトと AI は決定。詳細は [docs/architecture.md](docs/architecture.md)。

| 項目 | 採用 | 備考 |
|------|------|------|
| 言語 | TypeScript と Python | 画面と API |
| フレームワーク | Next.js と FastAPI | 画面は 3000、API は 8000 |
| 実行プロダクト | Cloud Run | プロジェクト `illustration-support`（番号 203853466674） |
| AI | Gemini Enterprise Agent Platform + grounding | ブラウザから呼ばない |
| 保存 | Cloud Storage と Firestore | バケット名などは [docs/deploy/status.md](docs/deploy/status.md) |
| デプロイ | Cloud Run | 設計は [docs/architecture.md](docs/architecture.md) |

## コマンド

```bash
# 初回
cp .env.example .env

# API（リポジトリ直下で）
python -m venv apps/api/.venv
apps/api/.venv/Scripts/python -m pip install -r apps/api/requirements.txt
apps/api/.venv/Scripts/python -m uvicorn app.main:app --app-dir apps/api --port 8000

# 画面（別ターミナル。API は 8000）
cd apps/web
npm install
npm run dev
```

## 開発方針

- MVP は、デプロイ URL と約3分の動画で通る1本の流れに絞る
- 審査軸は、課題の新規性、自律性（制御・可観測性・セキュリティ）、実装品質
- デモに不要な機能は足さない
- 外部 API は try-catch とタイムアウトを付ける
- API キーはコードとログに出さない

## AI エージェント向け指示

### やること

- 変更前に `docs/idea.md` の MVP を確認する
- 適合チェックと提出前チェックは `.cursor/skills/gc-hackathon-vol5/references/checklist.md`
- 提出物の作り方は `.cursor/skills/gc-hackathon-vol5-submit/SKILL.md`
- テスト方針は `.cursor/skills/mvp-test/SKILL.md`
- 機能・API 実装が終わったら `.cursor/skills/impl-docs-sync/SKILL.md`（計画ファイルだけでは他セッションに伝わらない）
- デプロイ・Cloud 操作は `.cursor/skills/cloud-run-gemini/SKILL.md`
- コスト・実用性の実装提案は `.cursor/skills/cost-practical-proposals/SKILL.md`（料金は必ず Web 検索）
- AWS 用語での質問は `.cursor/skills/gcp-for-aws-users/SKILL.md`（実装は GCP のまま）
- 必須プロダクト（実行基盤と AI）を外さない
- デモ経路が動くことを優先する
- コア（層・関節・出典）の精度と見せ方を優先する

### やらないこと

- `.env` の値をコード、ログ、`docs/` に書く
- `cursor.md` や `notes/` の調査メモを Git に戻す
- 提出後にデフォルトブランチを直接更新する
- 過去大会の提出形式に合わせた作りにする
- デモに不要な大規模リファクタ
- AWS / Bedrock / Lambda をこのプロジェクトの実行先や AI に採用する

### 判断に迷ったら

1. リモートの審査員が URL と3分動画で理解できるか
2. 2026-10-15 までにデプロイできるか
3. 必須の Google Cloud 条件を満たすか

## ドキュメント

| ファイル | 更新タイミング |
|---------|---------------|
| [docs/idea.md](docs/idea.md) | アイデア確定後。MVP に載る体験を実装したとき |
| [docs/architecture.md](docs/architecture.md) | クラウド構成・API・データ境界を変えたとき |
| [docs/deploy/status.md](docs/deploy/status.md) | 公開してよい識別子が変わったとき |
| [docs/tasks.md](docs/tasks.md) | 進捗が変わったとき |
| [docs/demo-script.md](docs/demo-script.md) | デモ手順が決まった・変わったとき |
| [docs/deploy/env-contract.md](docs/deploy/env-contract.md) | 環境変数のキーを足したとき |

実装完了時の同期手順 → [`.cursor/skills/impl-docs-sync/SKILL.md`](.cursor/skills/impl-docs-sync/SKILL.md)

## 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-09-18 | 初版。スタックとチームは未記入 |
| 2026-09-19 | 主催者スキルから日本語記載、OSS ライセンス、チェック手順を追加 |
| 2026-09-19 | 目的と AI・実行プロダクトを採用案に合わせた |
| 2026-09-19 | Google Cloud 設計を docs/architecture.md に追加 |
| 2026-09-19 | 別アプリから、秘密の境界・API 形・Cloud Run 用 env 契約だけを追加。製品コードは未取込 |
| 2026-09-19 | 画面は `apps/web`、API は `apps/api`。`src/` は削除 |
| 2026-09-20 | 公開リポジトリ向けに作業ログ・競合メモを非公開フォルダへ退避 |
| 2026-09-20 | ミニハッカソン制限を解除。締切は 10/15 のみ。`.cursorignore` で検索を高速化 |
| 2026-09-20 | `hackathon-bedrock` 削除。`cloud-run-gemini` と `gcp-for-aws-users`、skills 目次を追加 |
| 2026-09-20 | `mvp-test` と `gc-hackathon-vol5-submit`（テスト方針・提出物の作り方）を追加 |
| 2026-09-20 | `cost-practical-proposals`（費用対効果・実用性。料金は Web 検索必須）を追加 |
| 2026-09-21 | `impl-docs-sync`（実装後に docs を他セッション向け同期。依頼なしデプロイ禁止）を追加 |
