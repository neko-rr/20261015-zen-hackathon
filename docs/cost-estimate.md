# 費用の試算

取得日: **2026-10-15**。金額は公式ページの USD。円は請求通貨のレートで変わり、ここでは換算しない。モデル ID は `GEMINI_MODEL`（リポジトリには書かない）。下の Gemini は **Flash 系の導入単価を仮置き**したときの上限感である。大きいモデルなら公式表の方が高い。

審査から 2026-12-01 まで、最小インスタンス 0、GPU なし、RAG Engine なし、という前提。

## 公式の単価

- [Cloud Run](https://cloud.google.com/run/pricing): リクエスト課金はアクティブな vCPU 秒 $0.000024、GiB 秒 $0.0000025、100万リクエスト $0.40。月の無料枠は 180,000 vCPU 秒、360,000 GiB 秒、200万リクエスト。アイドル（最小台数を置かないとき）は $0
- [Agent Platform の Gemini](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing): Flash 系（3.8 / 3.7 / 3.6、global）は 2026-12-31 まで入力 $0.75 / 100万トークン、出力 $3.75 / 100万。2027-01-01 から $1.50 / $7.50
- [Google Search grounding](https://ai.google.dev/gemini-api/docs/pricing): 月 5,000 検索まで無料。超過は 1,000 あたり $14（モデル世代で表が分かれる。実装時のモデルの行を見る）
- [Cloud Vision Web Detection](https://cloud.google.com/vision/pricing): 月 1,000 ユニットまで無料。次は 1,000 あたり $3.50
- [Speech-to-Text V2](https://cloud.google.com/speech-to-text/pricing): 標準の最初の区分は 1 分 $0.016
- [Firestore](https://cloud.google.com/firestore/pricing): 1日あたり読み 50,000、書き 20,000、削除 20,000、保存 1 GiB が無料
- [Cloud Storage](https://cloud.google.com/storage/pricing): Standard は月 5 GiB まで無料。大阪（asia-northeast2）の超過単価は同ページの地域表

## 審査規模の仮置き

| 操作 | 回数 | 課金の見方 |
|------|------|------------|
| 写真の解析 | 200 | API を 1 vCPU・1 GiB・1回 10 秒と置くと 2,000 vCPU 秒、2,000 GiB 秒 |
| 画面の短い応答 | 数千 | リクエスト数は 200万の無料枠の内側 |
| 出典（Gemini） | 100 | 1回あたり入力 2万・出力 1千トークンと置く |
| 類似画像（Vision） | 200 | 月 1,000 の無料枠の内側 |
| 音声ポーズ | 30本 × 10秒 | 合計 5 分 |
| 保存 | 写真数 GiB 未満 | Storage の 5 GiB-月、Firestore の日次無料枠の内側 |

## この仮置きでの金額

- **Cloud Run: $0。** 2,000 vCPU 秒は無料枠 180,000 の約 1%。最小台数を 1 にすると、使っていなくても vCPU 秒が積み上がる
- **Vision・Storage・Firestore: $0。** いずれも上の回数なら無料枠の内側
- **Google Search grounding: 無料とは断定しない。** 5,000 回までの無料は [Gemini API の料金ページ](https://ai.google.dev/gemini-api/docs/pricing) の記載。Agent Platform 側の検索単価は 2026-10-15 に行を特定できなかった。仮置きの 100 回は、API 側の無料枠の内側ではある
- **Speech-to-Text: 約 $0.08。** 5 分 × $0.016
- **Gemini（Flash 仮置き）: 約 $1.9。** 入力 200万トークン × $0.75 = $1.50。出力 10万トークン × $3.75 = $0.375
- **Jev（TypeSafe）: この表に入れない。** 送るのは文章だけ。料金は TypeSafe 側で、2026-10-15 時点では公式の従量を未確認

合計の桁は **数ドル**。内訳のほとんどは出典のトークンで、常時起動のインフラではない。

## 上げないための実装

- 輪郭・関節・手は MediaPipe（CPU）。GPU を付けない
- よくあるポーズはコード内の一覧。その経路は Gemini を呼ばない
- 呼び方の文字だけではウェブの語検索を始めない
- RAG Engine は使わない。常時の Spanner 料金がデモに合わない（[architecture.md](architecture.md)）
- 手元資料の意味検索は `RAG_ENABLED=true` のときだけ。無効ならその分の呼び出しは無い
