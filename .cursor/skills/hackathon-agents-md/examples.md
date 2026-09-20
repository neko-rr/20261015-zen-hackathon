# AGENTS.md 記載例

汎用テンプレートの適用例。特定大会・スタックに依存しない構造を維持する。

## 入力コンテキスト（例）

```
docs/zenkoku-ai-hackathon-2026-summary.md     ← 大会要約
docs/zenkoku-ai-hackathon-2026-regulation-summary.md
docs/tasks.md                                  ← 3rd 大阪 Aブロック
docs/idea.md                                   ← スタック未確定
```

## 出力例（スタック未確定時）

スタックが決まっていない段階では `{TODO}` を残し、確定後に更新する。

```markdown
# AGENTS.md

> ハッカソン開発用の AI エージェント指示書。チーム全員で共有・更新する。

## プロジェクト概要

- **大会**: 全日本AIハッカソン 2026
- **チーム**: 2名（{メンバーA}: 実装 / {メンバーB}: 実装・発表）
- **開発時間**: 3時間（+ 作業時間）
- **目的**: {テーマ告知後に記入}
- **詳細**: [docs/zenkoku-ai-hackathon-2026-summary.md](docs/zenkoku-ai-hackathon-2026-summary.md)

## ハッカソン制約

- 開発は**9:40 開始合図後のみ**
- 開発中の **AI 利用必須**
- プレゼン **5分** / デモ必須 / Q&A なし
- 提出期限: **14:00**（Aブロック）
- 詳細: [docs/zenkoku-ai-hackathon-2026-regulation-summary.md](docs/zenkoku-ai-hackathon-2026-regulation-summary.md)

## チーム運用

- **意思決定**: 9:30 テーマ告知 → 9:40 までに MVP 確定
- **Git**: main に直接 push（2人チームのため PR 省略）

## 技術スタック

| 項目 | 採用 | 備考 |
|------|------|------|
| 言語 | {TODO} | オリエ後に決定 |
| フレームワーク | {TODO} | |
| AI/LLM | {TODO} | 開発中に必ず使用 |

## コマンド

```bash
# {TODO: スタック決定後に記入}
cp .env.example .env
```

## 開発方針

- MVP 優先。デモ1本通しを 12:00 までに完成
- 13:00 デモリハーサル、14:00 Drive 提出

## AI エージェント向け指示

### やらないこと

- 9:40 前のコード実装（企画・調査のみ）
- API キーのハードコード
- デモに不要な機能追加
```

## 出力例（スタック確定後）

```markdown
## 技術スタック

| 項目 | 採用 |
|------|------|
| 言語 | TypeScript |
| フレームワーク | Next.js 15 (App Router) |
| AI/LLM | OpenAI API (gpt-4o) |
| デプロイ | Vercel |

## コマンド

```bash
cp .env.example .env
npm install
npm run dev        # http://localhost:3000
npm run build      # デプロイ前確認
```
```

## チーム共有のベストプラクティス

1. **AGENTS.md を Git にコミット** — チーム全員が同じ指示を参照
2. **個人設定は書かない** — `.cursor/` の個人 Skill 等は AGENTS.md に混ぜない
3. **更新は最小限** — テーマ確定・スタック変更時のみ。毎コミット更新しない
4. **詳細は docs/ へ** — AGENTS.md はエージェント向けの「圧縮版」
5. **README との役割分担** — README=人間向け、AGENTS.md=AI向け

## よくあるミス

| ミス | 対策 |
|------|------|
| 長すぎる（200行超） | 詳細を docs/ に移しリンク |
| レギュレーション全文コピー | regulation-summary へリンク |
| 秘匿情報の記載 | `.env.example` にキー名のみ |
| 抽象的な指示のみ | コマンド・ファイルパスを具体化 |
