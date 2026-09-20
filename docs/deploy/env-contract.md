# 環境変数コントラクト

このファイルに実値を書かない。例はリポジトリ直下の `.env.example`。ローカルの実体は `.env`（Git 禁止）。

| 印 | 意味 |
|----|------|
| 必須 | その機能を動かすとき必要 |
| 任意 | 無くてもデモの骨は動く |
| 公開可 | ブラウザに載ってよい |
| 秘密 | ローカルか Cloud Run だけ |

## ホスト

| ホスト | 置く | 置かない |
|--------|------|----------|
| ローカル | `.env` | Git |
| ブラウザ | `NEXT_PUBLIC_API_BASE_URL` のみ | Gemini のキー、ADC |
| Cloud Run | サーバー用の環境変数。可能なら ADC（サービスアカウント） | リポジトリへの実値 |

## キー

| キー | 区分 | 公開 | 備考 |
|------|------|------|------|
| `NEXT_PUBLIC_API_BASE_URL` | 画面があるとき必須 | 公開可 | 末尾スラッシュなし。ローカルは `http://127.0.0.1:8000` |
| `CORS_ORIGINS` | 本番必須 | 秘密ではない | 本番は公開 Web のオリジンだけ。localhost を残さない |
| `GOOGLE_CLOUD_PROJECT` | Gemini を GCP 経由で使うとき必須 | 秘密ではない | `illustration-support` |
| `GOOGLE_CLOUD_LOCATION` | 同上 | 秘密ではない | 例: `global` |
| `GOOGLE_GENAI_USE_ENTERPRISE` | 同上 | 秘密ではない | `True` で Agent Platform 側 |
| `GOOGLE_API_KEY` | ローカル試作のみ任意 | 秘密 | 本番の既定は ADC。Git 禁止 |
| `GCS_BUCKET` | 写真を保存するとき必須 | 秘密ではない | `illustration-support-photos`。大阪 `asia-northeast2`。中身の URL は書かない |
| `TYPESAFE_API_KEY` | 検める・確かめるとき必須 | 秘密 | 未設定ならその段は飛ばす。枠は Gemini の確信度のまま。権利は `unknown` |

Gemini の呼び出しはサーバーだけ。公式: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/sdks/overview

## この大会で使うプロジェクト

| 項目 | 値 |
|------|-----|
| プロジェクト ID | `illustration-support` |
| プロジェクト番号 | `203853466674` |

番号は請求やサポート画面用。コマンドと環境変数には ID を使う。API キーではない。作成済みバケットと、まだ無いサービスは [status.md](status.md)。

## Git に載せてよいもの

- `.env.example`（空またはダミー）
- このファイルのキー名

## 載せていけないもの

- `.env`
- API キー、ADC の JSON、サービスアカウント鍵
- Cookie、Bearer、署名 URL の全文
