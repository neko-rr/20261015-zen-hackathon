# Google design.md 仕様要約

公式: [google-labs-code/design.md](https://github.com/google-labs-code/design.md) / [docs/spec.md](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md)

本 Skill は spec の **subset** をハッカソン向けに圧縮する。不明点は公式 spec を優先。

## ファイル構造

```
---
version: alpha          # 任意
name: <string>
description: <string>   # 任意
colors: { ... }
typography: { ... }
rounded: { ... }
spacing: { ... }
components: { ... }
---

# {任意の H1 タイトル}

## Overview
...
```

- frontmatter は `---` で囲む
- **tokens が normative**、本文 prose は適用 rationale
- セクション見出しは `##` のみ（パーサ対象）

## Token 型

| 型 | 形式 | 例 |
|----|------|-----|
| Color | `#` + hex | `"#1A1C1E"` |
| Dimension | 数 + 単位 | `48px`, `1.6rem` |
| Typography | オブジェクト | fontFamily, fontSize, fontWeight, lineHeight, letterSpacing |
| Token Reference | `{path.to.token}` | `{colors.primary}` |

## 8 セクション（順序固定）

存在するセクションはこの順。省略可。

1. Overview（Brand & Style）
2. Colors
3. Typography
4. Layout（Layout & Spacing）
5. Elevation & Depth
6. Shapes
7. Components
8. Do's and Don'ts

**同一 `##` 見出しの重複はエラー。**

## components プロパティ

許可: `backgroundColor`, `textColor`, `typography`, `rounded`, `padding`, `size`, `height`, `width`

バリアント例: `button-primary`, `button-primary-hover`

## 未知コンテンツ

| 状況 | 挙動 |
|------|------|
| 未知の `##` セクション | 保持（エラーにしない） |
| 未知の token 名 | 値が valid なら許容 |
| 未知の component プロパティ | 警告付きで許容 |

## CLI（任意）

```bash
npx @google/design.md lint DESIGN.md
npx @google/design.md tailwind DESIGN.md
```

## 本 Skill で書かないもの

| 内容 | 置き場所 |
|------|----------|
| API / エンドポイント | `AGENTS.md`, bedrock Skill |
| アーキテクチャ図 | `docs/infrastructure-*.md` |
| デモ手順 | `docs/demo-script.md` |
| タスク | `docs/tasks.md` |
