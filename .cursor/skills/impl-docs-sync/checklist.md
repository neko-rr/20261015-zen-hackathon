# 実装後ドキュメント — チェックリスト

実装完了前に、該当行だけ埋める。

## 共通

- [ ] 要約は1〜3文で言える
- [ ] `.cursor/plans/` だけに頼っていない
- [ ] 秘密・実キー・絶対パスが docs に無い
- [ ] デプロイしていない（依頼なしの場合）

## API を触った

- [ ] `docs/architecture.md` の API 表に path がある（または更新した）
- [ ] 新規フィールドは snake_case で表か節に出ている
- [ ] 所有者境界（`owner_id` / Cookie）が既存方針と矛盾しない
- [ ] エラー形を変えたなら `api_contract.mdc` と矛盾しない

## 画面・デモ手順を触った

- [ ] 操作が増えたなら `docs/demo-script.md` に1ステップ以上
- [ ] `/library` など新画面なら architecture か idea にパスが出る

## 個人補助・セッション内機能

- [ ] サーバー永続か、Studio セッション内＋書き出しかを明記
- [ ] RAG に効くもの（tags / project_id）と効かないもの（favorites / notes）を分けて書く

## 進捗

- [ ] `docs/tasks.md` の該当が現状と一致
- [ ] `docs/idea.md` の Must を広げすぎていない

## 環境

- [ ] 新キーは `docs/deploy/env-contract.md` と `.env.example`（値は空またはプレースホルダ）
