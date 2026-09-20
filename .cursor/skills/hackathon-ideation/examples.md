# アイデア出し — 例

## live モード — ファイル出力例

**Step 4 後の docs/ideas/:**

```
docs/ideas/
├── 01-yosegi-diary.md      # candidate
├── 02-mood-wood-ai.md      # candidate
├── 03-quick-diary-bot.md   # candidate
├── comparison.md           # 全案スコア更新済み
└── README.md
```

**comparison.md 抜粋:**

| ID | 名称 | ピッチ | A | B | C | D | E | 計 | ステータス |
|----|------|--------|---|---|---|---|---|-----|-----------|
| 01 | 寄木日記 | 日記→木目ピース | 3 | 3 | 3 | 3 | 2 | 14 | shortlisted |
| 02 | ムード木材 | 感情→色の木片 | 3 | 2 | 3 | 3 | 2 | 13 | shortlisted |
| 03 | 日記Bot | チャット日記 | 2 | 3 | 2 | 3 | 3 | 13 | shortlisted |
| 04 | SNS分析 | 投稿分析 | 0 | 2 | 2 | 1 | 1 | 6 | rejected |

**Step 6 — AI から人間へ:**

```markdown
## shortlisted（議論用）

1. **01 寄木日記（14点）** — デモインパクト最大
2. **02 ムード木材（13点）** — 実装が最も軽い
3. **03 日記Bot（13点）** — テーマ直球

comparison.md を見ながら、5分以内に選んでください。
```

**Step 7 — idea.md 更新後:**

```markdown
# 採用アイデア

| 採用案 | [01-yosegi-diary.md](ideas/01-yosegi-diary.md) |
| 決定理由 | 審査で「入力→ピース出現」が最も伝わる |
```

## prep モード — 練習

- `docs/ideas/01-yosegi-diary.md` を `candidate` のまま追加
- `idea.md` は「未決定」のまま
- `comparison.md` に議論ルールのみ記載

## 却下例

| 案 | 理由 | comparison への記載 |
|----|------|---------------------|
| 管理画面付きSNS | A=0 | rejected + 「認証・画面多数」 |
