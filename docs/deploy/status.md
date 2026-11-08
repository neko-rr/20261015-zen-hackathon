# クラウド設定（公開用）

秘密（API キー、ADC の中身、ログインメール、請求の詳細）は書かない。  
運用上の細かい現状メモはリポジトリ外の非公開フォルダに退避済み。

## 公開してよい識別子

| 項目 | 値 |
|------|-----|
| プロジェクト ID | `illustration-support` |
| プロジェクト番号 | `203853466674`（API キーではない） |
| Gemini の場所 | `global`（`GOOGLE_CLOUD_LOCATION`） |
| 写真バケット | `illustration-support-photos` |
| バケットの場所 | `asia-northeast2` |
| バケットの公開 | 禁止（public access prevention） |
| API サービス名 | `illustration-api` |
| 実行サービスアカウント | `run-runtime@illustration-support.iam.gserviceaccount.com` |

環境変数のキー名は [env-contract.md](env-contract.md)。`GCS_BUCKET` はバケット名だけ。

## デプロイ URL

本番の URL は提出フォームとデモ動画に書く。リポジトリには固定しない（変更・ローテーションしやすくするため）。

死活はデプロイ後に `GET {APIのURL}/health` で確認する。

## Firestore

| 項目 | 値 |
|------|-----|
| データベース | `(default)` |
| 場所 | `asia-northeast2` |
| モード | Native |

クライアント SDK からは読まない。API のサービスアカウント（ADC）だけが書く。メタデータの書き込みは確認済み。

## 請求・運用状態（審査終了後）

ハッカソン審査終了後、課金停止のためソフト終了済み（プロジェクト自体は残す）。

| 項目 | 状態 |
|------|------|
| 請求 | プロジェクトから unlink（`billingEnabled: false`） |
| Cloud Run | `illustration-api` / `illustration-web` を削除済み |
| GCS | バケットは残し、オブジェクトは空 |
| Artifact Registry | `cloud-run-source-deploy`（asia-northeast2）を削除済み |
| Firestore | データベース定義は残存（課金 unlink により利用停止） |

再デプロイ: 請求を再リンク → `scripts/deploy.ps1` または GitHub Actions の deploy。  
`main` への push は deploy ワークフローを起動するが、請求 unlink 中はデプロイ失敗が想定どおり。

## 有効な API と実行アカウント

実行アカウント `run-runtime` は `roles/aiplatform.user`、`roles/datastore.user`、バケットの `roles/storage.objectAdmin`、`roles/serviceusage.serviceUsageConsumer` を持つ。有効な API には Vertex AI、Cloud Vision、Cloud Speech-to-Text、Firestore、Cloud Storage、Cloud Run が含まれる。再デプロイ時に API サービスへ `RAG_ENABLED` や鍵系（`GOOGLE_API_KEY` / `GEMINI_API_KEY` / `TYPESAFE_API_KEY`）を再設定する（値は書かない）。

## 画面

ソフト終了後、Cloud Run 上の `illustration-web` は無し。ローカルまたは再デプロイ後に確認する。ログイン前の HTML は確認中の文言だけで止めず、ログインフォームを出す。
