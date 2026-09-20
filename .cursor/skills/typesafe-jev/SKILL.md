---
name: typesafe-jev
description: >-
  TypeSafe の System One モデル Jev を FastAPI から呼ぶ実装手順。
  Choice / Score / Noul、typesafe-sdk、TYPESAFE_API_KEY、構造化判定。
  Jev、TypeSafe、typesafe.ai、System One、判断の確率をコードで使う依頼で使う。
  写真解析や Gemini の置き換えには使わない。
---

# TypeSafe Jev の実装

Jev は文章と構造化 state に対し、Choice / Score / Noul の型付き判定と確率を返す。テキスト生成や JSON のパースはしない。ワークフローはコードが持つ。

**実装の直前にライブ文書を読む。** この skill は方向と、このリポジトリの境界だけを持つ。エンドポイント、SDK のメソッド、モデル ID、制限は文書が正。記憶でフィールドを足さない。

索引: https://docs.typesafe.ai/llms.txt  
ページはパス末尾に `.md` を付けると Markdown になる（例: https://docs.typesafe.ai/api.md ）。

## 公式 URL

| 用途 | URL |
|------|-----|
| 導入 | https://docs.typesafe.ai/introduction |
| 索引 | https://docs.typesafe.ai/llms.txt |
| Quick start | https://docs.typesafe.ai/introduction/quickstart |
| System One | https://docs.typesafe.ai/concepts/system-one |
| 作り方 | https://docs.typesafe.ai/concepts/how-to-build-with-system-one |
| State | https://docs.typesafe.ai/concepts/state |
| プリミティブ | https://docs.typesafe.ai/primitives |
| Choice | https://docs.typesafe.ai/primitives/choice |
| Score | https://docs.typesafe.ai/primitives/score |
| Noul | https://docs.typesafe.ai/primitives/noul |
| Confidence | https://docs.typesafe.ai/confidence |
| HTTP API | https://docs.typesafe.ai/api |
| モデル | https://docs.typesafe.ai/models |
| Python SDK | https://docs.typesafe.ai/sdk/python |
| JavaScript SDK | https://docs.typesafe.ai/sdk/javascript |
| 公式 agent skill | https://docs.typesafe.ai/agent-skill |
| 公式 SKILL.md | https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md |
| 生の SKILL.md | https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md |

詳細な写しと、実装前に開くページは [reference.md](reference.md)。

公式 skill の再インストールはしない。`npx skills add` と Claude Code プラグインは、このディレクトリと二重になる。更新するときは索引と [agent skill](https://docs.typesafe.ai/agent-skill) を読み、この skill の手順が古ければ直す。

## このリポジトリの境界

- 大会の必須 AI は Gemini。Jev は置き換えない。写真の解析はサーバーの Gemini だけ。
- Jev の入力はテキストだけ。画像・音声・動画は送れない。写真はテキストに落としてから state に入れる。
- 呼び出しは FastAPI（`apps/api`）だけ。ブラウザ、`NEXT_PUBLIC_*`、Next.js のクライアントから呼ばない。
- キー名は `TYPESAFE_API_KEY`。実値は `.env` と Cloud Run の環境変数だけ。Git、ログ、レスポンス、チャットに書かない。`Authorization` は失敗ログでもマスクする。
- 実装するときは `docs/deploy/env-contract.md` と `.env.example` にキー名だけ足す。実値は書かない。
- 公開 JSON は snake_case。エラーは `{ "error": { "code", "message" } }`。秘密とスタックトレースは入れない。
- ユーザーが Jev をデモ経路に足すと明示するまで、写真→層・関節→出典の流れは変えない。

## ワークフロー

```
Task Progress:
- [ ] Step 1: ライブ文書を読む
- [ ] Step 2: 判定を質問に分解する
- [ ] Step 3: サーバーだけから呼ぶ
- [ ] Step 4: 確率はコードで合成する
- [ ] Step 5: 失敗と秘密を確認する
```

### Step 1: ライブ文書

1. https://docs.typesafe.ai/llms.txt で該当ページを選ぶ。
2. HTTP か Python SDK のページと、使うプリミティブのページを読む。
3. 近い cookbook があればそれも読む。閾値の例は普遍の規則にしない。

### Step 2: 質問

欲しい画面の動作から、必要な判定だけを逆算する。計算、完全一致、実行はコードに残す。

| 欲しい答え | 型 | 戻り |
|------------|----|------|
| 定義した候補から 1 つ | Choice | `choice`, `probabilities`, `confidence` |
| 順序のある度合い | Score | `score`, `probabilities`, `confidence` |
| はい / いいえの確率 | Noul | `noul`（0〜1）。別の confidence は無い |

- 1 問は 1 つの狭い判定。独立した軸は分け、コードで重みを付ける。
- 同じ state の独立した質問は 1 リクエストにまとめる。質問同士は答えを見ない。
- 先の答えで次の候補や証拠が変わるときだけ、2 回目を呼ぶ。
- 質問 ID はコード用。モデルには送られない。意味は `instructions` と `criteria` に全部書く。
- 該当なしがあり得る Choice には、その選択肢を入れる。
- 候補に無い値は選べない。出典 URL などの原文はコードが候補を作り、Jev は選ぶだけにする。

### Step 3: 呼び出し

API 側の Python を既定にする。Python は 3.10 以上。パッケージは `typesafe-sdk`。

```bash
apps/api/.venv/Scripts/python -m pip install typesafe-sdk
```

クライアントは環境変数 `TYPESAFE_API_KEY` を読む。既定モデルは `jev-latest`。ベース URL の既定は `https://api.typesafe.ai`。評価は `POST /v1/systemone`。

実装直前の SDK ページの例に合わせる。Quick start は `response.answers`、Python SDK ページは `response.nouls` / `choices` / `scores` を例にしている。どちらが今の戻りか、読んだページで確認する。

```python
from typesafe_sdk import Noul, TypeSafeClient, TypeSafeError

def judge_claim(text: str) -> float | None:
    """出典本文が主張を支えている確率。失敗時は None。"""
    if not text.strip():
        return None
    try:
        with TypeSafeClient() as client:
            response = client.system_one(
                state={"passage": text},
                questions={
                    "supports_claim": Noul(
                        instructions="本文は、渡した主張を直接支えている",
                    ),
                },
            )
        return response.answers["supports_claim"].noul
    except TypeSafeError:
        # 本文とキーはログに出さない。上位へは業務エラーかシステムエラーを区別して渡す。
        raise
```

タイムアウトとリトライは SDK の既定を使う。HTTP を自前で書くときだけ、429 と 529 は指数バックオフにする。外部呼び出しは try-catch する。

JavaScript SDK（`@typesafe-ai/sdk`、Node.js 20 以上）は、どうしても TypeScript のサーバーで呼ぶときだけ。ブラウザバンドルに入れない。

### Step 4: 合成

- Choice / Score の `confidence` は分布の集中度であり、処理全体が正しい許可ではない。
- Noul が 0.5 付近は、はい/いいえが拮抗している。強さの中間ではない。
- 閾値は利用者のデータで決める。cookbook の数値を固定値にしない。
- 重みと閾値は 1 ファイルにまとめる。質問文も同じ場所に置く。
- 型が付いていることは、内容が真実であることではない。

### Step 5: 確認

- キーがレスポンス、ログ、`NEXT_PUBLIC_*`、Git に無い。
- 写真バイナリを state に入れていない。
- Gemini の経路が残っている。
- 代表例で、欠けた証拠・モデルの誤り・コードの誤り・通信失敗を分けて見る。

## 失敗

| 状態 | 意味 |
|------|------|
| 401 | キーが無い、または無効。値はログに出さない |
| 422 | 質問または body が不正 |
| 429 | レート制限。SDK なら既定の再試行 |
| 529 | 過負荷。待って再試行 |

業務エラー（空の入力）は利用者向けの `error.message` を返す。通信失敗と 5xx は上位へ送る。詳細は [reference.md](reference.md)。
