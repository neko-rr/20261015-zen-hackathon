/** メモ表示用。入力の HTML はタグにせず、文字として出す。 */

const ESCAPE: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ESCAPE[char] ?? char);
}

function inline(raw: string): string {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\))/g;
  const parts: string[] = [];
  let last = 0;
  for (const match of raw.matchAll(pattern)) {
    const index = match.index ?? 0;
    parts.push(escapeHtml(raw.slice(last, index)));
    const token = match[0];
    if (token.startsWith("`")) {
      parts.push(`<code>${escapeHtml(token.slice(1, -1))}</code>`);
    } else if (token.startsWith("**")) {
      parts.push(`<strong>${escapeHtml(token.slice(2, -2))}</strong>`);
    } else if (token.startsWith("*")) {
      parts.push(`<em>${escapeHtml(token.slice(1, -1))}</em>`);
    } else {
      parts.push(
        `<a href="${escapeHtml(match[3] ?? "")}" rel="noreferrer noopener" target="_blank">${escapeHtml(match[2] ?? "")}</a>`,
      );
    }
    last = index + token.length;
  }
  parts.push(escapeHtml(raw.slice(last)));
  return parts.join("");
}

export function renderMarkdown(source: string): string {
  const lines = source.replaceAll("\r\n", "\n").split("\n");
  const html: string[] = [];
  const list: string[] = [];
  let inCode = false;
  const code: string[] = [];

  function flushList() {
    if (!list.length) {
      return;
    }
    html.push(`<ul>${list.map((item) => `<li>${inline(item)}</li>`).join("")}</ul>`);
    list.length = 0;
  }

  for (const line of lines) {
    if (line.startsWith("```")) {
      flushList();
      if (inCode) {
        html.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`);
        code.length = 0;
        inCode = false;
      } else {
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      code.push(line);
      continue;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      list.push(line.slice(2));
      continue;
    }
    flushList();
    if (line.startsWith("### ")) {
      html.push(`<h3>${inline(line.slice(4))}</h3>`);
    } else if (line.startsWith("## ")) {
      html.push(`<h2>${inline(line.slice(3))}</h2>`);
    } else if (line.startsWith("# ")) {
      html.push(`<h1>${inline(line.slice(2))}</h1>`);
    } else if (line.trim()) {
      html.push(`<p>${inline(line)}</p>`);
    }
  }
  flushList();
  if (inCode) {
    html.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`);
  }
  return html.join("");
}
