/**
 * 秘匿情報検知 — guard-secrets-prompt / guard-shell 共通
 */
"use strict";

const fs = require("fs");
const path = require("path");

const CONFIG_PATH = path.join(process.cwd(), ".cursor", "hooks", "secrets.config.json");

const DEFAULT_CONFIG = {
  promptPatterns: [],
  promptAllowSubstrings: [".env.example", "YOUR_API_KEY", "{TODO}"],
  shellBlockPatterns: [],
};

function readStdinSync() {
  if (process.stdin.isTTY) return "";
  try {
    return fs.readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      return { ...DEFAULT_CONFIG, ...JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8")) };
    }
  } catch {
    /* ignore */
  }
  return DEFAULT_CONFIG;
}

function isAllowedPrompt(text, config) {
  const allows = config.promptAllowSubstrings || [];
  return allows.some((s) => text.includes(s));
}

function scanPrompt(text, config) {
  if (!text || isAllowedPrompt(text, config)) return null;

  for (const rule of config.promptPatterns || []) {
    try {
      const re = new RegExp(rule.pattern, "i");
      if (re.test(text)) {
        return rule;
      }
    } catch {
      /* invalid pattern */
    }
  }
  return null;
}

function scanShell(command, config) {
  if (!command) return null;

  for (const rule of config.shellBlockPatterns || []) {
    try {
      const re = new RegExp(rule.pattern, "i");
      if (re.test(command)) {
        return rule;
      }
    } catch {
      /* invalid pattern */
    }
  }
  return null;
}

function output(obj) {
  process.stdout.write(`${JSON.stringify(obj)}\n`);
}

module.exports = {
  readStdinSync,
  loadConfig,
  scanPrompt,
  scanShell,
  output,
};
