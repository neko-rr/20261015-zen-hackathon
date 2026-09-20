---
name: hackathon-tasks-plan
description: >-
  短期型ハッカソンでアイデア確定後に docs/tasks.md へ詳細な初期タスクを作成する。
  idea.md の MVP・レギュレーション要約の審査方式・開発時間から P0/P1 を分解。大会・
  インフラ・チーム人数非依存。タスク計画・初期 tasks 作成・役割分担の依頼時に使用。
---

# ハッカソン・タスク計画（初期作成）

アイデア確定 **直後に1回** 実行。`docs/tasks.md` に開発用詳細タスクを書き込む。  
**大会・AWS・チーム人数に依存しない。** 制約はプロジェクト doc から読む。

> 当日更新 → [hackathon-tasks-sync](../hackathon-tasks-sync/SKILL.md)

## トリガー

- アイデア決定直後（`hackathon-ideation` live 完了後）
- 「タスクを分解して」「tasks.md を作って」
- `docs/idea.md` 採用確定後

## ワークフロー

```
Task Progress:
- [ ] Step 1: 制約・審査方式・チームの収集
- [ ] Step 2: 開発時間区分とマイルストーン
- [ ] Step 3: 審査方式に応じた横断 P0
- [ ] Step 4: MVP → タスク分解
- [ ] Step 5: 役割・優先度・時刻
- [ ] Step 6: docs/tasks.md 更新
- [ ] Step 7: 品質チェック
```

### Step 1: 制約・審査方式・チーム

[milestones.md](milestones.md) のチェックリストに従う。

| 優先 | ファイル | 内容 |
|------|---------|------|
| 1 | `docs/idea.md` | Must / Nice / Won't |
| 2 | `DESIGN.md` / `docs/DESIGN.md` | UI tokens・Components（あればフロント P0 に反映） |
| 3 | `docs/ideas/NN-slug.md` | 詳細（あれば） |
| 4 | `docs/*-regulation-summary.md` | 審査方式・提出物・時間 |
| 5 | `AGENTS.md` | マイルストーン・コマンド・チーム |
| 6 | `docs/tasks.md` | 参加情報・タイムライン・**チーム表** |
| 7 | `infra/` / `docs/infrastructure-*.md` | **任意** — デプロイ詳細 |

**idea.md 未決定** → 実行せず ideation を促す。

**チーム人数・名前:** `docs/tasks.md` のチーム表 → `AGENTS.md` → 不明なら `{TBD}`。**人数固定の仮定をしない。**

**デプロイ:** `AGENTS.md` のコマンドセクションを優先。`infra/` は補助。

### Step 2: マイルストーン

[milestones.md](milestones.md) で **short / half / full** を判定し、ゲート表を tasks.md 用に生成。

- 開発開始時刻が分かれば **絶対時刻**（`HH:mm`）
- 不明なら **経過時間**（`+90分`）で記載

### Step 3: 審査方式に応じた横断 P0

[judging-tasks.md](judging-tasks.md) で方式 ID（`demo` / `presentation` / `submit` / `hybrid`）を判定し、横断 P0 を追加。

- プレゼン不要の大会 → スライド P0 を **入れない**
- 操作デモ → サンプル入力・ログイン不要・指定ブラウザ確認
- 判定不能 → ユーザーに確認

### Step 4: MVP → タスク分解

- Must 1行 = 最低 1 P0
- 1タスク = 30分以内
- Nice → P1、Won't → 含めない
- 依存関係を明示

### Step 5: 役割・優先度

| 優先 | 意味 |
|------|------|
| P0 | Must + 横断タスク。未完成だと審査・提出不可 |
| P1 | Nice。P0 後のみ |
| P2 | 記録のみ（当日やらない） |

担当: チーム表の **実名またはロール**（例: `{Alice}`, `{フロント}`）。

### Step 6: docs/tasks.md 更新

**維持:** 参加情報・チーム・前日まで・持ち込み

**追加・更新:**

- `審査方式: {demo|presentation|...}`
- `## 開発タスク（採用案: {名称}）`
- `## マイルストーンゲート`
- `## ブロッカー・メモ`

テンプレ → [template.md](template.md)

### Step 7: 品質チェック

- [ ] 全 Must → P0 対応
- [ ] 審査方式と横断 P0 が一致（judging-tasks.md）
- [ ] 開発時間区分に見合う P0 数（milestones.md）
- [ ] デプロイ P0 あり（提出形式に応じて）
- [ ] demo-script 更新 P0 あり
- [ ] Won't が紛れていない

---

## 関連 Skill

| Skill | タイミング |
|-------|-----------|
| [hackathon-ideation](../hackathon-ideation/SKILL.md) | 直前 |
| [hackathon-design-md](../hackathon-design-md/SKILL.md) | 直前（推奨） |
| [hackathon-tasks-sync](../hackathon-tasks-sync/SKILL.md) | 開発中 |
| [hackathon-bedrock](../hackathon-bedrock/SKILL.md) | Bedrock / LLM API 実装時 |

## 追加リソース

- マイルストーン: [milestones.md](milestones.md)
- 審査方式: [judging-tasks.md](judging-tasks.md)
- テンプレ: [template.md](template.md)
- 例: [examples.md](examples.md)
