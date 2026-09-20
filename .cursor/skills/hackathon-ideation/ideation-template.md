# アイデア 1件テンプレート

## 発散時（短縮版 — チャット出力）

```markdown
### 案{N}: {タイトル}

- **一言:** {誰の}{課題}を{どう}
- **核心機能:** （1つだけ）
- **見せ方:** 審査/デモで最初に触らせる操作
- **AI/技術:** （使う場合1行）
- **リスク:** （最大の1つ）
- **ファイル名案:** `docs/ideas/{NN}-{slug}.md`
```

## 候補ファイル（docs/ideas/NN-slug.md）

プロジェクトの [docs/ideas/template.md](../../docs/ideas/template.md) をコピーして作成。

必須ヘッダ:

```markdown
| ID | `{NN}` |
| ステータス | `candidate` |
```

## comparison.md への1行

```markdown
| {NN} | {名称} | {ピッチ15字以内} | A | B | C | D | E | 計 | candidate | [{NN}-{slug}.md]({NN}-{slug}.md) |
```

## 採用時（docs/idea.md）

[idea.md](../../docs/idea.md) に転記する項目:

- 採用案リンク（`ideas/NN-slug.md`）
- 決定日・決定理由
- 一言ピッチ
- MVP（Must）
- 技術スタック

## demo-script / tasks 追記

採用決定後のみ [demo-script.md](../../docs/demo-script.md) / [tasks.md](../../docs/tasks.md) を更新。

```markdown
## 操作フロー（採用案: {名称}）

| 順 | 操作 | 見せたいポイント |
|----|------|----------------|
| 1 | | |
```
