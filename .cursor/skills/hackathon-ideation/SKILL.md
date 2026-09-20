---
name: hackathon-ideation
description: >-
  短期型ハッカソン（数時間〜1日）向けのアイデア出し。テーマに沿ったMVP案の発散・絞り込み・
  実現性評価・docs/ideas/ への候補記録と docs/idea.md への採用反映。ブレスト・アイデア出し・
  MVP決定・チーム議論・テーマ確定後の方針整理の依頼時に使用。
---

# ハッカソン・アイデア出し

短期型ハッカソン向けの **アイデア発散 → 候補ファイル化 → 比較 → 採用決定** ワークフロー。  
大会・技術スタックに依存しない。**プロジェクト内ドキュメントがあればそこから制約を読み取る。**

## フォルダ構成

```
docs/ideas/
├── README.md           # 使い方
├── comparison.md       # 比較表・議論メモ（チーム議論の中心）
├── template.md         # 1案の雛形
└── NN-slug.md          # 候補アイデア（1ファイル1案）

docs/idea.md            # 採用案のみ（決定後に更新）
```

| ファイル | 役割 |
|---------|------|
| `docs/ideas/NN-slug.md` | 各候補の詳細 |
| `docs/ideas/comparison.md` | 全案スコア・ステータス・議論メモ |
| `docs/idea.md` | **採用1案**のサマリ（開発の正） |

## トリガー

- 「アイデア出し」「ブレスト」「MVPを決めたい」
- テーマ告知直後の方針整理
- 複数案の比較・チーム議論の準備

## 2つのモード

| モード | いつ | 目的 | 出力 |
|--------|------|------|------|
| **prep** | テーマ未確定 | 手法合意・練習 | `comparison.md` ルールのみ可 |
| **live** | テーマ確定後 | 候補生成→議論→採用 | `docs/ideas/*.md` + `idea.md` |

```
テーマ未確定 → prep（候補は練習扱い、selected にしない）
テーマ確定   → live（comparison → shortlisted → selected → idea.md）
```

## ワークフロー（live）

```
Task Progress:
- [ ] Step 1: 制約の収集
- [ ] Step 2: テーマ解釈の確認（人間必須）
- [ ] Step 3: 発散（10案以上）
- [ ] Step 4: 候補ファイル作成（上位5〜10案）
- [ ] Step 5: 実現性スコアリング → comparison.md 更新
- [ ] Step 6: 人間による議論・shortlisted 決定
- [ ] Step 7: 最終決定 → idea.md 反映
- [ ] Step 8: DESIGN.md / demo-script / tasks 更新
- [ ] Step 9: 品質チェック
```

### Step 1: 制約の収集

[constraints.md](constraints.md) を参照。推測しない。

### Step 2: テーマ解釈の確認（人間必須）

解釈案を提示し、**ユーザー確認後**に Step 3 へ。

### Step 3: 発散

10案以上。[ideation-template.md](ideation-template.md) の短縮版で出力。

### Step 4: 候補ファイル作成

**上位5〜10案**（または全案）を `docs/ideas/` に保存する。

**命名:** `{NN}-{slug}.md`（例: `02-voice-diary-ai.md`）

- 既存の最大 NN を確認し +1 する
- [template.md](../../docs/ideas/template.md) をベースに各ファイルを作成
- 各ファイルの `ステータス` は `candidate`

**1ファイルにまとめない。** チームが個別に読めるよう **1案1ファイル** を徹底。

### Step 5: スコアリング → comparison.md

[mvp-scorer.md](mvp-scorer.md) で採点し、[comparison.md](../../docs/ideas/comparison.md) の比較表を更新。

**（任意）** 各候補の差別化が弱い場合 → [hackathon-competitive-analysis](../hackathon-competitive-analysis/SKILL.md) focused（15分）を提案。

| ID | 名称 | ピッチ | A〜E | 計 | ステータス | ファイル |
|----|------|--------|------|-----|-----------|----------|

- 9点未満は `rejected` 候補として理由を記載
- 上位3案を `shortlisted` に更新

### Step 6: 人間による議論

AI は **1案を決め打ちしない。** `comparison.md` の shortlisted を提示し、ユーザーに選ばせる。

**comparison.md に追記:**

```markdown
### 第N回（日付）
- shortlisted: 01, 03, 05
- メモ: ...
```

タイムボックス: 3時間大会なら **5分**。

### Step 7: 採用決定 → idea.md

ユーザーが選んだ1案について:

1. 該当 `docs/ideas/NN-slug.md` のステータス → `selected`
2. 他 shortlisted → `rejected`（comparison.md に理由）
3. [idea.md](../../docs/idea.md) にピッチ・MVP・技術を転記
4. `AGENTS.md` の「目的」が `{TODO}` なら更新を提案

### Step 8: 関連 doc 更新

| ファイル | 内容 |
|---------|------|
| `docs/DESIGN.md` または `DESIGN.md` | [hackathon-design-md](../hackathon-design-md/SKILL.md) で **UI デザインシステム**（**tasks より先**） |
| `docs/demo-script.md` | 採用案のデモ手順 |
| `docs/tasks.md` | [hackathon-tasks-plan](../hackathon-tasks-plan/SKILL.md) で初期分解 |

### Step 9: 品質チェック

- [ ] `docs/ideas/` に候補が1ファイル1案で存在
- [ ] `comparison.md` に全候補のスコア行がある
- [ ] `selected` は **1案のみ**
- [ ] `idea.md` が採用案と一致
- [ ] テーマ・審査方式と MVP が対応

---

## ワークフロー（prep）

テーマ未確定。**selected にしない。**

```
- [ ] Step P1: 制約の確定分を整理
- [ ] Step P2: comparison.md に議論ルールを記載
- [ ] Step P3: （任意）[hackathon-competitive-analysis](../hackathon-competitive-analysis/SKILL.md) で landscape 調査
- [ ] Step P4: （任意）ダミーテーマで docs/ideas/ に練習候補を追加
```

練習候補は `ステータス: candidate` のまま。`idea.md` は「未決定」のまま。

---

## 人間 vs AI の分担

| 担当 | 人間 | AI |
|------|------|-----|
| テーマ解釈合意 | ● | 補助 |
| 10案発散 | | ● |
| 候補ファイル作成 | 確認 | ● |
| comparison 更新 | 確認 | ● |
| shortlisted / 最終決定 | ● | 推奨のみ |
| idea.md 反映 | 確認 | ● |

---

## 出力フォーマット（live Step 5 後）

```markdown
## 候補一覧

| ID | 名称 | 計 | ファイル |
|----|------|-----|----------|
| 01 | ... | 12 | docs/ideas/01-....md |

## shortlisted（議論用）

1. **01** — 理由
2. **03** — 理由
3. **05** — 理由

→ どれで進めますか？
```

---

## 関連 Skill

- 大会ドキュメント: [hackathon-summary](../hackathon-summary/SKILL.md)
- UI デザイン: [hackathon-design-md](../hackathon-design-md/SKILL.md)（採用直後）
- 競合分析: [hackathon-competitive-analysis](../hackathon-competitive-analysis/SKILL.md)（prep / テーマ直後）
- AGENTS.md: [hackathon-agents-md](../hackathon-agents-md/SKILL.md)

## 追加リソース

- 制約: [constraints.md](constraints.md)
- 採点: [mvp-scorer.md](mvp-scorer.md)
- 1案テンプレ: [ideation-template.md](ideation-template.md)
- 例: [examples.md](examples.md)
- プロジェクト雛形: [../../docs/ideas/template.md](../../docs/ideas/template.md)
- 当日シート: [scaffold/docs/idea-brainstorm.md](scaffold/docs/idea-brainstorm.md)
