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

## まだ無いもの（構成上）

- 画面の Cloud Run（`apps/web` に Dockerfile が無い場合）
- Firestore のデータベース
