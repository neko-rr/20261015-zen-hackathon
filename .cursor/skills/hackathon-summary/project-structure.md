# ハッカソンプロジェクト構成

要約作成時、存在しないフォルダ・ファイルをこの構成で作成する。
**既存ファイルは上書きしない**（追記・更新のみ、またはスキップ）。

## ディレクトリツリー

```
{project-root}/
├── README.md              # プロジェクト入口（要約へのリンク）
├── DESIGN.md              # UI デザインシステム（Google design.md 慣例・任意）
├── .gitignore             # 基本除外設定
├── .env.example           # 環境変数サンプル（実値は .env に）
├── docs/
│   ├── {event-slug}-summary.md
│   ├── {event-slug}-regulation-summary.md  # 応募要項ベース
│   ├── ideas/              # 候補アイデア（1ファイル1案）
│   │   ├── README.md
│   │   ├── comparison.md
│   │   ├── template.md
│   │   └── NN-slug.md
│   ├── idea.md             # 採用案（決定後）
│   ├── DESIGN.md           # UI デザインシステム（任意・docs/ 配置可）
│   ├── tasks.md           # 参加ラウンドのタイムテーブル
│   └── demo-script.md     # 審査用デモ確認（形式は要約に従う）
├── AGENTS.md              # hackathon-agents-md Skillで生成
├── src/                   # アプリケーション本体
│   └── .gitkeep
├── assets/                # 画像・スライド・素材
│   └── .gitkeep
└── notes/                 # 調査メモ・APIメモ
    └── .gitkeep
```

## 設計方針

| 方針 | 理由 |
|------|------|
| `docs/` に情報を集約 | 要約・アイデア・台本をチームで共有しやすい |
| `src/` は空で開始 | 技術スタックは当日決定してもよい |
| `notes/` を分離 | 調査メモと成果物を混ぜない |
| `assets/` を分離 | デモ用画像・スライドをコード外に置く |
| 最小ファイル数 | 3時間開発向け。過剰なボイラープレートは置かない |

## 発展パターン（必要になったら追加）

```
src/
├── frontend/     # Web UI を分ける場合
├── backend/      # API を分ける場合
└── ai/           # プロンプト・RAG・エージェントロジック

docs/
├── DESIGN.md         # UI デザインシステム（docs 集約時。ルート DESIGN.md と同一形式）
└── api-notes.md      # 外部API調査

tests/                # テストを書く余裕ができたら
scripts/              # デプロイ・デモ起動スクリプト
```

## 作成ルール

1. ディレクトリが無ければ作成する
2. ファイルが無ければ [scaffold/](scaffold/) のテンプレートから作成する
3. ファイルが既にあれば内容を上書きしない
4. `README.md` の `{event-slug}` `{イベント名}` `{summary_path}` は要約生成後に置換する
5. `.env` は作成しない（`.env.example` のみ）

## 別Skill化の判断基準

| 状況 | 推奨 |
|------|------|
| 要約 + 最小フォルダ作成（現状） | **同一Skill**（hackathon-summary） |
| 要約のみ欲しい | ユーザー指定または既存プロジェクト検出時にスキップ |
| フレームワーク別ボイラープレート（Next.js/FastAPI等） | **別Skill**（hackathon-scaffold 等）を検討 |
| CI/CD・デプロイ自動化 | **別Skill**（インフラ系は関心が異なる） |
