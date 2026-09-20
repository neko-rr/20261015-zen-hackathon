# 01 — 絵描きの資料補助

| ID | `01` |
| ステータス | `selected` |

## 一言ピッチ

絵描きが写真資料を物体の層と関節に分け、選んだ部分を出典付きで調べ、引用に使える履歴を残せる。

## 課題とユーザー

- 対象ユーザー: イラストを描く人
- 解決する課題: 写真の構造（層・筋肉・骨格・関節）が分からず、調べた資料の出典・ライセンス・時期も後から辿れない
- 現状の代替手段と、その不満: 既存は骨格線・3D人形・線画化が中心で、言葉の解説と出典管理が弱い。詳細な競合メモは非公開フォルダ（リポジトリ外）に退避済み

## 差別化ポイント

- 絵は生成しない。層・関節・筋肉の見方と、出典付きの説明を返す
- 出典のライセンス・作成時期・著作権は、ページに書いてある範囲だけ記録する。不明は不明のまま残す
- その履歴を、完成後の引用と、資料をどこまで絵に反映したかの判断に使う

## エージェント

- 観察 → 判断 → 行動: 写真を物体ごとに分け、人や動物なら関節（できれば筋肉・骨格）を示す。選んだ物体を検索し、出典・ライセンス・時期を履歴に書く
- 制御・監査・セキュリティ: ライセンスを推測で埋めない。本はユーザーが自分で持っている PDF だけを入れる。こちらから本をダウンロードしない。非公式な Kindle 取得はしない。アップロード画像の保存期間は未決

## 実現構成

- 実行プロダクト（必須リストから 1 つ以上）: Cloud Run
- AI 技術（必須リストから 1 つ以上）: Gemini API（画像の読み取り）。ウェブの調べものは [Grounding with Google Search](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/grounding/grounding-with-google-search)。手元の PDF は [RAG Engine](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/rag-quickstart) に入れる
- 構成: 写真を上げる → 物体レイヤーと関節を表示 → 選んだ物体を検索 → 出典・ライセンス・時期を履歴に残す

## スコープ

### MVP（必須）

- [ ] 写真を1枚アップロードできる。サンプル写真ならログイン不要
- [ ] 物体ごとに分け、レイヤーの表示を切り替えられる
- [ ] 人、または動物の主対象に、関節が分かる表示を重ねる
- [ ] 選んだ物体を自然言語で調べ、出典 URL 付きで短く返す
- [ ] 出典ごとに、ライセンス・作成時期・著作権の記載を抜き、履歴に残す。ページに無い項目は「未確認」

### 時間が余ったら

- 人の主要筋肉と骨格のラベル
- 動物の筋肉・骨格
- 描き上がった絵と資料を並べ、反映度のメモを履歴に残す
- ユーザーが持っている PDF（ダウンロード済みの本を含む）を RAG に入れ、選んだ物体に合うページをファイル名とページ付きで提案する。製品名の KLM は無い。体験が近いのは NotebookLM。アプリに組み込むのは RAG Engine。NotebookLM Enterprise は PDF 投入の API はあるが、2026-05 時点で問い合わせ API は公開フォーラムで未確認（[議論](https://discuss.google.dev/t/notebooklm-enterprise-api-missing-query-chat-endpoint-for-rag-orchestration/366875)）

### 今回はやらない

- 完成イラストの生成、線画化、描画ソフト本体
- Kindle 本棚の自動連携。公式 API はプロフィールまでで、蔵書は取れない（[Login with Amazon](https://developer.amazon.com/docs/login-with-amazon/customer-profile-other-platforms-cbl-docs.html)）。非公式クライアントは規約違反の可能性がある（[kindle-api](https://github.com/transitive-bullshit/kindle-api)）
- こちらからの書籍ダウンロード。入れる PDF はユーザーが権利を持つファイルだけ
- NotebookLM の非公式クライアント
