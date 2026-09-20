---
name: hackathon-bedrock
description: >-
  短期型ハッカソン向け Amazon Bedrock 連携。Lambda/API Gateway 経由の InvokeModel、
  JSON 出力プロンプト、タイムアウト・フォールバック、.env/SSM の秘匿管理。
  Bedrock・LLM API・Claude on AWS の実装依頼時に使用。
---

# ハッカソン・Bedrock 連携

**Amazon Bedrock** をバックエンド（Lambda 等）から呼ぶ実装向け Skill。  
出力 JSON スキーマは **プロジェクト doc から読む**。アプリ固有のフィールドを Skill 内に固定しない。

> タスク管理 → [hackathon-tasks-plan](../hackathon-tasks-plan/SKILL.md) / [hackathon-tasks-sync](../hackathon-tasks-sync/SKILL.md)

## トリガー

- Bedrock / Lambda / API Gateway の AI 連携実装
- 「LLM API を作って」「Bedrock を繋いで」
- プロンプト設計・JSON 出力・デモ用フォールバック

## いつ使わないか

- Bedrock 以外のみ（OpenAI 直叩き等）→ 本 Skill の SSM/JSON パターンのみ参考に
- アイデア出し・デプロイ全体・フロントのみ → 各専用 Skill

## アーキテクチャ（推奨）

```
[フロント] → [API Gateway] → [Lambda] → [Bedrock InvokeModel]
                ↑
         秘匿: .env（ローカル）/ SSM or 環境変数（Lambda）
```

**フロントから Bedrock を直接呼ばない**（キー露出）。必ず Lambda 等を経由。

## ワークフロー

```
Task Progress:
- [ ] Step 1: 入出力仕様の確定
- [ ] Step 2: 環境・モデル ID の確認
- [ ] Step 3: プロンプト設計（JSON 出力）
- [ ] Step 4: Lambda 実装
- [ ] Step 5: エラー処理・デモ用フォールバック
- [ ] Step 6: フロント連携・動作確認
- [ ] Step 7: 品質チェック
```

### Step 1: 入出力仕様

| 優先 | ソース | 内容 |
|------|--------|------|
| 1 | ユーザー指示 | 入力・期待 JSON |
| 2 | `docs/idea.md` / `docs/ideas/*.md` | データモデル・AI 役割 |
| 3 | `AGENTS.md` | 技術スタック |

**出力 JSON スキーマ** を明示する（フィールド名・型）。未確定ならユーザーに確認。

[prompt-guide.md](prompt-guide.md) のテンプレにスキーマを埋める。

### Step 2: 環境・モデル

[security.md](security.md) に従う。

| 項目 | 読む場所 |
|------|---------|
| リージョン | `.env` / `.env.example` / `AGENTS.md` |
| モデル ID | `BEDROCK_MODEL_ID` / ユーザー指定 |
| Model access | 事前に有効化済みか確認を促す |

**リージョンとモデル ID の組み合わせ** が doc に無ければ `.env.example` を更新提案（値はコミットしない）。

### Step 3: プロンプト設計

- **system**: JSON のみ返す・スキーマ厳守・余計な markdown 禁止
- **user**: フロントから渡すユーザー入力（サニタイズ後）
- ハッカソン向け: 短い応答・デモに適したトーン

詳細 → [prompt-guide.md](prompt-guide.md)

### Step 4: Lambda 実装

[invoke-pattern.md](invoke-pattern.md) のパターンに従う。

- `src/backend/` またはプロジェクト既存構成に合わせる
- ランタイムは **プロジェクト既存**（Python / Node）を優先。新規言語を増やさない
- タイムアウト: Lambda **29秒以内**（API Gateway 上限を意識）、Bedrock 呼び出しに **15〜25秒** 目安

### Step 5: エラー処理・フォールバック

[error-handling.md](error-handling.md) 必須:

- try-catch（外部 API）
- Throttling / ModelTimeout → 1回リトライ
- **審査用フォールバック JSON** — Bedrock 失敗時も UI が動く固定レスポンス
- ログに **入力全文・API キー** を出さない

### Step 6: フロント連携

- `fetch('/api/...')` または環境変数 `VITE_API_URL`
- ローディング・エラー表示（審査員向けに「再試行」またはフォールバック表示）
- CORS: API Gateway でフロント origin を許可

### Step 7: 品質チェック

- [ ] キーがコード・Git に無い
- [ ] 成功時レスポンスがスキーマどおり
- [ ] Bedrock 障害時フォールバックが返る
- [ ] ローカル + デプロイ先の両方で手順が doc にある
- [ ] `docs/demo-script.md` 用サンプル入力で 1 回成功

---

## 関連 Skill

| Skill | 関係 |
|-------|------|
| [hackathon-tasks-plan](../hackathon-tasks-plan/SKILL.md) | API 連携 P0 タスク |
| [hackathon-ideation](../hackathon-ideation/SKILL.md) | 採用案の AI 役割 |

## 追加リソース

- Invoke 実装: [invoke-pattern.md](invoke-pattern.md)
- プロンプト: [prompt-guide.md](prompt-guide.md)
- エラー: [error-handling.md](error-handling.md)
- 秘匿: [security.md](security.md)
- 例: [examples.md](examples.md)
