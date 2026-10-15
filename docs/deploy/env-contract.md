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
| `NEXT_PUBLIC_API_BASE_URL` | 画面があるとき必須 | 公開可 | 末尾スラッシュなし。ローカルは `http://127.0.0.1:8000`。本番イメージは `/drawref-api`（画面と同じオリジン） |
| `API_BASE_URL` | 本番の画面で必須 | 秘密ではない | Next が `/drawref-api` を転送する API の URL。ブラウザのコードには入れない |
| `CORS_ORIGINS` | 本番必須 | 秘密ではない | 本番は公開 Web のオリジンだけ。localhost を残さない |
| `GOOGLE_CLOUD_PROJECT` | Gemini を GCP 経由で使うとき必須 | 秘密ではない | `illustration-support` |
| `GOOGLE_CLOUD_LOCATION` | 同上 | 秘密ではない | 例: `global` |
| `GOOGLE_GENAI_USE_ENTERPRISE` | 同上 | 秘密ではない | `True` で Agent Platform 側 |
| `GEMINI_MODEL` | 出典検索・呼び方で必須 | 秘密ではない | モデル ID。公式一覧から選ぶ。リポジトリには書かない。Cloud Run の API サービスに置く |
| `GOOGLE_API_KEY` | 意味検索を使うとき必須。ローカル試作でも可 | 秘密 | Gemini Developer API のキー。File Search はこれか `GEMINI_API_KEY`。ADC ではストアを作れない。Git 禁止。Cloud Vision と Speech-to-Text の本番は ADC のまま |
| `GCS_BUCKET` | 写真・資料をクラウド保存するとき必須 | 秘密ではない | `illustration-support-photos`。設定時は実体をこのバケット、メタデータを同じプロジェクトの Firestore `(default)` へ書く。未設定時はプロセス内と API ローカル `.data` |
| `TYPESAFE_API_KEY` | 検める・確かめるとき必須 | 秘密 | 未設定ならその段は飛ばす。枠は Gemini の確信度のまま。権利は `unknown` |
| `SESSION_SIGNING_SECRET` | セッション必須 | 秘密 | Cookie の HMAC 署名。十分長いランダム文字列。Git 禁止 |
| `SESSION_COOKIE_SECURE` | 任意 | 秘密ではない | `true` なら Secure 属性。本番 HTTPS では `true`。ローカル http は `false` または未設定 |
| `RAG_ENABLED` | 任意 | 秘密ではない | `true` で Gemini API の File Search（人ごとにストア1つ）。Developer API の `GEMINI_API_KEY` か `GOOGLE_API_KEY` が要る。Enterprise の ADC ではストアを作れない。未設定／`false`、またはキーが無いときは Firestore の索引テキストを単語一致。RAG Engine は使わない |

Gemini の呼び出しはサーバーだけ。公式: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/sdks/overview

## 後回し（提出後・需要確認後）

| キー | 区分 | 公開 | 備考 |
|------|------|------|------|
| `SUPABASE_URL` | 後回し | 秘密ではない | 推し活と連携するときだけ。ハッカソン提出物では使わない |
| `SUPABASE_JWT_SECRET` | 後回し | 秘密 | JWT 検証用。サービスロール鍵は置かない |

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
