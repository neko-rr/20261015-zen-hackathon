#!/usr/bin/env node
/**
 * beforeShellExecution: .env の git add、危険な git 操作をブロック
 */
"use strict";

const { readStdinSync, loadConfig, scanShell, output } = require("./guard-secrets-lib");

function main() {
  const raw = readStdinSync();
  if (!raw.trim()) {
    output({ permission: "allow" });
    process.exit(0);
  }

  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    output({ permission: "allow" });
    process.exit(0);
  }

  const command = payload.command || "";
  const config = loadConfig();
  const hit = scanShell(command, config);

  if (hit) {
    output({
      permission: "deny",
      user_message: `このコマンドは Hook によりブロックされました: ${hit.label}`,
      agent_message:
        `${hit.label} はハッカソン中に禁止されています。` +
        " .env は Git に含めない。force push / hard reset / clean -fd は使わない。",
    });
    process.exit(0);
  }

  output({ permission: "allow" });
  process.exit(0);
}

main();
