#!/usr/bin/env node
/**
 * afterFileEdit Hook: 編集ファイルを自動フォーマット。
 * - JS/TS/CSS: Prettier / ESLint --fix
 * - Python: black / ruff check --fix
 * ツール未設定時はスキップ（fail open）。設定は format.config.json。
 */
"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT = process.cwd();
const CONFIG_PATH = path.join(ROOT, ".cursor", "hooks", "format.config.json");

const DEFAULT_CONFIG = {
  includePathPrefixes: ["src/frontend/", "src/backend/", "frontend/", "backend/", "src/"],
  extensions: [".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".json", ".py"],
  excludePathContains: ["node_modules/", "dist/", "build/", ".venv/", "venv/", "__pycache__/"],
  runPrettier: true,
  runEslintFix: true,
  runBlack: true,
  runRuffFix: true,
};

function log(msg) {
  process.stderr.write(`[format-after-edit] ${msg}\n`);
}

function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      return { ...DEFAULT_CONFIG, ...JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8")) };
    }
  } catch (e) {
    log(`config read error: ${e.message}`);
  }
  return DEFAULT_CONFIG;
}

function readStdinSync() {
  if (process.stdin.isTTY) return "";
  try {
    return fs.readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function normalizePath(p) {
  return p.replace(/\\/g, "/").replace(/^\.\//, "");
}

function extractFilePaths(payload) {
  const paths = new Set();
  if (!payload || typeof payload !== "object") return paths;

  for (const key of ["file_path", "filePath", "path", "file"]) {
    if (typeof payload[key] === "string" && payload[key]) paths.add(normalizePath(payload[key]));
  }
  if (Array.isArray(payload.files)) {
    for (const f of payload.files) {
      if (typeof f === "string") paths.add(normalizePath(f));
      else if (f?.path) paths.add(normalizePath(f.path));
    }
  }
  if (Array.isArray(payload.edits)) {
    for (const e of payload.edits) {
      if (e?.path) paths.add(normalizePath(e.path));
      if (e?.file_path) paths.add(normalizePath(e.file_path));
    }
  }
  return paths;
}

function shouldFormat(filePath, config) {
  const norm = normalizePath(filePath);
  if (config.excludePathContains.some((x) => norm.includes(x))) return false;
  const ext = path.extname(norm).toLowerCase();
  if (!config.extensions.includes(ext)) return false;
  const prefixes = config.includePathPrefixes || [];
  if (prefixes.length === 0) return true;
  return prefixes.some((prefix) => norm.startsWith(prefix) || norm.includes(`/${prefix}`));
}

function findNodeRoot(startDir) {
  let dir = startDir;
  while (dir && (dir === ROOT || dir.startsWith(ROOT))) {
    if (fs.existsSync(path.join(dir, "package.json"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return ROOT;
}

function findPythonRoot(startDir) {
  let dir = startDir;
  while (dir && (dir === ROOT || dir.startsWith(ROOT))) {
    if (fs.existsSync(path.join(dir, "pyproject.toml"))) return dir;
    if (fs.existsSync(path.join(dir, "setup.cfg"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  const backend = path.join(ROOT, "src", "backend");
  if (startDir.startsWith(backend) && fs.existsSync(backend)) return backend;
  return ROOT;
}

function run(cmd, args, cwd) {
  const result = spawnSync(cmd, args, {
    cwd,
    stdio: "pipe",
    shell: process.platform === "win32",
    encoding: "utf8",
  });
  if (result.status !== 0) {
    log(`${cmd} ${args.join(" ")} failed: ${(result.stderr || "").trim().slice(0, 200)}`);
    return false;
  }
  return true;
}

function commandOk(cmd, args, cwd) {
  return spawnSync(cmd, args, { cwd, stdio: "ignore", shell: process.platform === "win32" }).status === 0;
}

function resolvePython(cwd) {
  for (const py of ["python", "py", "python3"]) {
    if (commandOk(py, ["--version"], cwd)) return py;
  }
  return null;
}

function hasPrettier(nodeRoot) {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(nodeRoot, "package.json"), "utf8"));
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };
    if (deps.prettier) return true;
  } catch {
    /* ignore */
  }
  return [".prettierrc", ".prettierrc.json", "prettier.config.js"].some((n) =>
    fs.existsSync(path.join(nodeRoot, n))
  );
}

function hasEslint(nodeRoot) {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(nodeRoot, "package.json"), "utf8"));
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };
    if (deps.eslint) return true;
  } catch {
    /* ignore */
  }
  return ["eslint.config.js", "eslint.config.mjs", ".eslintrc.json"].some((n) =>
    fs.existsSync(path.join(nodeRoot, n))
  );
}

function canRunBlack(python, cwd) {
  return commandOk(python, ["-m", "black", "--version"], cwd);
}

function canRunRuff(python, cwd) {
  return commandOk(python, ["-m", "ruff", "--version"], cwd);
}

function formatJs(absPath, rel, config) {
  const nodeRoot = findNodeRoot(path.dirname(absPath));
  const relFromRoot = path.relative(nodeRoot, absPath);

  if (config.runPrettier && hasPrettier(nodeRoot)) {
    if (run("npx", ["prettier", "--write", relFromRoot], nodeRoot)) log(`prettier: ${rel}`);
  }

  const ext = path.extname(absPath).toLowerCase();
  if (config.runEslintFix && hasEslint(nodeRoot) && [".js", ".jsx", ".ts", ".tsx"].includes(ext)) {
    if (run("npx", ["eslint", "--fix", relFromRoot], nodeRoot)) log(`eslint --fix: ${rel}`);
  }
}

function formatPy(absPath, rel, config) {
  const pyRoot = findPythonRoot(path.dirname(absPath));
  const python = resolvePython(pyRoot);
  if (!python) {
    log(`skip python (interpreter not found): ${rel}`);
    return;
  }
  const relFromRoot = path.relative(pyRoot, absPath);

  if (config.runBlack && canRunBlack(python, pyRoot)) {
    if (run(python, ["-m", "black", relFromRoot], pyRoot)) log(`black: ${rel}`);
  } else if (config.runBlack) {
    log(`skip black (pip install black): ${path.relative(ROOT, pyRoot) || "."}`);
  }

  if (config.runRuffFix && canRunRuff(python, pyRoot)) {
    if (run(python, ["-m", "ruff", "check", "--fix", relFromRoot], pyRoot)) log(`ruff: ${rel}`);
  }
}

function formatFile(absPath, config) {
  if (!fs.existsSync(absPath)) {
    log(`skip (missing): ${absPath}`);
    return;
  }

  const rel = normalizePath(path.relative(ROOT, absPath));
  if (!shouldFormat(rel, config)) {
    log(`skip (pattern): ${rel}`);
    return;
  }

  const ext = path.extname(absPath).toLowerCase();
  if (ext === ".py") formatPy(absPath, rel, config);
  else formatJs(absPath, rel, config);
}

function main() {
  const raw = readStdinSync();
  const config = loadConfig();

  if (!raw.trim()) process.exit(0);

  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    log("stdin is not JSON; exit 0");
    process.exit(0);
  }

  const filePaths = extractFilePaths(payload);
  if (filePaths.size === 0) {
    log("no file paths in payload");
    process.exit(0);
  }

  for (const rel of filePaths) {
    const abs = path.isAbsolute(rel) ? rel : path.join(ROOT, rel);
    formatFile(abs, config);
  }

  process.exit(0);
}

main();
