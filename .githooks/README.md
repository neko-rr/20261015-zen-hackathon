# Git hooks

コミット前に、ステージされた `.env` と鍵らしい行を拒否する。

各マシンで一度だけ（エージェントは `git config` を実行しない）:

```powershell
git config core.hooksPath .githooks
```

未設定や `--no-verify` では効かない。公開前に `git status` で `.env` が無いことを見る。
