# `.cursor/rules`

エージェントへの命令。解説の正本は `docs/`。

| 設定 | 意味 |
|------|------|
| `alwaysApply: true` | 毎回 |
| `globs` | そのパスを触るとき |
| `alwaysApply: false` | 説明に合うときだけ |

| ファイル | 頻度 |
|----------|------|
| security.mdc | 毎回 |
| architecture.mdc | 毎回 |
| naming.mdc | 毎回 |
| api_contract.mdc | `apps/` を触るとき |
| deploy.mdc | デプロイや本番 URL のとき |

入口はリポジトリ直下の `AGENTS.md`。環境変数のキー名は `docs/deploy/env-contract.md`。
