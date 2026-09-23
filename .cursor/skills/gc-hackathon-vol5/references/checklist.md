# チェック手順

検査対象はカレントリポジトリ。根拠はファイルパスで示す。

## レギュレーション適合

### 1. 実行プロダクト

次の痕跡を探す。App Engine / Compute Engine / GKE / Cloud Run / Cloud Run functions / Cloud TPU・GPU。

- `Dockerfile`, `app.yaml`, `cloudbuild.yaml`, `skaffold.yaml`
- Terraform の `google_cloud_run_*`, `google_container_cluster` など
- `gcloud run deploy` を含むスクリプトや CI

Firebase のとき: Cloud Functions for Firebase と Firebase App Hosting は満たす。Firebase Extension だけは満たさない。

デプロイ先が無い、またはローカルだけなら不足。コードから分からないときは、デプロイ URL の実行環境を参加者に確認する。

### 2. AI 技術

依存とコードから、Gemini Enterprise Agent Platform（旧 Vertex AI）/ Gemini API / Gemma / Nano Banana / ADK / Speech / Vision / Natural Language / Translation を探す。

パッケージ例: `google-cloud-aiplatform`, `google-genai`, `@google-cloud/vertexai`, `@google/genai`, `google-adk`。

Gemini API の AI Studio 直接利用、Firebase 経由の Gemini API は AI 条件を満たす。実行プロダクトは別に必要。

### 3. 報告

各必須条件について、根拠パスと充足を報告する。見つからなければ利用者に確認し、未使用と断定しない。

## 提出前チェック

1. GitHub 連携: ダッシュボードの審査向け情報で、連携が最大 5 リポジトリまでか参加者に確認する。公開・非公開は問わない。
2. 上記の適合チェックを実行する。
3. デプロイ URL を確認し、可能なら開いて応答を見る。
4. 提出物: 説明文、アーキテクチャ図、約 3 分の自作 YouTube 動画。記載は日本語。OSS を使うなら提出物にライセンスを書く。
5. 認証があるなら、テストアカウントとサンプルデータ。ソーシャルログインとメール受信必須は不可。
6. 期限は 2026-10-15 23:59。ダッシュボード: https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol5/dashboard

不足と対応を一覧で報告する。

提出物そのものの作り方（図・動画・ダッシュボード記入）は [../gc-hackathon-vol5-submit/SKILL.md](../gc-hackathon-vol5-submit/SKILL.md)。
