#!/usr/bin/env node
/**
 * beforeSubmitPrompt: チャットに API キー等が含まれる場合は送信をブロック
 */
"use strict";

const { readStdinSync, loadConfig, scanPrompt, output } = require("./guard-secrets-lib");

function main() {
  const raw = readStdinSync();
  if (!raw.trim()) {
    output({ continue: true });
    process.exit(0);
  }

  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    output({ continue: true });
    process.exit(0);
  }

  const text = [payload.prompt, payload.text].filter(Boolean).join("\n");
  const config = loadConfig();
  const hit = scanPrompt(text, config);

  if (hit) {
    output({
      continue: false,
      user_message:
        `秘匿情報の可能性があります（${hit.label}）。` +
        "チャットには貼らず、.env に記載してください（Git 管理外）。",
    });
    process.exit(0);
  }

  output({ continue: true });
  process.exit(0);
}

main();
