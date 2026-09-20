# ハッカソン最小 DESIGN.md

**3時間開発**向け。審査員が Chrome で触る **Must 画面**だけカバーする。

## 目標

- 初回作成 **15分以内**
- AI が生成する UI の **generic 化を防ぐ**
- tokens 変更 → 全画面に波及（一貫性）

## 最小 YAML tokens

```yaml
---
version: alpha
name: {プロダクト名}
colors:
  primary: "#..."      # CTA・強調
  secondary: "#..."    # 補助テキスト・ボーダー
  neutral: "#..."      # 背景
  surface: "#..."      # カード背景
  on-surface: "#..."   # カード上テキスト
typography:
  h1:
    fontFamily: {system-ui または Google Fonts 1種}
    fontSize: 32px
    fontWeight: 700
    lineHeight: 1.2
  body-md:
    fontFamily: {同上}
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  label-md:
    fontFamily: {同上}
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
```

## 最小 Markdown セクション

| セクション | 最低限書くこと |
|-----------|---------------|
| Overview | 1段落（トーン + 審査印象） |
| Colors | primary/secondary の役割（各1行） |
| Typography | 見出し vs 本文の使い分け |
| Layout | spacing スケール（8px 基準等） |
| Components | button-primary, input-field の用途 |
| Do's and Don'ts | **3項目以上**（下記テンプレ） |

### Do's and Don'ts テンプレ（審査向け）

```markdown
## Do's and Don'ts

- Do: 1画面に primary CTA は1つだけ
- Do: 本文は body-md、見出しは h1 のみ（ weight は2種まで）
- Do: **IT素人の審査員**向け — 専門用語を使わず、操作は大きく・少なく
- Do: タップ/クリック領域は最低 44px
- Don't: 審査3分で説明が必要な UI
- Don't: 小さなリンク・隠しメニュー・多段階の設定
- Don't: 画面ごとに角丸や色を変えない
- Don't: 4.5:1 未満のコントラスト（WCAG AA）
```

## 省略してよいもの

| 項目 | 条件 |
|------|------|
| Elevation & Depth | フラット UI なら「shadow 使わず border で階層」と1行 |
| Shapes | Layout に角丸方針を含めれば省略可 |
| tertiary 色 | Must 画面に accent が1色で足りる場合 |
| chip / tooltip 等 | Must に無ければ定義しない |

## Must 画面から逆算

`idea.md` の Must を画面に分解:

```
Must: テキスト入力 → AI 結果表示
  → 必要 components: input-field, button-primary, card（結果）
Must: 履歴一覧
  → list item スタイルを Components に1行追加
```

**Must に無いコンポーネントは tokens に追加しない**（panic 防止）。
