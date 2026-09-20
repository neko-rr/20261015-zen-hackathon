---
name: hackathon-tasks-sync
description: >-
  短期型ハッカソン当日の docs/tasks.md 進捗更新。開発時間区分とマイルストーンから
  遅延検知・P1 延期・完了反映を行う。大会・インフラ非依存。タスク更新・進捗同期の依頼時に使用。
---

# ハッカソン・タスク同期（当日更新）

開発中 **何度でも** 実行。`docs/tasks.md` の進捗・優先度・ブロッカーを更新。  
**大会非依存** — ゲート判定は [milestones.md](../hackathon-tasks-plan/milestones.md) に従う。

> 初回分解 → [hackathon-tasks-plan](../hackathon-tasks-plan/SKILL.md)

## トリガー

- 「タスクを更新」「進捗 sync」
- マイルストーン前後
- ブロッカー・機能完了時

## ワークフロー

```
Task Progress:
- [ ] Step 1: 現状把握（時刻・tasks.md・idea.md）
- [ ] Step 2: 開発時間区分とゲート判定
- [ ] Step 3: 完了反映
- [ ] Step 4: 優先度再編（sync-rules.md）
- [ ] Step 5: docs/tasks.md 更新
- [ ] Step 6: 報告
```

### Step 1: 現状把握

| ソース | 内容 |
|--------|------|
| `docs/tasks.md` | タスク表、**審査方式**、**開発時間区分** |
| `AGENTS.md` | マイルストーン |
| `docs/idea.md` | Must |
| ユーザー | 完了・ブロッカー・**現在時刻** |

区分・方式が tasks.md に無い → milestones / judging から再判定またはユーザー確認。

### Step 2: ゲート判定

[milestones.md](../hackathon-tasks-plan/milestones.md) の「ゲート判定」表を適用。  
開発時間区分（short/half/full）で sync 頻度の目安も参照。

### Step 3〜4

[sync-rules.md](sync-rules.md) に従う。完了は **推測で `[x]` にしない**。

### Step 5: 更新範囲

- タスク表・マイルストーンゲートの完了列
- ブロッカー・メモ
- 任意: `## 残り P0（N件）` サマリ

**維持:** 参加情報・チーム・前日チェック

### Step 6: 報告

```markdown
## タスク sync ({HH:mm})

- **区分 / 方式:** {short|half|full} / {demo|…}
- **次ゲート:** {時刻} — {条件}
- **P0 残り:** {N}件
- **延期:** {P1}
- **今やること:** {1行}
```

## 更新モード

| モード | トリガー |
|--------|----------|
| **quick** | 進捗報告 |
| **gate** | マイルストーン時刻 |
| **panic** | 間に合わない — Must を最小化（sync-rules） |

## 関連 Skill

| Skill | 関係 |
|-------|------|
| [hackathon-tasks-plan](../hackathon-tasks-plan/SKILL.md) | 初回のみ |
| [milestones.md](../hackathon-tasks-plan/milestones.md) | ゲート判定 |
| [judging-tasks.md](../hackathon-tasks-plan/judging-tasks.md) | panic 時のデモ最小化 |
| [hackathon-bedrock](../hackathon-bedrock/SKILL.md) | Lambda + Bedrock 実装 |

## 追加リソース

- 再編ルール: [sync-rules.md](sync-rules.md)
- 例: [examples.md](examples.md)
