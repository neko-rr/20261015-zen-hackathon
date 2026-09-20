# プロンプト設計（JSON 出力）

## 原則

1. **スキーマは doc / ユーザーから取得** — Skill 内に固定しない
2. **JSON のみ** 返させる（markdown コードブロックも禁止と明記）
3. ハッカソン: **短く・デモ向け**（長文禁止）
4. 不適切入力 → スキーマ内 `error` フィールド or 安全なデフォルト

## スキーマ定義テンプレ（実装前に埋める）

```markdown
## Bedrock 入出力

### 入力（API リクエスト body）
| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| text | string | ✓ | ユーザー入力 |

### 出力（Bedrock → Lambda → フロント）
| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| {field} | {type} | | {説明} |
```

`docs/idea.md` に TypeScript 型や JSON 例があればそれを正とする。

## System プロンプトテンプレ

```
You are a structured data generator for a hackathon demo app.

Rules:
- Respond with a single valid JSON object only. No markdown, no explanation.
- Conform exactly to this schema:
{SCHEMA_JSON_OR_TABLE}

- Keep string values concise (under 100 chars unless specified).
- If input is empty or invalid, return: {"error": "invalid_input", ...defaults}
- Language: match the user input language unless specified otherwise.
```

## User プロンプト

```
{sanitized_user_input}
```

**サニタイズ:** 最大文字数（例: 2000）、制御文字除去。超過は 400 エラー。

## Claude Messages API 形式（Bedrock）

```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 1024,
  "system": "{system_prompt}",
  "messages": [
    { "role": "user", "content": [{ "type": "text", "text": "{user_input}" }] }
  ]
}
```

## レスポンスパース

1. `response.body` を読み `completion` / `content[0].text` を取得（モデルにより異なる）
2. `JSON.parse` — 失敗時は **1回** 「JSON only」と再プロンプト or フォールバック
3. 必須フィールド欠落 → フォールバック JSON

## 審査向け調整

| 目的 | プロンプト指示例 |
|------|-----------------|
| AI 活用が見える | 入力キーワードを出力の `{summary}` に含める |
| デモ安定 | 抽象・安全な表現（実在人物・攻撃的内容を避ける） |
| 速度 | `max_tokens` を 512 以下に |

## スキーマ例（参考 — プロジェクトで差し替え）

**テキスト分類:**

```json
{ "category": "string", "confidence": 0.0, "summary": "string" }
```

**創作メタデータ:**

```json
{ "motif": "string", "mood": "string", "tags": ["string"], "caption": "string" }
```

実際のスキーマは **idea.md から生成** し、ここにコピーしない。
