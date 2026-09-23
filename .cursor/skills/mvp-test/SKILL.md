---
name: mvp-test
description: >-
  このリポジトリの最小テスト方針。FastAPI の pytest（業務エラーと /health）、
  デプロイ後の /health スモーク、画面は next build まで。
  「テストを書いて」「pytest」「スモーク」「next build」の依頼で使う。
  E2E・カバレッジ100%・負荷試験はハッカソンではやらない。
---

# MVP テスト方針

目的は **デモ経路が壊れていないこと**。網羅より速いフィードバック。

正本の API 形: `.cursor/rules/api_contract.mdc`  
デプロイ後確認: [cloud-run-gemini](../cloud-run-gemini/SKILL.md)

## やること（必須レベル）

| 層 | 何を | ツール |
|----|------|--------|
| API 単体 | `GET /health` が 200 と `{ "status": "ok" }` | pytest + FastAPI `TestClient` |
| API 業務 | 非対応 MIME・空・過大サイズが `{ "error": { "code", "message" } }` | 同上。Gemini は呼ばない |
| 画面ビルド | `apps/web` で型・ビルドが通る | `npm run build` |
| 本番スモーク | デプロイ後に公開 API の `/health` | `curl` またはブラウザ。キーは出さない |

## やらないこと

- Playwright / Cypress の本格 E2E（動画前の手動操作で可）
- Gemini / Jev 実呼び出しの CI（課金・揺れ。ローカル手動で十分）
- カバレッジ目標、負荷試験、ビジュアルリグレッション

## API（pytest）

配置の目安: `apps/api/tests/`（未作成なら作るときこのパス）。

```text
apps/api/
  app/
  tests/
    test_health.py
    test_photos_validation.py
  requirements.txt   # 本番用
  requirements-dev.txt  # pytest 等（任意。無ければ requirements に追記しない方針も可）
```

実行例（リポジトリ直下、Windows）:

```powershell
apps\api\.venv\Scripts\python -m pip install pytest httpx
apps\api\.venv\Scripts\python -m pytest apps\api\tests -q
```

`TestClient` は `from fastapi.testclient import TestClient`。  
`app` は `from app.main import app`（`--app-dir apps/api` 相当のパスが通っていること）。

業務エラーの期待形:

```json
{ "error": { "code": "unsupported_type", "message": "..." } }
```

秘密・スタックトレースが JSON に無いことを確認する。

## 画面（next build）

```powershell
cd apps\web
npm install
npm run build
```

失敗したら型エラーや import を直す。`npm run dev` だけの確認で提出しない。

## デプロイ後スモーク

1. [cloud-run-gemini](../cloud-run-gemini/SKILL.md) で API を出す
2. `GET {APIのURL}/health` が 200
3. 失敗ログに `Authorization` や鍵を残さない（マスク）

URL の全文を Git に固定しなくてよい（`docs/deploy/status.md` の方針）。

## エージェントへの指示

- テストを足すときは **上記の必須レベルだけ**。依頼が無い限り E2E を増やさない
- Gemini をモックせずに CI で毎回叩かない
- 実装セッションでテストコードを書くときは、この skill のパスとコマンドに合わせる

## 関連

| 用途 | パス |
|------|------|
| 提出物の作り方 | [gc-hackathon-vol5-submit](../gc-hackathon-vol5-submit/SKILL.md) |
| 適合チェック（検査） | [gc-hackathon-vol5](../gc-hackathon-vol5/SKILL.md) |
| デモ操作 | [docs/demo-script.md](../../../docs/demo-script.md) |
