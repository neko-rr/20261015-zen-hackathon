# DESIGN.md テンプレート（Google design.md 準拠）

ルート `DESIGN.md` または `docs/DESIGN.md` に出力。

````markdown
---
version: alpha
name: {プロダクト名}
description: {1行 — ハッカソン採用案}
colors:
  primary: "#1A1C1E"
  secondary: "#6C7278"
  neutral: "#F7F5F2"
  surface: "#FFFFFF"
  on-surface: "#1A1C1E"
typography:
  h1:
    fontFamily: system-ui
    fontSize: 32px
    fontWeight: 700
    lineHeight: 1.2
  body-md:
    fontFamily: system-ui
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  label-md:
    fontFamily: system-ui
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.4
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
rounded:
  sm: 4px
  md: 8px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 12px
  input-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: 12px
---

# {プロダクト名}

## Overview

{ブランド人格・ターゲット・審査員が感じるべき印象。idea.md 参照}

## Colors

- **Primary:** CTA・最重要アクションのみ
- **Secondary:** ボーダー・キャプション
- **Neutral / Surface:** ページ背景・カード

## Typography

- **h1:** 画面タイトル（1画面1つ）
- **body-md:** 本文・説明
- **label-md:** ボタン・フォームラベル

## Layout

{8px 基準 spacing。max-width。Must 画面の情報密度}

## Elevation & Depth

{shadow または border で階層。フラットなら明記}

## Shapes

{角丸方針 — rounded tokens と一致}

## Components

- **button-primary:** メイン CTA
- **input-field:** テキスト入力

{Must 画面の card / list 等を追記}

## Do's and Don'ts

- Do: 1画面に primary CTA は1つ
- Do: DESIGN.md の tokens のみ使用（ハードコード hex 禁止）
- Do: タップ領域 44px 以上
- Don't: 画面ごとにフォントや角丸を変えない
- Don't: primary 色を装飾に使わない
````

## sync 更新時

- tokens 変更 → 参照 `{...}` の整合を確認
- Components 追加のみの場合、## Components と frontmatter の両方を更新
