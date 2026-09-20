# タスク同期ルール

[milestones.md](../hackathon-tasks-plan/milestones.md) の開発時間区分と併用。

## P0 / P1 / 延期

| 条件 | ルール |
|------|--------|
| 次ゲートまで 30分未満 | P1 → `（延期）` |
| P0 が 3件以上残 & ゲート 15分前 | 未着手 P1 を削除候補 |
| ブロッカー 15分未解決 | 代替 P0 を提案 |
| P0 全完了 | 提出物 + demo-script を最優先 |

**sync 頻度:** milestones.md の表（short/half/full）

## panic モード（最小 MVP）

idea.md Must から **審査方式で見せる最小操作 1 本** に絞る。

**手順:**

1. `docs/tasks.md` の `審査方式` を確認
2. [judging-tasks.md](../hackathon-tasks-plan/judging-tasks.md) の必須体験だけ残す
3. 削る機能と理由を表で提示
4. ユーザー承認後 tasks.md を更新

**報告フォーマット:**

```markdown
| 残す（P0） | 削る（Won't 扱い） |
|------------|-------------------|
| {核心1操作} | {Nice / 副次機能} |

理由: {審査時間}内に {方式} で伝わる最小構成
```

具体例 → [examples.md](examples.md)

## ブロッカー記録

```markdown
- 🔴 BLOCKED: {内容}（担当: {名前}）
- 作品URL / 提出物: {URL or TBD}
```

解決 → `✅`

## 新規タスク追加

**可:** Must 漏れ、提出・審査確認漏れ  
**不可:** Nice / Won't、リファクタのみ

## 審査方式別 panic 優先

| 方式 | 最後まで残すもの |
|------|-----------------|
| demo | 1画面 + サンプル入力 + 核心結果 |
| presentation | デモ1本 + 30秒説明メモ |
| submit | ビルド成功 + README |
| hybrid | demo 側を優先、台本は最小 |
