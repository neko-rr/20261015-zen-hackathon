# TypeSafe Jev 参照

実装直前にライブ文書を読む。ここは索引と、2026-09-19 時点で確認した契約の控え。食い違ったら文書を優先する。

## 実装前に開くページ

| 作業 | 最初に開く |
|------|------------|
| モデルの考え方 | https://docs.typesafe.ai/concepts/system-one.md |
| 質問の分け方 | https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md |
| state の形 | https://docs.typesafe.ai/concepts/state.md |
| 型の選択 | https://docs.typesafe.ai/primitives.md |
| 不確実さ | https://docs.typesafe.ai/confidence.md |
| HTTP | https://docs.typesafe.ai/api.md |
| Python | https://docs.typesafe.ai/sdk/python.md |
| Python の使い方 | https://docs.typesafe.ai/sdk/python/usage.md |
| 例外 | https://docs.typesafe.ai/sdk/python/api/exceptions.md |
| 定数・環境変数 | https://docs.typesafe.ai/sdk/python/api/constants.md |
| リトライ | https://docs.typesafe.ai/sdk/python/api/retries.md |
| JavaScript | https://docs.typesafe.ai/sdk/javascript.md |
| モデルと制限 | https://docs.typesafe.ai/models.md |
| 移行 | https://docs.typesafe.ai/migrating-to-v1.md |
| 既知の偏り | https://docs.typesafe.ai/model-jaggedness/jev-1.13.md |

Cookbook の入口は索引 https://docs.typesafe.ai/llms.txt 。コンソール側の一覧は https://console.typesafe.ai/docs/cookbooks 。

この製品に近い例:

| やりたいこと | Cookbook |
|--------------|----------|
| 出典が主張を支えるか | https://docs.typesafe.ai/cookbooks/citation_check.md |
| 候補から原文の値を選ぶ | https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md |
| 検索結果の並べ替え | https://docs.typesafe.ai/cookbooks/rerank_typesafe.md |
| 独立した質問を 1 回で | https://docs.typesafe.ai/cookbooks/parallel_questions.md |
| 確信度で人に回す | https://docs.typesafe.ai/patterns/confidence-routing.md |

## エンドポイント

```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

モデル一覧: `GET https://api.typesafe.ai/v1/models`（同じ Authorization）。

キーの発行手順は Quick start が正: https://docs.typesafe.ai/introduction/quickstart

## 環境変数（Python SDK）

出典: https://docs.typesafe.ai/sdk/python/api/constants.md

| 名前 | 意味 | 既定 |
|------|------|------|
| `TYPESAFE_API_KEY` | API キー | 無し。必須 |
| `TYPESAFE_BASE_URL` | ベース URL | `https://api.typesafe.ai` |
| `TYPESAFE_DEFAULT_MODEL` | モデル | `jev-latest` |
| `TYPESAFE_LOG_LEVEL` | ログレベル | SDK の既定 |

タイムアウトの既定は 1 HTTP 操作あたり 10 秒。キー以外をコードに直書きしない。

## モデル（控え）

出典: https://docs.typesafe.ai/models.md

| 名前 | 意味 |
|------|------|
| `jev-latest` | 安定版エイリアス。SDK の既定。確認時点では `jev-1.13.0` |
| `jev-preview` | プレビューを含む最新。確認時点では `jev-latest` と同じ |
| `jev-1.13.0` | バージョン固定。閾値を合わせたあとはこちらをピンする |

確認時点の制限（変わる、と文書が明記している）:

- 入力はテキストのみ。文字列、JSON オブジェクト、テキストの配列。
- コンテキスト 64k トークン（state と全質問）。state と最長の 1 問で 32k。
- 英語が最も正確。日本語は動くが同等ではない。Confidence を見てから経路に使う。
- 顧客のリクエストでは学習しない。法務: https://docs.typesafe.ai/legal

応答の `model` に、実際に答えたバージョン ID が入る。ログに残してよいのはこの ID と質問 ID と数値。state の本文とキーは残さない。

## リクエストの形

```json
{
  "state": { "passage": "本文", "claim": "主張" },
  "model": "jev-latest",
  "questions": {
    "supports_claim": {
      "type": "noul",
      "instructions": "本文は主張を直接支えている",
      "criteria": {
        "true": "主張の内容が本文にある",
        "false": "本文に無い、または矛盾する"
      }
    }
  }
}
```

Choice の `criteria` は選択肢名から説明へのオブジェクト。説明が不要なら `null`。  
Score の `criteria` は 2 つ以上の説明の配列。レベルは具体的な状況を書く。  
Noul の `criteria` は任意。`true` と `false` の意味。

質問のキーは答えのキーと一致する。モデルには送られない。

## 応答の形

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "supports_claim": { "type": "noul", "noul": 0.92 }
  },
  "usage": { "input_tokens": 312, "output_tokens": 48 }
}
```

Choice は `choice`, `probabilities`, `confidence`。  
Score は `score`, `legend`, `probabilities`, `confidence`。`score` はレベルの間に落ちることがある。

## Python の例外

出典: https://docs.typesafe.ai/sdk/python/api/exceptions.md

基底は `TypeSafeError`。HTTP は `TypeSafeAPIError`（`status`, `body`, `headers`, `endpoint`, `request_id`）。

| クラス | 状態 |
|--------|------|
| `TypeSafeAuthenticationError` | 401 |
| `TypeSafeUnprocessableEntityError` | 422 |
| `TypeSafeRateLimitError` | 429。`retry_after_ms` |
| `TypeSafeAPITimeoutError` | タイムアウト |
| `TypeSafeAPIConnectionError` | 応答無し |
| `TypeSafeInternalServerError` | 5xx |

`request_id` は `x-typesafe-request-id`。サポートに出すとき以外、本文と一緒にログへ出さない。

## インストールを重ねない

公式の導入文（1 つの方法だけ使う）:

- Claude Code: `claude plugin marketplace add typesafe-ai/skills` のあと `claude plugin install typesafe@typesafe-ai`
- その他: `npx skills add typesafe-ai/skills --skill typesafe-ai`
- 手動: https://github.com/typesafe-ai/skills/tree/main/skills/typesafe-ai を agent の skills にコピー

このリポジトリでは、上記の代わりに `.cursor/skills/typesafe-jev/` を使う。公式ディレクトリの再コピーはしない。
