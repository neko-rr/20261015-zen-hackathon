# 要約ファイルの記載例

## 正しい情報源の取り方

```
1. https://www.aifestival.jp/hackathon          ← 大会概要
2. https://www.aifestival.jp/hackathon/entry-2026-3  ← 3rd大阪（正）
3. PDF（任意）← 2と照合。矛盾時は 2 を正とする
```

## 失敗例（再発防止）

### 何が起きたか

2026年3rd大阪向けレギュレーション要約に、**2025年頃のルール**が混入した。

| 誤記 | 正 |
|------|-----|
| プレゼン5分 | プレゼン不要 |
| Google Drive + QR | Web作品URL提出 |
| 参加費1,100円 | 無料 |
| Aブロック 9:00集合 | 10:15集合 |

### 原因

1. 画像PDFを正として要約（テキスト抽出不可）
2. **応募要項ページを取得・照合しなかった**
3. 一般的なハッカソン常識（プレゼン・Drive）で補完
4. 別ラウンド・別年次の情報を混在

### 防止策

→ [verification.md](verification.md) の Step 2.5 クロスチェックを必須化

## 出力例（大会概要・正）

```markdown
---
primary_source: https://www.aifestival.jp/hackathon
fetched_at: 2026-05-29
event_name: 全日本AIハッカソン 2026
verified: true
---

## ルール（2026年予選）

詳細 → [regulation-summary.md](zenkoku-ai-hackathon-2026-regulation-summary.md)

| 項目 | 内容 |
|------|------|
| 作品 | Google Chrome で体験できるWeb作品 |
| 審査 | 審査員が操作（3分/チーム） |
| プレゼン | 不要 |
| 提出 | Web作品URLを事務局に提出 |
```

## 出力例（レギュレーション・正）

```markdown
---
primary_source: https://www.aifestival.jp/hackathon/entry-2026-3
event_round: 3rd
event_date: 2026-05-30
verified: true
---

## 当日スケジュール（Aブロック）

| 時刻 | 内容 | 出典 |
|------|------|------|
| 10:15 | 集合 | 応募要項 |
| 10:30-13:30 | ハッカソン | 応募要項 |
| 13:30-14:30 | 審査会 | 応募要項 |
```

## オンライン単発・24時間制

従来どおり。ただし**必ずその大会の応募要項**から取得すること。
