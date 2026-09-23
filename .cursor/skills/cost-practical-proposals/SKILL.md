---
name: cost-practical-proposals
description: >-
  ハッカソン向けに、コスト（費用対効果）と実用性を踏まえた実装提案をする。
  「コスト」「料金」「安い構成」「費用対効果」「実用性」「この実装でよい？」の依頼で使う。
  提案の前に必ず公式の最新料金・制限を Web 検索する。記憶や古い表だけで金額を断定しない。
---

# コストと実用性を踏まえた実装提案

審査軸の「実装品質と拡張性」には **運用性・費用対効果** が含まれる（[regulation-summary](../../../docs/google-cloud-japan-ai-hackathon-vol5-regulation-summary.md)）。  
クラウド費用は自己負担。エントリー者向け **300 ドル分クーポン**（数に限りあり・再発行なし）がある。

このリポジトリの正本構成は [docs/architecture.md](../../../docs/architecture.md)。AWS には出さない。

## 必須: 毎回ネットで最新情報を取る

**料金・クォータ・モデル名・リージョン可否は、スキル内の数値や学習データを正にしない。**  
提案を書く **前に**、次を実行する。

1. `WebSearch`（または同等の検索）で公式ドキュメントを探す
2. 必要なら公式ページを `WebFetch` して本文を確認する
3. 提案文に **取得日** と **出典 URL** を付ける
4. 検索できない・ページが開けないときは、金額を断定せず「未確認。公式で要確認」と書く

### 検索クエリ例（必要に応じて年号・製品名を足す）

| 対象 | 検索の例 |
|------|----------|
| Cloud Run | `Cloud Run pricing asia-northeast2 site:cloud.google.com` |
| Gemini / Agent Platform | `Gemini Enterprise Agent Platform pricing` または `Google Gen AI pricing cloud.google.com` |
| Cloud Storage | `Cloud Storage pricing asia-northeast2 site:cloud.google.com` |
| Firestore | `Firestore pricing site:cloud.google.com` |
| 無料枠・Always Free | `Google Cloud Always Free tier Cloud Run` |
| 大会クーポン | 公式ハッカソンページ FAQ（300 ドル） |

複数案を比べるときは、**案ごとに関係する料金ページを検索**する。1回の検索結果を全製品に流用しない。

## 提案の観点

| 観点 | 見るもの |
|------|----------|
| コスト | リクエスト数・CPU 時間・トークン・保存量・egress。デモ期間〜2026-12-01 維持分 |
| 実用性 | 審査員が URL で触れるか、失敗時の挙動、運用の単純さ、MVP に不要な部品が無いか |
| 大会必須 | 実行プロダクト（Cloud Run 等）と Google Cloud の AI を外さない |
| このリポ | ブラウザから Gemini 直呼び禁止。秘密は Git に出さない |

## ワークフロー

```
Task Progress:
- [ ] Step 1: ユーザーの案または現状構成を短く要約
- [ ] Step 2: 関係サービスの最新料金・制限を Web 検索（必須）
- [ ] Step 3: コストと実用性で 2〜3 案に整理（推奨 / 許容 / 非推奨）
- [ ] Step 4: 推奨案を docs/idea.md の MVP と照合。スコープ外を足さない
- [ ] Step 5: 出典 URL・取得日付きで提案。不明点は質問
```

### Step 3 の書き方

各案に必ず入れる:

- **何をするか**（1〜2 行）
- **だいたいのコスト要因**（例: Cloud Run のインスタンス時間、Gemini の入出力トークン、GCS の保存）。金額は検索結果に基づく概算か「公式の単価 × 想定使用量」
- **実用性**（デモで足りるか、運用が単純か、失敗時）
- **トレードオフ**（安いが遅い、強いが課金が読めない、等）

想定使用量の例（ハッカソン向け。ユーザーの実測があればそちら優先）:

- 審査・デモ: 写真解析と lookup が数十〜百回程度
- 維持: 2026-12-01 まで `/health` と軽いアクセスが来る程度

過大な常時 GPU・巨大クラスタ・本番級マルチリージョンは、理由が無い限り非推奨。

## このプロジェクトでの目安（金額は検索で更新）

記憶の金額は書かない。方向性だけ:

| 寄せ方 | 内容 |
|--------|------|
| 寄せる | Cloud Run の `--max-instances` 抑制、不要サービスの停止、Gemini 呼び出し回数を MVP どおり最小、公開バケットにしない |
| 避けがち | ブラウザ直 Gemini（鍵と課金が危険）、常時高スペック、使わない AI 製品の追加、Render 等への退避（大会条件） |

詳細手順は [cloud-run-gemini](../cloud-run-gemini/SKILL.md)。AWS 名の読み替えは [gcp-for-aws-users](../gcp-for-aws-users/SKILL.md)。

## 出力テンプレ

```markdown
## コスト・実用性の提案（取得日: YYYY-MM-DD）

### 前提
- 対象機能:
- 想定利用量:

### 最新情報（検索結果）
| サービス | 要点 | 出典 URL |
|----------|------|----------|
| … | … | https://… |

### 案
| 案 | 概要 | コスト感 | 実用性 | 判定 |
|----|------|----------|--------|------|
| A | | | | 推奨 |
| B | | | | 許容 |
| C | | | | 非推奨 |

### 推奨とその理由
（MVP・必須プロダクト・費用対効果）

### 確認してほしいこと
（請求・クーポン残高・想定トラフィックなど）
```

## やらないこと

- 検索せずに「だいたい月○円」と断定する
- 必須の Cloud Run / Gemini を外して安く見せる
- クーポン額を超える前提を黙って進める（超えるなら明示して同意を取る）
- 秘密や請求アカウントの実値をチャットや docs に書く

## 関連

| 用途 | パス |
|------|------|
| 大会ルール・審査軸 | [gc-hackathon-vol5](../gc-hackathon-vol5/SKILL.md) |
| デプロイ | [cloud-run-gemini](../cloud-run-gemini/SKILL.md) |
| アイデア壁打ち | [gc-hackathon-vol5-ideation](../gc-hackathon-vol5-ideation/SKILL.md) |
| 提出物 | [gc-hackathon-vol5-submit](../gc-hackathon-vol5-submit/SKILL.md) |
