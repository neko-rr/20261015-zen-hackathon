---
name: hackathon-design-md
description: >-
  短期型ハッカソン向けに Google design.md 仕様の DESIGN.md（UIデザインシステム）を
  作成・更新する。YAML design tokens + Overview/Colors/Typography 等8セクション。
  デザインシステム・UI統一・ブランドトークン・DESIGN.md 作成の依頼時に使用。
---

# ハッカソン・DESIGN.md 作成（Google design.md 準拠）

[Google Labs design.md](https://github.com/google-labs-code/design.md) 仕様に従い、**AI エージェントが UI を一貫して実装できる**デザインシステムファイルを書く。

> **idea.md** = プロダクト（WHAT） / **DESIGN.md** = ビジュアルアイデンティティ（HOW it looks） / **AGENTS.md** = 運用・制約

**技術設計（API・アーキテクチャ）は DESIGN.md に書かない。** それらは `AGENTS.md` や infra doc へ。

## フォーマット概要

| レイヤ | 内容 |
|--------|------|
| **YAML frontmatter** | 色・タイポ・spacing・rounded・components（機械可読 tokens） |
| **Markdown 本文** | 8  canonical セクション（人間・AI 向けの rationale） |

詳細 → [spec-reference.md](spec-reference.md) / 公式 [docs/spec.md](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md)

## 配置

| パス | 用途 |
|------|------|
| ルート `DESIGN.md` | **Google 慣例** — brandmd / Stitch 等の標準 |
| `docs/DESIGN.md` | `docs/` に doc を集約するチーム向け（**同一フォーマット**） |

既存ファイルがあれば **そのパスを維持**。両方ある場合はユーザーにどちらを正とするか確認。

## トリガー

- 「DESIGN.md を作って」「デザインシステムを定義して」
- UI が generic になり始めた（色・フォントがバラバラ）
- `idea.md` 確定後、**フロント実装前**

## いつ使わないか

- アイデア未確定 → [hackathon-ideation](../hackathon-ideation/SKILL.md)
- API / Lambda 設計 → [hackathon-bedrock](../hackathon-bedrock/SKILL.md) / `AGENTS.md`
- タスク分解のみ → [hackathon-tasks-plan](../hackathon-tasks-plan/SKILL.md)

## 2つのモード

| モード | いつ | 動作 |
|--------|------|------|
| **initial** | 初回 | ハッカソン最小セットで tokens + 8 セクション |
| **sync** | 開発中 | tokens / Components / Do's のみ差分更新 |

## ハッカソン最小セット（3時間向け）

[hackathon-minimal.md](hackathon-minimal.md) を参照。**Must 画面に必要な分だけ**。

| 必須 tokens | 必須セクション |
|-------------|---------------|
| `colors`: primary, secondary, neutral, surface | Overview |
| `typography`: h1, body-md, label-md | Colors |
| `spacing`: xs, sm, md, lg | Typography |
| `rounded`: sm, md | Layout |
| `components`: button-primary, input-field | Components |
| | Do's and Don'ts |

Elevation / Shapes は **1段落ずつ** または省略可。

## ワークフロー（initial）

```
Task Progress:
- [ ] Step 1: 入力ソース収集
- [ ] Step 2: ビジュアル方向の確認（人間）
- [ ] Step 3: YAML tokens 草案
- [ ] Step 4: 8 セクション本文
- [ ] Step 5: DESIGN.md 出力
- [ ] Step 6: lint（任意）
- [ ] Step 7: AGENTS.md 整合
- [ ] Step 8: 品質チェック
```

### Step 1: 入力ソース

| 優先 | ソース | 取得内容 |
|------|--------|----------|
| 1 | `docs/idea.md` | テーマ・ターゲット・世界観 |
| 2 | `docs/ideas/NN-slug.md` | ビジュアルイメージ（あれば） |
| 3 | 参考 URL / スクショ | ユーザー提示 |
| 4 | 既存 `src/frontend/` CSS / Tailwind | 既存 tokens（あれば） |
| 5 | `docs/*-regulation-summary.md` | Chrome 審査・可読性制約 |

**idea.md 未決定** → ideation を促す（方向性だけ先に決める場合は Overview のみ draft 可）。

### Step 2: ビジュアル方向の確認（人間）

```
【ビジュアル方向】
- トーン: （例: 温かみ / テック / 和風）
- 参考: （URL または1行）
- 主色のイメージ: 
- Must 画面: （例: 入力 → 結果 → 一覧）
この方向で DESIGN.md を作成してよいですか？
```

**5分タイムボックス。** 完璧より「一貫性」を優先。

### Step 3: YAML tokens

[template.md](template.md) の frontmatter をベースに:

- 色は **#hex**（sRGB）
- 参照は `{colors.primary}` 形式
- components は `button-primary` 等、MVP で使うものだけ

### Step 4: 8 セクション本文

[sections.md](sections.md) の **順序を守る**。存在するセクションは spec 順。

- Overview: ブランド人格・審査員が感じるべき印象
- Do's and Don'ts: **審査3分**向け（1画面1 primary CTA 等）

### Step 5: 出力

[template.md](template.md) をベースに `DESIGN.md` を作成または更新。

- **120行以内**を目標（tokens は compact に）
- 既存ファイル → 差分を提示してから上書き

### Step 6: lint（任意）

CLI が使える環境なら:

```bash
npx @google/design.md lint DESIGN.md
```

エラーがあれば tokens / 重複見出しを修正。

### Step 7: AGENTS.md 整合

| 提案 | 条件 |
|------|------|
| `AGENTS.md` に DESIGN.md パス追記 | 未記載の場合 |
| 「UI 実装時は DESIGN.md に従う」 | 開発方針に無い場合 |

### Step 8: 品質チェック

[sections.md](sections.md) のチェックリストを実施。

---

## ワークフロー（sync）

```
- [ ] 変更理由を Overview 末尾かコミットメッセージに1行
- [ ] 影響 tokens / Components のみ更新
- [ ] lint 再実行（任意）
- [ ] 既存画面との視覚的 regression を確認
```

---

## 他 Skill との順序

```
ideation live → idea.md 確定
    → hackathon-design-md (initial)  ← UI 実装前
    → hackathon-tasks-plan（フロント P0 に「DESIGN.md 準拠」）
    → フロント実装
    → hackathon-design-md (sync) ※コンポーネント追加時
```

---

## 追加リソース

- 公式仕様要約: [spec-reference.md](spec-reference.md)
- セクション定義: [sections.md](sections.md)
- 最小セット: [hackathon-minimal.md](hackathon-minimal.md)
- テンプレ: [template.md](template.md)
- 例: [examples.md](examples.md)
- 雛形: [scaffold/DESIGN.md](scaffold/DESIGN.md)

## 関連 Skill

| Skill | 関係 |
|-------|------|
| [hackathon-ideation](../hackathon-ideation/SKILL.md) | 直前（世界観・Must 画面） |
| [hackathon-tasks-plan](../hackathon-tasks-plan/SKILL.md) | 並行〜直後 |
| [hackathon-agents-md](../hackathon-agents-md/SKILL.md) | AGENTS.md 整合 |
