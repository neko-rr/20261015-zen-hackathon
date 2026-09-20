# 秘匿情報・セキュリティ

## 絶対禁止

- API キー・Access Key を **ソースコードに直書き**
- `.env` を **Git コミット**
- ログ・チャット・エラーメッセージに **秘匿値を出力**
- フロント JS から **Bedrock 直接呼び出し**（キー露出）

## 読み込み優先順位

| 環境 | 方式 |
|------|------|
| ローカル開発 | `.env`（`.gitignore` 済み） |
| Lambda（本番） | 環境変数 or **SSM Parameter Store** |
| CI | シークレットストア（ハッカソンでは稀） |

`.env.example` には **キー名のみ**。値は空 or プレースホルダ。

## 環境変数（標準名）

| 変数 | 用途 |
|------|------|
| `AWS_REGION` | リージョン |
| `AWS_PROFILE` | ローカル CLI プロファイル（任意） |
| `BEDROCK_MODEL_ID` | モデル ID |
| `VITE_API_URL` | フロント → API Gateway URL（ビルド時） |

プロジェクトが別名を使う場合 → `AGENTS.md` / `.env.example` を正とする。

## SSM（Lambda 向け・任意）

```
/bedrock/model-id
/app/api-key  （Bedrock 以外の外部 API 用）
```

Lambda 内で `ssm:GetParameter`（`WithDecryption`）。IAM に `ssm:GetParameter` を追加。

ハッカソン MVP では **Lambda 環境変数だけ** でも可（時間優先）。

## IAM

- root 不使用
- Lambda 実行ロール: `bedrock:InvokeModel` のみ最小付与
- 開発者 PC: デプロイ用 IAM ユーザー（事前準備）

## beforeSubmitPrompt / Git

Hook で `.env` コミット防止を推奨（別途 [create-hook skill] 参照）。

## 品質チェック

- [ ] `git diff` に `.env` が無い
- [ ] コード検索で `sk-`, `AKIA`, `gho_` がヒットしない
- [ ] フロント bundle に AWS シークレットが無い
