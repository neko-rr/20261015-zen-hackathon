# タスク計画 — 例

具体例はここに集約。SKILL.md 本体は大会非依存。

---

## 例 A: 操作デモ + Web + 3時間（本リポジトリ想定）

**入力 doc:**

- regulation-summary: 審査員操作、Chrome、3分/チーム、URL 提出
- AGENTS.md: 10:30 開始、13:30 審査
- tasks.md チーム: Alice（API）、Bob（フロント）
- AGENTS.md コマンド: `infra/deploy-s3.ps1`

**判定:** 開発時間 `short` / 審査方式 `demo`

**横断 P0（judging-tasks）:** Chrome 確認、ログイン不要、サンプル入力、demo-script

**出力（抜粋）:**

```markdown
> 審査方式: demo / 開発時間区分: short

| P | タスク | 担当 | 目標 | 完了 |
|---|--------|------|------|------|
| P0 | フロント起動確認 | Bob | 10:40 | [ ] |
| P0 | 核心 UI | Bob | 11:00 | [ ] |
| P0 | API 連携 | Alice | 11:30 | [ ] |
| P0 | サンプル入力データ | 共同 | 12:15 | [ ] |
| P0 | デプロイ（deploy-s3.ps1） | Alice | 13:00 | [ ] |
| P0 | Chrome + demo-script 確認 | 共同 | 13:15 | [ ] |
```

---

## 例 B: プレゼン審査 + 半日

**入力 doc:**

- regulation-summary: 5分プレゼン + デモ
- 開発 6時間、チーム 4名

**判定:** `half` / `hybrid`

**横断 P0 追加:** 5分リハーサル、台本、デモバックアップ

**担当例:** `{Carol}`, `{Dave}` — チーム表から割当

---

## 例 C: リポジトリ提出のみ + 1日

**判定:** `full` / `submit`

**横断 P0:** push 完了、README、提出期限確認  
**入れない:** ブラウザ確認、スライド（要項に無ければ）

---

## ideation 連携

```
ideation live → idea.md → tasks-plan → （任意）demo-script Skill → 開発
```

## 悪い例

| 例 | 理由 |
|----|------|
| 全員「共同」だけ | 担当不明 |
| プレゼン不要なのにスライド P0 | judging 未確認 |
| infra 必須扱い | AGENTS.md にコマンド無しでも TBD で可 |
| Must 1行「完成」 | 分解不足 |
