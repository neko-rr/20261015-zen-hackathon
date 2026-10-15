"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, saveProjectMemo, type Project } from "@/lib/api";
import { renderMarkdown } from "@/lib/markdown";
import { text, type Locale } from "@/lib/messages";

type Props = {
  locale: Locale;
  project: Project;
  onSaved: (project: Project) => void;
};

export function ProjectMemo({ locale, project, onSaved }: Props) {
  const [draft, setDraft] = useState(project.memo ?? "");
  const [preview, setPreview] = useState(false);
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const baseline = useRef(project.memo ?? "");

  useEffect(() => {
    const incoming = project.memo ?? "";
    setDraft(incoming);
    setNotice("");
    setPreview(false);
    baseline.current = incoming;
  }, [project.project_id]);

  useEffect(() => {
    const incoming = project.memo ?? "";
    if (incoming === baseline.current) {
      return;
    }
    if (draft === baseline.current) {
      setDraft(incoming);
      baseline.current = incoming;
      setNotice(text(locale, "memoGenerated"));
      return;
    }
    setNotice(text(locale, "memoGeneratedDraft"));
  }, [project.memo, project.project_id, draft, locale]);

  async function onSave() {
    setSaving(true);
    setNotice("");
    try {
      const saved = await saveProjectMemo(project.project_id, draft);
      onSaved(saved);
      baseline.current = saved.memo ?? "";
      setNotice(text(locale, "memoSaved"));
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : text(locale, "memoFailed");
      setNotice(message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="project-memo" aria-label={text(locale, "memoLabel")}>
      <p className="hint">{text(locale, "memoLabel")}</p>
      <p className="hint">{text(locale, "memoHint")}</p>
      {preview ? (
        <div
          className="markdown-body"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(draft) }}
        />
      ) : (
        <textarea
          value={draft}
          maxLength={20000}
          rows={8}
          placeholder={text(locale, "memoPlaceholder")}
          onChange={(event) => setDraft(event.target.value)}
        />
      )}
      <div className="memo-actions">
        <button type="button" onClick={() => setPreview((open) => !open)}>
          {preview ? text(locale, "memoEdit") : text(locale, "memoPreview")}
        </button>
        <button type="button" onClick={() => void onSave()} disabled={saving || draft === (project.memo ?? "")}>
          {text(locale, "memoSave")}
        </button>
      </div>
      {notice ? <p className="hint">{notice}</p> : null}
    </section>
  );
}
