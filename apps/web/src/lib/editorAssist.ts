/** 編集者向けの危険度・引用メモ・書き出し。法的断定はしない。 */

import type { ChatTurn, Lookup, LookupSource, MaterialKind, Source } from "@/lib/api";

export type RiskLevel = "easy" | "conditional" | "review";

export type CheckAnswer = "yes" | "no" | "unknown";

export type SourceChecklist = {
  needs_credit: CheckAnswer;
  allow_modify: CheckAnswer;
  commercial: CheckAnswer;
  not_confused: CheckAnswer;
};

export const EMPTY_CHECKLIST: SourceChecklist = {
  needs_credit: "unknown",
  allow_modify: "unknown",
  commercial: "unknown",
  not_confused: "unknown",
};

const EASY = /(CC0|Public Domain|パブリックドメイン)/i;
const CONDITIONAL = /(CC[-\s]?BY|Creative Commons|All rights reserved|クリエイティブ・コモンズ)/i;

const KIND_JA: Record<MaterialKind, string> = {
  own_work: "自作",
  third_party: "他者",
  web: "Web",
};

export function riskLevel(source: {
  license?: string;
  material_kind?: MaterialKind;
  risk_level?: RiskLevel;
}): RiskLevel {
  if (source.risk_level === "easy" || source.risk_level === "conditional" || source.risk_level === "review") {
    return source.risk_level;
  }
  const license = (source.license || "").trim();
  if (license === "own_claim" || (license && EASY.test(license))) {
    return "easy";
  }
  if (license && CONDITIONAL.test(license)) {
    return "conditional";
  }
  return "review";
}

export function creditMemo(
  source: {
    title?: string;
    url?: string;
    material_kind?: MaterialKind;
    license?: string;
    credit_memo?: string;
  },
  viewedAt = "",
): string {
  if (source.credit_memo?.trim()) {
    return source.credit_memo.trim();
  }
  const title = source.title?.trim() || "(無題)";
  const url = source.url?.trim() || "(URLなし)";
  const kind = source.material_kind || "web";
  const license = source.license?.trim() || "unknown";
  const when = viewedAt.trim() || new Date().toISOString();
  return [
    `タイトル: ${title}`,
    `URL: ${url}`,
    `種別: ${KIND_JA[kind] || kind}`,
    `ライセンス: ${license}`,
    `取得日: ${when}`,
  ].join("\n");
}

export function splitByOwnership<T extends { material_kind?: MaterialKind }>(
  sources: T[],
): { own: T[]; other: T[] } {
  const own: T[] = [];
  const other: T[] = [];
  for (const item of sources) {
    if (item.material_kind === "own_work") {
      own.push(item);
    } else {
      other.push(item);
    }
  }
  return { own, other };
}

export function kindCounts(sources: { material_kind?: MaterialKind }[]): string {
  let own = 0;
  let other = 0;
  for (const item of sources) {
    if (item.material_kind === "own_work") {
      own += 1;
    } else {
      other += 1;
    }
  }
  return `自作${own} / 他者${other}`;
}

export function formatViewedAt(iso: string | undefined): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("ja-JP", { hour12: false });
}

export function isFavoriteCandidate(
  source: { url?: string; license?: string; material_kind?: MaterialKind; risk_level?: RiskLevel },
  checklist: SourceChecklist,
): boolean {
  if (riskLevel(source) !== "easy") {
    return false;
  }
  return (
    checklist.needs_credit !== "unknown" &&
    checklist.allow_modify !== "unknown" &&
    checklist.commercial !== "unknown" &&
    checklist.not_confused !== "unknown"
  );
}

export function buildExportMarkdown(
  history: Lookup[],
  chatHistory: ChatTurn[],
  checks: Record<string, SourceChecklist>,
  objectLabels: Record<string, string>,
  favorites: Record<string, true> = {},
  notes: Record<string, string> = {},
): string {
  const lines: string[] = ["# 制作ログ（出典下書き）", "", "> 目安です。法的な断定ではありません。", ""];

  const favoriteUrls = Object.keys(favorites).filter((url) => favorites[url]);
  if (favoriteUrls.length) {
    lines.push("## お気に入り", "");
    for (const url of favoriteUrls) {
      const note = (notes[url] || "").trim();
      lines.push(`- ${url}${note ? ` — ${note}` : ""}`);
    }
    lines.push("");
  }

  if (history.length) {
    lines.push("## 自動検索", "");
    for (const turn of history) {
      const label = turn.object_label || objectLabels[turn.object_id] || turn.object_id;
      lines.push(`### ${label} · ${formatViewedAt(turn.viewed_at)}`);
      lines.push("");
      lines.push(turn.summary || "");
      lines.push("");
      for (const source of turn.sources) {
        lines.push(..._sourceBlock(source, turn.viewed_at, checks, notes));
      }
    }
  }

  if (chatHistory.length) {
    lines.push("## チャット判断", "");
    for (const turn of chatHistory) {
      const label = turn.object_label || objectLabels[turn.object_id] || turn.object_id;
      lines.push(`### ${label} · ${formatViewedAt(turn.viewed_at)}`);
      lines.push("");
      lines.push(`質問: ${turn.message}`);
      lines.push("");
      lines.push(turn.answer || "");
      lines.push("");
      for (const source of turn.sources) {
        lines.push(..._sourceBlock(source, turn.viewed_at, checks, notes));
      }
    }
  }

  return `${lines.join("\n").trim()}\n`;
}

function _sourceBlock(
  source: LookupSource | Source,
  viewedAt: string | undefined,
  checks: Record<string, SourceChecklist>,
  notes: Record<string, string>,
): string[] {
  const key = source.url || source.title || "";
  const check = checks[key] || EMPTY_CHECKLIST;
  const license = "license" in source ? source.license : "unknown";
  const note = (notes[key] || "").trim();
  const block = [
    "```",
    creditMemo({ ...source, license }, viewedAt || ""),
    `危険度目安: ${riskLevel({ ...source, license })}`,
    `チェック: クレジット=${check.needs_credit} / 改変=${check.allow_modify} / 商用=${check.commercial} / 混同なし=${check.not_confused}`,
  ];
  if (note) {
    block.push(`メモ: ${note}`);
  }
  block.push("```", "");
  return block;
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export function downloadText(filename: string, body: string): void {
  const blob = new Blob([body], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
