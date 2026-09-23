---
name: gcp-for-aws-users
description: >-
  AWS の名称しか分からない人向けに、このプロジェクトの Google Cloud 構成を
  AWS 相当と併記して説明する。Cloud Run / Gemini / GCS / Firestore / IAM /
  「Bedrock の代わりは？」と聞かれたとき、または AWS 用語で GCP を尋ねられたときに使う。
  AWS への実装誘導はしない。このリポジトリに AWS は無い。
---

# Google Cloud を AWS 名で読む（このリポジトリ向け）

この大会・このアプリは **Google Cloud のみ**。AWS サービスは使わない・作らない。  
下表は理解用の対応であり、1対1の完全一致ではない。

正本の構成: [docs/architecture.md](../../../docs/architecture.md)  
デプロイ手順: [cloud-run-gemini](../cloud-run-gemini/SKILL.md)

## いま使う部品（AWS 併記）

| このプロジェクト（GCP） | だいたいの AWS 相当 | 役割 |
|-------------------------|---------------------|------|
| Cloud Run（`illustration-api` / `illustration-web`） | App Runner や ECS Fargate＋ALB、または Lambda＋API Gateway に近い「URL で動くコンテナ」 | 画面と API の実行。サーバーレス寄りのコンテナ |
| Gemini Enterprise Agent Platform（`google-genai`） | Amazon Bedrock（InvokeModel） | 写真解析・検索 grounding。**API はサーバーだけ** |
| Cloud Storage（バケット `illustration-support-photos`） | Amazon S3 | 上げた写真のオブジェクト保存 |
| Firestore | DynamoDB（ドキュメント寄り）や DocumentDB に近い「マネージド文書 DB」 | 出典履歴 |
| Cloud Logging | CloudWatch Logs | 見る／検める／探す／確かめる／残すの段ログ |
| サービスアカウント `run-runtime@…` | IAM Role（実行ロール） | Cloud Run が GCS / Gemini 等を呼ぶ身分。**鍵 JSON は作らない** |
| ADC（Application Default Credentials） | ローカルの `~/.aws/credentials` やインスタンスプロファイルに近い「アプリ用の既定認証」 | ローカルは `gcloud auth application-default login` |
| `gcloud` | `aws` CLI | プロジェクト操作・デプロイ |
| Secret Manager または Cloud Run の環境変数 | Secrets Manager / SSM Parameter Store | `TYPESAFE_API_KEY` など。Git に書かない |
| GitHub Actions + Workload Identity | OIDC で AWS に入る（GitHub→IAM Role）に近い | 鍵をリポジトリに置かずデプロイ |
| Artifact Registry + Cloud Build | ECR + CodeBuild（`--source` デプロイ時に裏で動く） | イメージビルド |

## よくある言い換え

| 言われたこと（AWS 頭） | このリポジトリでの答え |
|------------------------|------------------------|
| Bedrock を繋いで | Gemini を `apps/api` から呼ぶ。ブラウザ直呼び禁止 |
| Lambda + API Gateway | Cloud Run の FastAPI（`illustration-api`） |
| S3 に画像を置く | Cloud Storage。バケット名は `docs/deploy/status.md` |
| DynamoDB に履歴 | Firestore（まだ無い場合は構成タスク。メモリの `store.py` は仮） |
| IAM ユーザー鍵を発行 | **しない**。実行 SA と ADC。鍵 JSON 禁止 |
| VPC / セキュリティグループ | ハッカソン MVP では Cloud Run 公開 URL＋CORS。複雑な VPC は足さない |
| CloudFront | 必須ではない。Cloud Run の URL で提出可 |

## やらないこと

- AWS リソース・`boto3`・Bedrock・Lambda の新規追加
- 「AWS の方が慣れているから」とスタックを変える提案
- 対応表を理由に、設計に無いサービスを足すこと

## 関連

| 知りたいこと | 行く先 |
|--------------|--------|
| このリポのデプロイ手順 | [cloud-run-gemini](../cloud-run-gemini/SKILL.md) |
| キー名 | [env-contract.md](../../../docs/deploy/env-contract.md) |
| 公開してよい ID | [status.md](../../../docs/deploy/status.md) |
| 大会ルール | [gc-hackathon-vol5](../gc-hackathon-vol5/SKILL.md) |
