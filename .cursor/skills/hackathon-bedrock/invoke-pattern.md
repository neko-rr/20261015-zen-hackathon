# Invoke 実装パターン

プロジェクトの既存ランタイムに合わせる。**新規 FW よりコピペ可能な最小実装。**

## 環境変数（Lambda）

| 変数 | 用途 |
|------|------|
| `AWS_REGION` | リージョン（Lambda では通常自動） |
| `BEDROCK_MODEL_ID` | 例: `anthropic.claude-3-haiku-20240307-v1:0` |
| `BEDROCK_MAX_TOKENS` | 任意。デフォルト 1024 |

ローカル: `.env` から読む（[security.md](security.md)）。

## Python（boto3）— 参考

```python
import json
import os
import boto3
from botocore.exceptions import ClientError

bedrock = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
MODEL_ID = os.environ["BEDROCK_MODEL_ID"]

def handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        user_text = (body.get("text") or "").strip()
        if not user_text:
            return _response(400, {"error": "invalid_input"})

        payload = _build_payload(user_text)
        resp = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(resp["body"].read())
        parsed = _parse_and_validate(result)
        return _response(200, parsed)
    except ClientError as e:
        # ログは err code のみ。入力全文は出さない
        print(f"Bedrock ClientError: {e.response['Error']['Code']}")
        return _response(200, _fallback_json())  # 審査用: 200 + フォールバック
    except Exception as e:
        print(f"Unhandled: {type(e).__name__}")
        return _response(200, _fallback_json())

def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body, ensure_ascii=False),
    }
```

`_build_payload`, `_parse_and_validate`, `_fallback_json` は [prompt-guide.md](prompt-guide.md) のスキーマに合わせて実装。

## Node.js（@aws-sdk/client-bedrock-runtime）— 参考

```javascript
import { BedrockRuntimeClient, InvokeModelCommand } from "@aws-sdk/client-bedrock-runtime";

const client = new BedrockRuntimeClient({ region: process.env.AWS_REGION });
const MODEL_ID = process.env.BEDROCK_MODEL_ID;

export const handler = async (event) => {
  try {
    const { text } = JSON.parse(event.body || "{}");
    if (!text?.trim()) return json(400, { error: "invalid_input" });

    const payload = buildPayload(text.trim());
    const cmd = new InvokeModelCommand({
      modelId: MODEL_ID,
      contentType: "application/json",
      accept: "application/json",
      body: JSON.stringify(payload),
    });
    const resp = await client.send(cmd);
    const parsed = parseAndValidate(JSON.parse(new TextDecoder().decode(resp.body)));
    return json(200, parsed);
  } catch (err) {
    console.error("Bedrock error:", err.name);
    return json(200, fallbackJson());
  }
};
```

## API Gateway

| 設定 | 推奨 |
|------|------|
| メソッド | POST |
| CORS | フロント origin |
| タイムアウト | 29s |
| 認証 | ハッカソン MVP: なし可（レート制限は Nice） |

## ローカル開発

1. `.env` に `AWS_REGION`, `BEDROCK_MODEL_ID`, 認証（profile 等）
2. `aws sts get-caller-identity` 確認
3. Lambda ローカル: SAM local / 単体スクリプトで handler 呼び出し
4. フロント: Vite proxy で `/api` → ローカル Lambda

**infra/ または AGENTS.md** に手順があればそれを優先。

## IAM（Lambda 実行ロール）

最小権限:

```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel"],
  "Resource": "arn:aws:bedrock:{region}::foundation-model/{model-id}"
}
```

## 配置

| パス | 用途 |
|------|------|
| `src/backend/` | Lambda ソース（プロジェクト標準） |
| `infra/` | SAM template.yaml（あれば） |

存在しない場合は **既存構成に合わせて** ユーザーに確認。
