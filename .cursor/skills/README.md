# `.cursor/skills` 目次

エージェントは依頼内容に合う skill の `SKILL.md` を読んでから動く。  
ルール（毎回・パス別）は [../rules/README.md](../rules/README.md)。

このリポジトリに **AWS / Bedrock 用 skill は無い**。実行は Google Cloud（Cloud Run）のみ。

## いつどれを読むか

| 依頼の例 | Skill |
|----------|--------|
| ハッカソンのルール・適合・提出前チェック | [gc-hackathon-vol5](gc-hackathon-vol5/SKILL.md) |
| 提出物の作り方（図・3分動画・ダッシュボード） | [gc-hackathon-vol5-submit](gc-hackathon-vol5-submit/SKILL.md) |
| 第5回向けアイデア壁打ち | [gc-hackathon-vol5-ideation](gc-hackathon-vol5-ideation/SKILL.md) |
| 要約・レギュレーション整理（汎用） | [hackathon-summary](hackathon-summary/SKILL.md) |
| AGENTS.md の作成・更新 | [hackathon-agents-md](hackathon-agents-md/SKILL.md) |
| 汎用アイデア出し（第5回は vol5-ideation を優先） | [hackathon-ideation](hackathon-ideation/SKILL.md) |
| 競合調査 | [hackathon-competitive-analysis](hackathon-competitive-analysis/SKILL.md) |
| tasks.md の初回分解 | [hackathon-tasks-plan](hackathon-tasks-plan/SKILL.md) |
| tasks.md の進捗 sync（本戦は date ベース。short/panic は明示時のみ） | [hackathon-tasks-sync](hackathon-tasks-sync/SKILL.md) |
| DESIGN.md（UI トークン） | [hackathon-design-md](hackathon-design-md/SKILL.md) |
| Cloud Run / Gemini / GCS / Firestore / デプロイ / CORS | [cloud-run-gemini](cloud-run-gemini/SKILL.md) |
| コスト・実用性を踏まえた実装提案（料金は必ず Web 検索） | [cost-practical-proposals](cost-practical-proposals/SKILL.md) |
| 「Bedrock 相当は？」「S3 は GCP で何？」など AWS 名での理解 | [gcp-for-aws-users](gcp-for-aws-users/SKILL.md) |
| TypeSafe Jev（検める・確かめる） | [typesafe-jev](typesafe-jev/SKILL.md) |
| テスト（pytest・/health・next build） | [mvp-test](mvp-test/SKILL.md) |
| 実装後に docs / API 契約を他セッション向けに同期 | [impl-docs-sync](impl-docs-sync/SKILL.md) |

## 正本ドキュメント（skill より優先）

| 内容 | パス |
|------|------|
| MVP | `docs/idea.md` |
| クラウド設計 | `docs/architecture.md` |
| 環境変数のキー名 | `docs/deploy/env-contract.md` |
| 公開してよい識別子 | `docs/deploy/status.md` |
| 大会ルール要約 | `docs/google-cloud-japan-ai-hackathon-vol5-regulation-summary.md` |
