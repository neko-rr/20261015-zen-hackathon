# デプロイ

実行先は Cloud Run。公開用の識別子は [status.md](status.md)。キー名は [env-contract.md](env-contract.md)。実値は書かない。

`main` への push では、テストが通ったあと Cloud Run に出す。手元は `scripts/deploy.ps1`。手動実行も Actions からできる。GitHub 変数は `GCP_WORKLOAD_IDENTITY_PROVIDER` と `GCP_DEPLOYER_SA`。`SESSION_SIGNING_SECRET` は Actions の secret か、既に Cloud Run にある値。リポジトリには書かない。手順の正は `.cursor/skills/cloud-run-gemini`。AWS 名での読み替えは `.cursor/skills/gcp-for-aws-users`。

ログイン状態・請求確認・本番 URL の運用メモは、リポジトリ外の `20261015-zen-hackathon-private` に置く。

公開前:

- [ ] `.env` が Git に無い
- [ ] `cursor.md` と `notes/` の中身が Git に無い
- [ ] ブラウザ向けの値は公開 URL だけ
- [ ] `/health` がデプロイ URL で開ける
- [ ] 本番 CORS に localhost が無い
