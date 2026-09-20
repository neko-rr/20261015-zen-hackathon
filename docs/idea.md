# 採用アイデア

> 候補の詳細は [ideas/01-photo-structure-for-illustrators.md](ideas/01-photo-structure-for-illustrators.md)。比較は [ideas/comparison.md](ideas/comparison.md)。

| ステータス | 採用 |
| 採用案 | [01 絵描きの資料補助](ideas/01-photo-structure-for-illustrators.md) |
| 決定日 | 2026-09-19 |
| 決定理由 | この案で進める。層分け・出典・ライセンス履歴を足した |

## 一言ピッチ

絵描きが写真資料を物体の層と関節に分け、選んだ部分を出典付きで調べ、引用に使える履歴を残せる。

## MVP（Must）

- 写真を1枚アップロードできる。サンプル写真ならログイン不要
- 物体ごとに分け、レイヤーの表示を切り替えられる
- 人、または動物の主対象に、関節が分かる表示を重ねる
- 選んだ物体を自然言語で調べ、出典 URL 付きで短く返す
- 出典ごとに、ライセンス・作成時期・著作権の記載を抜き、履歴に残す。ページに無い項目は「未確認」

## 技術スタック

- 実行プロダクト: Cloud Run
- AI: Gemini（写真の層と関節、検索の出典 URL）。Jev（枠を出すか、引用がライセンス等を書いているか）
- 手元の PDF: Vertex AI RAG Engine。NotebookLM は似た体験だが、組み込み用の問い合わせ API は未確認
- 構成: [architecture.md](architecture.md)。画面と API は別の Cloud Run。Gemini は API だけ

## 今回はやらない

- 完成イラストの生成
- Kindle 本棚の自動取得（公式 API では蔵書を読めない。非公式取得はしない）
- こちらからの書籍ダウンロード。NotebookLM の非公式クライアント

## 後回し

- 筋肉・骨格の詳細、動物の解剖、描いた絵との反映度
- ユーザーが持っている PDF を RAG に入れ、合うページをファイル名とページ付きで提案する
