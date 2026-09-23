---
name: cloud-run-gemini
description: >-
  このリポジトリ（illustration-support）向けの Cloud Run デプロイ、ADC、CORS、
  Gemini（サーバーのみ）、GCS / Firestore の境界。デプロイ・Cloud Run・GCS・
  Firestore・本番 CORS・「Gemini をブラウザから？」の依頼で使う。
  キー名の正本は docs/deploy/env-contract.md。実値は書かない。
---

# このリポジトリの Cloud Run + Gemini

個人マシンの `google-cloud-app-runtime` に依存しない。**ここが正**。  
AWS 名での読み替えは [gcp-for-aws-users](../gcp-for-aws-users/SKILL.md)。  
クラウド部品の役割は [docs/architecture.md](../../../docs/architecture.md)。

## 公開してよい識別子

[docs/deploy/status.md](../../../docs/deploy/status.md) を読む。要約:

| 項目 | 値 |
|------|-----|
| プロジェクト | `illustration-support` |
| リージョン | `asia-northeast2`（大阪） |
| API サービス | `illustration-api` |
| 実行 SA | `run-runtime@illustration-support.iam.gserviceaccount.com` |
| 写真バケット | `illustration-support-photos` |
| Gemini 場所 | `GOOGLE_CLOUD_LOCATION=global` |

本番 URL はリポジトリに固定しない。提出フォームとデモに書く。

## 認証（ローカル）

エージェントは代わりにログインしない。未ログインならユーザーに依頼する。

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project illustration-support
```

| 用途 | 手段 |
|------|------|
| gcloud コマンド | `gcloud auth login` |
| ローカルのクライアントライブラリ | ADC（上記の application-default） |
| Cloud Run 上 | 実行サービスアカウント。**鍵 JSON は作らない** |

## 環境変数

キー名の一覧だけ [docs/deploy/env-contract.md](../../../docs/deploy/env-contract.md)。

- ブラウザに出してよいのは `NEXT_PUBLIC_API_BASE_URL` だけ
- 本番 API の `CORS_ORIGINS` に `localhost` を残すな
- Gemini: `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` / `GOOGLE_GENAI_USE_ENTERPRISE=True`
- 写真: `GCS_BUCKET`（バケット名だけ。`gs://` を付けない）
- Jev: `TYPESAFE_API_KEY`（秘密。未設定ならその段は飛ばす）

## デプロイ手順

開発中は push では出さない。出すとき:

1. 手元: `powershell -File scripts/deploy.ps1`（リポジトリ直下）
2. または `.github/workflows/deploy.yml` の手動実行（要 GitHub 変数 `GCP_WORKLOAD_IDENTITY_PROVIDER` / `GCP_DEPLOYER_SA`）

前提:

- `apps/api/Dockerfile` があること（API）
- 画面は `apps/web/Dockerfile` があるときだけデプロイされる
- `--max-instances` を付ける（スクリプト・ワークフロー済み）
- 公開（`--allow-unauthenticated`）は、応答に鍵が無いことを確認してから

## デプロイ後チェック

- [ ] `GET {APIのURL}/health` が 200
- [ ] `.env` と鍵が Git に無い
- [ ] 本番 CORS が Web のオリジンだけ
- [ ] Gemini は `apps/api` だけ。ブラウザから直接呼ばない

手順の短い命令は `.cursor/rules/deploy.mdc`。公開前チェックは [docs/deploy/README.md](../../../docs/deploy/README.md)。

## 保存の境界

| 部品 | 役割 | 注意 |
|------|------|------|
| Cloud Storage | 写真オブジェクト | 公開バケットにしない |
| Firestore | 出典履歴 | 未作成なら status.md の「まだ無いもの」を先に確認 |
| プロセス内 `store.py` | 仮の履歴 | 本番の正ではない。置き換え時もキーをログに出さない |

## やらないこと

- Render / Cloudflare / AWS を実行先にする
- サービスアカウント鍵 JSON の生成・コミット
- AI Studio キーを本番の既定にする（ローカル試作のみ可）
- 実値・署名 URL・Cookie を docs やチャットに書く

## 関連

| 用途 | パス |
|------|------|
| 大会適合・提出前 | [gc-hackathon-vol5](../gc-hackathon-vol5/SKILL.md) |
| Jev | [typesafe-jev](../typesafe-jev/SKILL.md) |
| AWS 名での読み替え | [gcp-for-aws-users](../gcp-for-aws-users/SKILL.md) |
