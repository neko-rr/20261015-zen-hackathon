---
name: hackathon-competitive-analysis
description: >-
  短期型ハッカソン向けの競合分析。WebSearch/WebFetch で類似サービス・既存製品を調査し、
  機能比較・差別化・MVP 示唆を notes/competitive/ に記録。競合分析・類似アプリ調査・
  ベンチマーク・差別化ポイント・市場調査の依頼時に使用。
---

# ハッカソン・競合分析（検索ベース）

**Web 検索で事実を集め**、ハッカソン向けに **差別化と MVP 判断** に落とし込む。  
大会・業界非依存。推測より **出典付きの調査結果** を優先。

> 調査メモ → `notes/competitive/` / 採用案への反映 → `docs/ideas/*.md` の差別化

## 配置

```
notes/competitive/
├── README.md                    # 使い方（任意）
├── YYYY-MM-DD-{slug}.md         # 1回の調査セッション
└── _sources.md                  # 共通ソース一覧（任意）

docs/ideas/NN-slug.md            # 「差別化ポイント」へ要約を転記
docs/ideas/comparison.md         # 議論用サマリ（任意）
```

| パス | 役割 |
|------|------|
| `notes/competitive/*.md` | **調査の正**（出典・比較表・所見） |
| `docs/ideas/*.md` | 候補アイデアへの差別化反映 |
| `docs/idea.md` | 採用確定後の最終差別化 |

## トリガー

- 「競合分析して」「類似サービスを調べて」
- アイデア確定前の **差別化確認**
- テーマ確定直後（**15〜20分** の集中調査）
- 「この案、既にない？」の検証

## いつ使わないか

- テーマもカテゴリも未定 → 先に [hackathon-ideation](../hackathon-ideation/SKILL.md) で仮説を1行
- 実装・API 設計 → [hackathon-bedrock](../hackathon-bedrock/SKILL.md) 等
- 深い市場規模・財務分析 → ハッカソン範囲外（スキップ）

## 2つのモード

| モード | いつ | 時間目安 | 出力 |
|--------|------|----------|------|
| **landscape** | カテゴリ全体 | 20〜30分 | 5〜10 競合の一覧比較 |
| **focused** | 特定案・テーマ | 10〜15分 | 3〜5 直接競合 + 差別化案 |
| **sync** | 既存メモ更新 | 5分 | 差分追記のみ |

**3時間大会当日** → **focused のみ**。landscape は前日まで。

## ワークフロー（focused）

```
Task Progress:
- [ ] Step 1: 調査スコープ確定
- [ ] Step 2: 検索クエリ設計
- [ ] Step 3: Web 検索（複数クエリ）
- [ ] Step 4: 主要 URL を Fetch 検証
- [ ] Step 5: 比較表・差別化マトリクス
- [ ] Step 6: notes/competitive/ に出力
- [ ] Step 7: docs/ideas/ へ転記（該当時）
- [ ] Step 8: 品質チェック
```

### Step 1: 調査スコープ

[search-queries.md](search-queries.md) のチェックリスト。

```
【競合分析スコープ】
- 対象: {アイデア名 / テーマキーワード}
- ユーザー: {誰の課題か}
- 直接競合: {同じ体験を提供するもの}
- 間接競合: {別手段で同じ課題を解くもの}
- 除外: {調べない範囲}
- 時間上限: {例: 15分}
この範囲で調査してよいですか？
```

**不明点はユーザー確認。** 推測でカテゴリを広げすぎない。

### Step 2: 検索クエリ設計

最低 **4 クエリ**（[search-queries.md](search-queries.md) 参照）:

| 種別 | 例 |
|------|-----|
| 製品名 | `{キーワード} app`, `{キーワード} サービス` |
| 機能 | `{核心機能} AI tool`, `{核心機能} web app` |
| 日本語 | `{課題} 解決 アプリ`, `{テーマ} ツール` |
| 代替 | `{課題} alternative`, `{既知競合} vs` |

### Step 3: Web 検索

**必須:** `WebSearch` を **複数回** 実行（1クエリ1回）。

- 各結果から **公式サイト・Product Hunt・GitHub・App Store** を優先
- 同一製品は重複カウントしない
- スニペットだけで断定しない → Step 4 へ

### Step 4: URL 検証

上位 **3〜5 URL** を `WebFetch` で取得:

- 実在するか・現在稼働しているか
- 核心機能（1〜2行で要約）
- AI 利用の有無
- **取得日** を記録

Fetch 失敗 → 検索スニペットのみの場合は `{未検証}` と明記。

### Step 5: 比較・差別化

[comparison-matrix.md](comparison-matrix.md) に従い:

1. **機能比較表**（Must 機能が既にあるか）
2. **差別化マトリクス**（我々だけ / 既存も / 不要）
3. **MVP 示唆**（真似しない・簡略化・逆張り）

ハッカソン審査向けに **「3分デモで伝わる差」** を1行で書く。

### Step 6: 出力

[template.md](template.md) をベースに:

`notes/competitive/{YYYY-MM-DD}-{slug}.md`

- slug: 英小文字・ハイフン（例: `yosegi-diary`）
- 既存ファイル → **sync**（追記・更新日）

### Step 7: アイデア doc へ転記

該当 `docs/ideas/NN-slug.md` があれば:

- `## 差別化ポイント` を **3 bullet 以内** で更新
- 出典リンク → `notes/competitive/...` へ

`comparison.md` に1行サマリを追記してもよい（任意）。

### Step 8: 品質チェック

[comparison-matrix.md](comparison-matrix.md) のチェックリスト。

---

## ワークフロー（landscape）

```
- [ ] カテゴリ定義（1文）
- [ ] 検索 6〜8 クエリ
- [ ] 競合 5〜10 件を一覧化（機能1行ずつ）
- [ ] 空白地帯（white space）を1段落
- [ ] focused 用の shortlist（3件）を提案
```

---

## 検索の原則

| 原則 | 内容 |
|------|------|
| 出典必須 | 製品名ごとに URL + 確認日 |
| 未検証明示 | Fetch できなかった claim は `{未検証}` |
| 時間盒 | 3時間大会当日は **15分で打切** → 結果をそのまま議論へ |
| 実装優先 | 「調査完璧」より「差別化1つ決めて実装」 |
| 秘匿 | ログイン情報・API キーは調査対象にしない |

## 他 Skill との順序

```
prep / テーマ直後
    → hackathon-competitive-analysis (focused)
    → hackathon-ideation（差別化を込めて候補更新）
    → hackathon-design-md / tasks-plan
```

競合が **既に Must 機能を全部持つ** → ideation で案の修正または niche 化を提案。

---

## 追加リソース

- 検索クエリ: [search-queries.md](search-queries.md)
- 比較・差別化: [comparison-matrix.md](comparison-matrix.md)
- 出力テンプレ: [template.md](template.md)
- 例: [examples.md](examples.md)
- 雛形: [scaffold/notes/competitive/_template.md](scaffold/notes/competitive/_template.md)

## 関連 Skill

| Skill | 関係 |
|-------|------|
| [hackathon-ideation](../hackathon-ideation/SKILL.md) | 前後（差別化入力） |
| [hackathon-design-md](../hackathon-design-md/SKILL.md) | UI 差別化の参考 |
| [hackathon-tasks-plan](../hackathon-tasks-plan/SKILL.md) | 調査 P1 を入れない |
