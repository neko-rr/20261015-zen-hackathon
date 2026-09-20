# DESIGN.md セクション定義（Google design.md 準拠）

[spec-reference.md](spec-reference.md) に沿う。ハッカソンでは [hackathon-minimal.md](hackathon-minimal.md) で subset 可。

## 8 セクション（公式順）

| # | 見出し | 本文で書くこと | tokens |
|---|--------|---------------|--------|
| 1 | Overview | ブランド人格・ターゲット・UI が evoke する感情 | — |
| 2 | Colors | パレットの役割（primary = CTA 等） | `colors` |
| 3 | Typography | 見出し/本文/ラベルの使い分け | `typography` |
| 4 | Layout | グリッド・余白・max-width | `spacing` |
| 5 | Elevation & Depth | shadow か border か | — |
| 6 | Shapes | 角丸・シャープネスの方針 | `rounded` |
| 7 | Components | button / input / card 等の variant | `components` |
| 8 | Do's and Don'ts | エージェント向け guardrails | — |

**順序を入れ替えない。** 省略するセクションは飛ばしてよい。

## ハッカソン必須（initial）

```
- [ ] YAML frontmatter あり（name + colors + typography + spacing + rounded + components）
- [ ] Overview / Colors / Typography / Layout / Components / Do's and Don'ts
- [ ] Must 画面で使う component が tokens に定義されている
- [ ] primary 色が CTA にのみ使われる旨が Do's にある
```

## 書かないもの

| 除外 | 理由 |
|------|------|
| API / Lambda / Bedrock | 技術設計。DESIGN.md の範囲外 |
| データモデル | 同上 |
| デモ手順 | demo-script.md |
| タスク一覧 | tasks.md |
| プロンプト全文 | コード / bedrock Skill |
| API キー | .env のみ |

## 品質チェックリスト

```
- [ ] 公式 8 セクション順を守っている（存在するもの）
- [ ] 色はすべて #hex（sRGB）
- [ ] components の参照 `{colors.*}` が frontmatter に存在
- [ ] 同一 ## 見出しが重複していない
- [ ] idea.md の世界観と Overview が矛盾しない
- [ ] Must 画面に必要な UI パターンが Components で足りる
- [ ] WCAG AA（4.5:1）を Do's に明記
- [ ] 120行以内（超過時は hackathon-minimal から削る）
- [ ] 技術設計（API 等）が混入していない
```

## lint よくあるエラー

| エラー | 対処 |
|--------|------|
| 重複 `## Colors` | 1つに統合 |
| 無効な color | `#` + 6桁 hex |
| 壊れた `{reference}` | frontmatter のパスを確認 |
