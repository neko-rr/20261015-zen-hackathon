# DESIGN.md — 例（UI デザインシステム）

Google design.md 形式の具体例。大会・スタック非依存。

---

## 例 A: 和風日記アプリ（3時間 MVP）

**入力:** idea.md — 温かみ・手作り感・テキスト入力 → 結果カード

**Overview（抜粋）**

> 寄木細工の温もり。審査員には「丁寧な craft ツール」と感じさせる。  
> 密度は低め、余白多め。

**tokens（抜粋）**

```yaml
colors:
  primary: "#8B4513"    # 木目ブラウン — CTA のみ
  secondary: "#A0522D"
  neutral: "#FAF6F0"
  surface: "#FFFFFF"
typography:
  h1:
    fontFamily: "Noto Serif JP"
    fontSize: 28px
    fontWeight: 600
```

**Do's**

- Do: 結果カードは surface + rounded.md
- Don't: 原色のグラデーション（generic AI UI 回避）

---

## 例 B: テック系ダッシュボード

**Overview:** 精密・信頼。ダーク neutral 背景 + 1 accent。

```yaml
colors:
  primary: "#533AFD"
  neutral: "#0D1738"
  surface: "#1A2340"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    rounded: "{rounded.sm}"   # 4px — シャープ
```

---

## 例 C: sync — ボタンが画面ごとにバラバラ

**きっかけ:** panic で AI が毎回違う purple を生成

**更新:**

1. `components.button-primary` を固定
2. Do's に「ハードコード hex 禁止」を追加
3. `npx @google/design.md lint DESIGN.md`

---

## 悪い例

| 例 | 理由 |
|----|------|
| POST /api/generate を DESIGN に書く | API は design.md の範囲外 |
| mermaid アーキテクチャ図 | 技術設計。別 doc へ |
| 色を prose のみ（tokens 無し） | AI が exact value を再現できない |
| 20 component 定義 | 3時間で実装・維持不能 |
| `#rgb` 短縮 hex | spec は `#RRGGBB` |

---

## 他 Skill 連携

```
hackathon-design-md (initial)
  → フロント実装時エージェントが tokens 参照
  → generic UI が減る
hackathon-tasks-plan
  → P0「DESIGN.md 準拠で Must 画面3つ」
```

技術設計が必要なら **別 Skill / AGENTS.md** で扱う。DESIGN.md に混ぜない。
