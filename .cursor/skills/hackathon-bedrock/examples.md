# Bedrock 連携 — 例

具体例はここに集約。SKILL.md は非依存。

---

## 例 A: テキスト → 構造化 JSON（汎用）

**idea.md スキーマ:**

```json
{ "summary": "string", "tags": ["string"], "sentiment": "positive|neutral|negative" }
```

**API:** `POST /api/analyze` body `{ "text": "..." }`

**用途:** 分類・要約・タグ付け系 MVP

---

## 例 B: ユーザー入力 → 創作メタデータ

**idea.md スキーマ:**

```json
{ "motif": "string", "mood": "string", "colors": ["#hex"], "caption": "string" }
```

**用途:** 入力を別表現（UI・SVG・画像）に変換するアプリ

**フロント:** JSON を受け取り procedural 描画（画像生成 API は Nice）

---

## 例 C: チャット 1 ターン

**入出力:**

```json
// in:  { "message": "string" }
// out: { "reply": "string" }
```

**注意:** 会話履歴は MVP では **1ターンのみ**（状態管理を避ける）

---

## ワークフロー例

```
1. idea.md から JSON スキーマを読む
2. prompt-guide で system プロンプト生成
3. src/backend/ に handler 追加
4. error-handling の fallback 定義
5. フロント fetch 接続
6. demo-script のサンプル入力でテスト
```

---

## フォールバック例（例 B）

```json
{
  "fallback": true,
  "motif": "demo",
  "mood": "neutral",
  "colors": ["#8B7355", "#DEB887"],
  "caption": "Demo mode"
}
```

---

## やってはいけない例

| 例 | 理由 |
|----|------|
| React から `@aws-sdk` + キー直書き | キー露出 |
| スキーマ未定で実装開始 | パース不能 |
| 500 のみ返して UI 停止 | 審査デモ中断 |
| max_tokens 8192 | 遅延・コスト |

---

## 他 LLM（OpenAI 等）を使う場合

- アーキテクチャ（Lambda 経由・JSON 出力・フォールバック）は **同じ**
- Invoke 部分のみ API 差し替え
- 秘匿: `OPENAI_API_KEY` を `.env` + Lambda 環境変数

Bedrock 専用 Skill だが **パターンは転用可**。
