# エラー処理・フォールバック

ハッカソン審査では **Bedrock 障害時も UI が動く** ことが重要。

## 方針

| 種別 | 扱い |
|------|------|
| 業務エラー（空入力・形式不正） | 400 + `{ "error": "..." }` |
| Bedrock / ネットワーク / スロットリング | ログ + **200 + フォールバック JSON** |
| システムエラー（想定外） | ログ + フォールバック（審査中は 500 よりデモ継続優先） |

審査デモ中は **画面が止まらない** を優先。本番 SaaS とは trade-off が異なる。

## リトライ

```
1回目 InvokeModel 失敗
  → Throttling / ServiceUnavailable のみ 500ms 待って 1 回リトライ
  → 再失敗 → フォールバック JSON
```

JSON パース失敗:

```
1回だけ "Return JSON only" を system に追加して再 Invoke
  → 失敗 → フォールバック
```

## フォールバック JSON

[prompt-guide.md](prompt-guide.md) の **出力スキーマと同じキー** を持つ固定値。

```json
{
  "fallback": true,
  "...": "デモ用の安全な固定値"
}
```

フロント: `fallback === true` なら「デモモード」表示（任意）。

**idea.md の Must に合わせて** 審査員が次の操作に進める値を入れる。

## よくある Bedrock エラー

| コード / 症状 | 原因 | 対処 |
|--------------|------|------|
| AccessDeniedException | IAM / Model access | コンソールで Model access 有効化 |
| ValidationException | モデル ID・リージョン不一致 | `.env` の ID とリージョン確認 |
| ThrottlingException | レート制限 | リトライ → フォールバック |
| 403 model not found | 未提供モデル | リージョン対応モデルに変更 |

## ログ

**出してよい:** エラーコード、requestId、処理時間  
**出してはいけない:** ユーザー入力全文、API キー、Authorization ヘッダ

```python
# 良い
print(f"Bedrock error: {code}, latency_ms={ms}")

# 悪い
print(f"input={user_text}, key={os.environ.get('AWS_SECRET_ACCESS_KEY')}")
```

## タイムアウト目安

| レイヤ | 目安 |
|--------|------|
| Bedrock invoke | 15〜25s |
| Lambda | 29s（API GW 上限内） |
| フロント fetch | 30s + ローディング UI |

## デモ前チェック

- [ ] 機内モード / オフライン → フォールバック or エラーメッセージ
- [ ] サンプル入力 3 件で 1 回以上成功
- [ ] 意図的にモデル ID を無効化 → フォールバックで UI 継続
