"use client";

import { useState } from "react";

import { sourceHref, type LookupSource, type Source } from "@/lib/api";
import {
  EMPTY_CHECKLIST,
  copyText,
  creditMemo,
  isFavoriteCandidate,
  riskLevel,
  splitByOwnership,
  type CheckAnswer,
  type SourceChecklist,
} from "@/lib/editorAssist";
import { text, type Locale } from "@/lib/messages";

function rightLabel(locale: Locale, value: string): string {
  if (!value || value === "unknown") {
    return text(locale, "unknown");
  }
  if (value === "own_claim") {
    return text(locale, "ownClaim");
  }
  return value;
}

function materialKindLabel(locale: Locale, kind: string | undefined): string {
  if (kind === "own_work") {
    return text(locale, "kindOwn");
  }
  if (kind === "third_party") {
    return text(locale, "kindThird");
  }
  return text(locale, "kindWeb");
}

function riskLabel(locale: Locale, level: ReturnType<typeof riskLevel>): string {
  if (level === "easy") {
    return text(locale, "riskEasy");
  }
  if (level === "conditional") {
    return text(locale, "riskConditional");
  }
  return text(locale, "riskReview");
}

function percentLabel(locale: Locale, value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return text(locale, "unknown");
  }
  return `${value}%`;
}

function CheckRow({
  locale,
  label,
  value,
  onChange,
}: {
  locale: Locale;
  label: string;
  value: CheckAnswer;
  onChange: (next: CheckAnswer) => void;
}) {
  return (
    <div className="check-row">
      <span>{label}</span>
      <div className="check-options">
        {(
          [
            ["yes", "checkYes"],
            ["no", "checkNo"],
            ["unknown", "checkUnknown"],
          ] as const
        ).map(([key, messageKey]) => (
          <button
            key={key}
            type="button"
            aria-pressed={value === key}
            onClick={() => onChange(key)}
          >
            {text(locale, messageKey)}
          </button>
        ))}
      </div>
    </div>
  );
}

function SourceCard({
  locale,
  source,
  viewedAt,
  checklist,
  onChecklist,
  showFacts,
  favorited,
  onToggleFavorite,
  note,
  onNote,
}: {
  locale: Locale;
  source: LookupSource | Source;
  viewedAt?: string;
  checklist: SourceChecklist;
  onChecklist: (next: SourceChecklist) => void;
  showFacts: boolean;
  favorited: boolean;
  onToggleFavorite: () => void;
  note: string;
  onNote: (next: string) => void;
}) {
  const href = sourceHref(source.url);
  const license = ("license" in source ? source.license : "") || "unknown";
  const level = riskLevel({ ...source, license });
  const [copied, setCopied] = useState(false);
  const jev = "jev" in source ? source.jev : undefined;
  const candidate = isFavoriteCandidate({ ...source, license }, checklist);
  const canPin = Boolean(source.url);

  return (
    <article className="source">
      {href ? (
        <a href={href} target="_blank" rel="noreferrer">
          {source.title || href}
        </a>
      ) : (
        <p>{source.title || text(locale, "unknown")}</p>
      )}
      <div className="source-badges">
        <span className="badge">{materialKindLabel(locale, source.material_kind)}</span>
        <span className={`badge risk-${level}`} title={text(locale, "riskHint")}>
          {riskLabel(locale, level)}
        </span>
        {canPin ? (
          <button
            type="button"
            className={`badge favorite-btn${favorited ? " is-on" : ""}`}
            aria-pressed={favorited}
            onClick={onToggleFavorite}
          >
            {favorited ? text(locale, "favoriteUnpin") : text(locale, "favoritePin")}
          </button>
        ) : null}
      </div>
      {candidate && !favorited ? <p className="hint">{text(locale, "favoriteHint")}</p> : null}
      {showFacts && "created" in source ? (
        <div className="facts">
          <div>
            <span>{text(locale, "license")}</span>
            <span>{rightLabel(locale, source.license)}</span>
          </div>
          <div>
            <span>{text(locale, "created")}</span>
            <span>{rightLabel(locale, source.created)}</span>
          </div>
          <div>
            <span>{text(locale, "copyright")}</span>
            <span>{rightLabel(locale, source.copyright)}</span>
          </div>
        </div>
      ) : null}
      {showFacts && jev ? (
        <div className="jev">
          <p className="hint">{text(locale, "jevPercent")}</p>
          <div className="facts">
            <div>
              <span>{text(locale, "jevAbout")}</span>
              <span>{percentLabel(locale, jev.about)}</span>
            </div>
            {source.material_kind === "own_work" ? null : (
              <>
                <div>
                  <span>{text(locale, "license")}</span>
                  <span>{percentLabel(locale, jev.license)}</span>
                </div>
                <div>
                  <span>{text(locale, "created")}</span>
                  <span>{percentLabel(locale, jev.created)}</span>
                </div>
                <div>
                  <span>{text(locale, "copyright")}</span>
                  <span>{percentLabel(locale, jev.copyright)}</span>
                </div>
              </>
            )}
          </div>
        </div>
      ) : null}
      <button
        type="button"
        className="copy-credit"
        onClick={() => {
          void copyText(creditMemo({ ...source, license }, viewedAt || "")).then((ok) => {
            if (ok) {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1500);
            }
          });
        }}
      >
        {copied ? text(locale, "copied") : text(locale, "copyCredit")}
      </button>
      <div className="checklist">
        <p className="hint">{text(locale, "checklist")}</p>
        <CheckRow
          locale={locale}
          label={text(locale, "checkCredit")}
          value={checklist.needs_credit}
          onChange={(needs_credit) => onChecklist({ ...checklist, needs_credit })}
        />
        <CheckRow
          locale={locale}
          label={text(locale, "checkModify")}
          value={checklist.allow_modify}
          onChange={(allow_modify) => onChecklist({ ...checklist, allow_modify })}
        />
        <CheckRow
          locale={locale}
          label={text(locale, "checkCommercial")}
          value={checklist.commercial}
          onChange={(commercial) => onChecklist({ ...checklist, commercial })}
        />
        <CheckRow
          locale={locale}
          label={text(locale, "checkConfused")}
          value={checklist.not_confused}
          onChange={(not_confused) => onChecklist({ ...checklist, not_confused })}
        />
        <label className="source-note">
          <span className="hint">{text(locale, "sourceNote")}</span>
          <textarea
            rows={2}
            value={note}
            placeholder={text(locale, "sourceNotePlaceholder")}
            onChange={(event) => onNote(event.target.value)}
          />
        </label>
      </div>
    </article>
  );
}

export function CompareSources({
  locale,
  sources,
  viewedAt,
  checks,
  onCheck,
  showFacts,
  favorites,
  onToggleFavorite,
  notes,
  onNote,
}: {
  locale: Locale;
  sources: Array<LookupSource | Source>;
  viewedAt?: string;
  checks: Record<string, SourceChecklist>;
  onCheck: (key: string, next: SourceChecklist) => void;
  showFacts: boolean;
  favorites: Record<string, true>;
  onToggleFavorite: (url: string) => void;
  notes: Record<string, string>;
  onNote: (url: string, next: string) => void;
}) {
  const { own, other } = splitByOwnership(sources);

  function renderColumn(title: string, items: Array<LookupSource | Source>) {
    return (
      <div className="compare-col">
        <h4>{title}</h4>
        {items.length === 0 ? <p className="hint">{text(locale, "compareEmpty")}</p> : null}
        {items.map((source) => {
          const key = source.url || source.title || "";
          return (
            <SourceCard
              key={key}
              locale={locale}
              source={source}
              viewedAt={viewedAt}
              checklist={checks[key] || EMPTY_CHECKLIST}
              onChecklist={(next) => onCheck(key, next)}
              showFacts={showFacts}
              favorited={Boolean(source.url && favorites[source.url])}
              onToggleFavorite={() => {
                if (source.url) {
                  onToggleFavorite(source.url);
                }
              }}
              note={source.url ? notes[source.url] || "" : ""}
              onNote={(next) => {
                if (source.url) {
                  onNote(source.url, next);
                }
              }}
            />
          );
        })}
      </div>
    );
  }

  return (
    <div className="compare-grid">
      {renderColumn(text(locale, "compareOwn"), own)}
      {renderColumn(text(locale, "compareOther"), other)}
    </div>
  );
}
