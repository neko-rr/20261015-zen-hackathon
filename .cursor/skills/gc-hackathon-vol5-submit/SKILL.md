---
name: gc-hackathon-vol5-submit
description: >-
  第5回ハッカソン提出物の「作り方」。アーキテクチャ図、約3分の YouTube 動画、
  ダッシュボード項目の記入手順。提出準備・動画・図・ダッシュボードの依頼で使う。
  適合の合否判定は gc-hackathon-vol5 の checklist。こちらは作成手順。
---

# 提出物の作り方（第5回）

検査（満たしているか）→ [gc-hackathon-vol5](../gc-hackathon-vol5/SKILL.md) の [checklist](../gc-hackathon-vol5/references/checklist.md)  
操作の確認シート → [docs/demo-script.md](../../../docs/demo-script.md)  
締切: **2026-10-15 23:59**  
ダッシュボード: https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol5/dashboard

記載は **日本語**。秘密・鍵・`.env` の実値は書かない。

## ダッシュボードに揃えるもの

| 項目 | 作り方の要点 |
|------|----------------|
| GitHub 連携 | ダッシュボードからリポジトリを連携（公開・非公開どちらでも可。最大5まで） |
| デプロイ URL | Cloud Run の作品 URL。[cloud-run-gemini](../cloud-run-gemini/SKILL.md) で出し、`/health` が開くこと |
| 動作確認の方法 | ログインなしなら「サンプル写真で操作」と書く。認証があるならテストアカウントとサンプル（ソーシャル／メール受信必須は避ける）。**パスワードを Git に書かない** |
| 説明文 | ユーザー像・課題・ソリューション。`docs/idea.md` を短く要約 |
| システムアーキテクチャ図 | 下節。日本語ラベル |
| YouTube デモ動画 | 約3分・自作。下節 |
| OSS ライセンス | 使う OSS があれば提出物か README にライセンスを書く |
| Zenn 記事 | 任意。書くならカテゴリ Idea |

提出後〜2026-12-01 はデフォルトブランチとデプロイを提出時点のままにする。

## アーキテクチャ図

1. 正本の流れは [docs/architecture.md](../../../docs/architecture.md) の mermaid（web → api → Gemini / Jev / GCS / Firestore）
2. 提出用は `assets/` に画像（PNG や SVG）を書き出す。ファイル名は英語（例: `architecture.png`）
3. 図に含める: Cloud Run（web / api）、Gemini、（あれば）Jev、Cloud Storage、Firestore、ブラウザは Gemini を呼ばないこと
4. 図に書かない: プロジェクト番号以外の秘密、個人メール、鍵、ローカル絶対パス
5. ダッシュボードにはその画像を載せる（または公式の指定形式に従う）

エージェントは図の説明文を日本語で短く添え、実ファイル生成はユーザーがツールを選ぶか、依頼があれば画像生成を使う。

## 約3分のデモ動画

台本の骨格は [docs/demo-script.md](../../../docs/demo-script.md) の操作フロー。

| 目安秒 | 内容 |
|--------|------|
| 0:00–0:20 | 誰向けか・何の課題か（絵描きの資料） |
| 0:20–1:20 | サンプル写真 → 層と関節（絵は生成しない） |
| 1:20–2:20 | 物体を選ぶ → 出典 URL・ライセンス（無ければ未確認） |
| 2:20–2:50 | Google Cloud（Cloud Run）と Gemini を使っていること |
| 2:50–3:00 | まとめ |

撮影の注意:

- 本番 URL か、それに近い動作を映す。モックだけの画面でごまかさない
- 画面に API キー・`.env`・ADC パスを映さない
- YouTube に上げ、ダッシュボードに URL を貼る
- 撮り終わったら `docs/demo-script.md` の操作完了列と「作品URL」欄を更新（URL は提出用メモ。鍵は書かない）

## 説明文の型（短く）

```text
（ユーザー）絵を描く人が、
（課題）写真の構造や出典を自分で調べる負担が大きく、
（解決）写真から層と関節を示し、選んだ物体の出典を履歴に残す。
絵の生成はしない。実行は Cloud Run、AI は Gemini。
```

## 提出直前の順序

1. [mvp-test](../mvp-test/SKILL.md): ローカル pytest・`next build`・本番 `/health`
2. [checklist](../gc-hackathon-vol5/references/checklist.md): 適合と提出前チェック
3. ダッシュボードの提出タブから提出
4. `docs/tasks.md` の提出物チェックを更新

## やらないこと

- 第4回以前の「公開リポジトリ必須」「Zenn 必須」を前提にする
- 提出用にソーシャルログインを足す
- 動画や図に秘密を写す
- 提出後にデフォルトブランチへ直接機能追加

## 関連

| 用途 | パス |
|------|------|
| ルール・合否検査 | [gc-hackathon-vol5](../gc-hackathon-vol5/SKILL.md) |
| デプロイ | [cloud-run-gemini](../cloud-run-gemini/SKILL.md) |
| テスト | [mvp-test](../mvp-test/SKILL.md) |
| 進捗 | `docs/tasks.md` |
