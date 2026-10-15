"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AccountGate, SignedIn } from "@/components/AccountGate";
import { hydrateAccountPrefs, LOCALE_KEY } from "@/lib/accountPrefs";
import {
  ApiError,
  createProject,
  deleteMaterial,
  deleteProject,
  currentSession,
  listMaterials,
  listProjects,
  patchMaterial,
  uploadMaterials,
  type Material,
  type Project,
  type SessionInfo,
} from "@/lib/api";
import { sanitizeLocale, text, type Locale } from "@/lib/messages";

const ACCEPT =
  ".jpg,.jpeg,.png,.webp,.pdf,.docx,.xlsx,.md,.txt,image/jpeg,image/png,image/webp,application/pdf,text/plain,text/markdown";

function DropZone({
  locale,
  kind,
  busy,
  onFiles,
}: {
  locale: Locale;
  kind: "own_work" | "third_party";
  busy: boolean;
  onFiles: (kind: "own_work" | "third_party", files: File[]) => void;
}) {
  const [active, setActive] = useState(false);
  const title = kind === "own_work" ? text(locale, "dropOwn") : text(locale, "dropThird");
  const hint = kind === "own_work" ? text(locale, "dropOwnHint") : text(locale, "dropThirdHint");

  return (
    <label
      className={`drop-zone${active ? " is-active" : ""}${kind === "own_work" ? " is-own" : " is-third"}`}
      onDragEnter={(event) => {
        event.preventDefault();
        setActive(true);
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={() => setActive(false)}
      onDrop={(event) => {
        event.preventDefault();
        setActive(false);
        if (busy) {
          return;
        }
        const files = Array.from(event.dataTransfer.files || []);
        if (files.length) {
          onFiles(kind, files);
        }
      }}
    >
      <input
        type="file"
        multiple
        accept={ACCEPT}
        disabled={busy}
        hidden
        onChange={(event) => {
          const files = Array.from(event.target.files || []);
          event.target.value = "";
          if (files.length) {
            onFiles(kind, files);
          }
        }}
      />
      <strong>{title}</strong>
      <span className="hint">{hint}</span>
    </label>
  );
}

function parseTags(raw: string): string[] {
  return raw
    .split(/[,、]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function LibraryPage() {
  const [locale, setLocale] = useState<Locale>("ja");
  const [sessionChecked, setSessionChecked] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
  const [accountName, setAccountName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [materials, setMaterials] = useState<Material[]>([]);
  const [knownTags, setKnownTags] = useState<string[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [filterProjectId, setFilterProjectId] = useState("");
  const [uploadProjectId, setUploadProjectId] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [tagDrafts, setTagDrafts] = useState<Record<string, string>>({});

  const projectNameById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const item of projects) {
      map[item.project_id] = item.name;
    }
    return map;
  }, [projects]);

  const refresh = useCallback(async (projectId = filterProjectId) => {
    const [materialBody, projectItems] = await Promise.all([
      listMaterials(projectId),
      listProjects(),
    ]);
    setMaterials(materialBody.materials);
    setKnownTags(materialBody.tags);
    setProjects(projectItems);
    setTagDrafts((prev) => {
      const next = { ...prev };
      for (const item of materialBody.materials) {
        if (next[item.doc_id] === undefined) {
          next[item.doc_id] = (item.tags || []).join(", ");
        }
      }
      return next;
    });
  }, [filterProjectId]);

  useEffect(() => {
    const next = sanitizeLocale(localStorage.getItem(LOCALE_KEY));
    setLocale(next);
    document.documentElement.lang = next;
    void (async () => {
      try {
        const current = await currentSession();
        if (!current) {
          return;
        }
        setAccountName(current.username || "");
        setSessionReady(true);
        try {
          const prefs = await hydrateAccountPrefs();
          setLocale(prefs.locale);
        } catch (prefError) {
          console.error("preference load failed", prefError);
        }
        const [materialBody, projectItems] = await Promise.all([listMaterials(""), listProjects()]);
        setMaterials(materialBody.materials);
        setKnownTags(materialBody.tags);
        setProjects(projectItems);
        setTagDrafts(
          Object.fromEntries(
            materialBody.materials.map((item) => [item.doc_id, (item.tags || []).join(", ")]),
          ),
        );
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : text(next, "sessionNeeded"));
      } finally {
        setSessionChecked(true);
      }
    })();
  }, []);

  function applyLocale(next: Locale) {
    setLocale(next);
    localStorage.setItem(LOCALE_KEY, next);
    document.documentElement.lang = next;
  }

  async function enterAccount(session: SessionInfo) {
    setAccountName(session.username || "");
    setSessionReady(true);
    setError("");
    try {
      const prefs = await hydrateAccountPrefs();
      setLocale(prefs.locale);
    } catch (prefError) {
      console.error("preference load failed", prefError);
    }
    try {
      await refresh("");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : text(locale, "sessionNeeded"));
    }
  }

  async function onFiles(kind: "own_work" | "third_party", files: File[]) {
    if (!sessionReady) {
      setError(text(locale, "sessionNeeded"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await uploadMaterials(kind, files, uploadProjectId);
      if (result.errors?.length) {
        setError(result.errors.map((item) => `${item.filename}: ${item.message}`).join(" / "));
      }
      await refresh(filterProjectId);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : text(locale, "uploading"));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(docId: string) {
    setBusy(true);
    setError("");
    try {
      await deleteMaterial(docId);
      await refresh(filterProjectId);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : text(locale, "deleteMaterial"));
    } finally {
      setBusy(false);
    }
  }

  async function onCreateProject() {
    setBusy(true);
    setError("");
    try {
      const created = await createProject(newProjectName);
      setNewProjectName("");
      setUploadProjectId(created.project_id);
      await refresh(filterProjectId);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : text(locale, "projectCreate"));
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteProject(projectId: string) {
    setBusy(true);
    setError("");
    try {
      await deleteProject(projectId);
      if (filterProjectId === projectId) {
        setFilterProjectId("");
      }
      if (uploadProjectId === projectId) {
        setUploadProjectId("");
      }
      await refresh(filterProjectId === projectId ? "" : filterProjectId);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : text(locale, "projectDelete"));
    } finally {
      setBusy(false);
    }
  }

  async function onSaveTags(docId: string) {
    setBusy(true);
    setError("");
    try {
      const tags = parseTags(tagDrafts[docId] || "");
      const updated = await patchMaterial(docId, { tags });
      setTagDrafts((prev) => ({ ...prev, [docId]: (updated.tags || []).join(", ") }));
      await refresh(filterProjectId);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : text(locale, "tagsSave"));
    } finally {
      setBusy(false);
    }
  }

  async function onMoveProject(docId: string, projectId: string) {
    setBusy(true);
    setError("");
    try {
      await patchMaterial(docId, { project_id: projectId });
      await refresh(filterProjectId);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : text(locale, "projectFolder"));
    } finally {
      setBusy(false);
    }
  }

  if (!sessionChecked) {
    return (
      <main className="gate-wrap">
        <p className="hint">{text(locale, "checkingSession")}</p>
      </main>
    );
  }

  if (!sessionReady) {
    return <AccountGate locale={locale} onLocale={applyLocale} onSignedIn={(session) => void enterAccount(session)} />;
  }

  return (
    <main className="app">
      <header className="top">
        <div>
          <h1>{text(locale, "library")}</h1>
          <p className="lead">{text(locale, "libraryLead")}</p>
          <p className="hint">{text(locale, "libraryHint")}</p>
        </div>
        <div className="prefs">
          <SignedIn
            locale={locale}
            username={accountName}
            onLoggedOut={() => {
              setAccountName("");
              setSessionReady(false);
            }}
          />
          <Link href="/licenses">{text(locale, "licenses")}</Link>
          <Link className="lookup" href="/">
            {text(locale, "backStudio")}
          </Link>
        </div>
      </header>

      {busy ? <p>{text(locale, "uploading")}</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <section className="card project-bar">
        <h2>{text(locale, "projectFolder")}</h2>
        <div className="project-row">
          <label>
            <span className="hint">{text(locale, "projectFolder")}</span>
            <select
              value={uploadProjectId}
              disabled={busy || !sessionReady}
              onChange={(event) => setUploadProjectId(event.target.value)}
            >
              <option value="">{text(locale, "projectNone")}</option>
              {projects.map((item) => (
                <option key={item.project_id} value={item.project_id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="hint">{text(locale, "materialList")}</span>
            <select
              value={filterProjectId}
              disabled={busy || !sessionReady}
              onChange={(event) => {
                const next = event.target.value;
                setFilterProjectId(next);
                void refresh(next);
              }}
            >
              <option value="">{text(locale, "projectAll")}</option>
              {projects.map((item) => (
                <option key={item.project_id} value={item.project_id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="project-row">
          <input
            type="text"
            value={newProjectName}
            placeholder={text(locale, "projectNamePlaceholder")}
            disabled={busy || !sessionReady}
            onChange={(event) => setNewProjectName(event.target.value)}
          />
          <button
            type="button"
            disabled={busy || !sessionReady || !newProjectName.trim()}
            onClick={() => void onCreateProject()}
          >
            {text(locale, "projectCreate")}
          </button>
          {uploadProjectId ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void onDeleteProject(uploadProjectId)}
            >
              {text(locale, "projectDelete")}
            </button>
          ) : null}
        </div>
      </section>

      <div className="drop-grid">
        <DropZone locale={locale} kind="own_work" busy={busy || !sessionReady} onFiles={onFiles} />
        <DropZone locale={locale} kind="third_party" busy={busy || !sessionReady} onFiles={onFiles} />
      </div>

      <section className="history">
        <h2>{text(locale, "materialList")}</h2>
        {materials.length === 0 ? <p className="hint">{text(locale, "emptyMaterials")}</p> : null}
        <ul className="material-list">
          {materials.map((item) => (
            <li key={item.doc_id}>
              <div className="material-main">
                <strong>{item.title}</strong>
                <span className="badge">
                  {item.material_kind === "own_work" ? text(locale, "kindOwn") : text(locale, "kindThird")}
                </span>
                <span className="hint">
                  {item.media_type} · {Math.round(item.byte_size / 1024)} KB
                  {item.project_id
                    ? ` · ${projectNameById[item.project_id] || item.project_id}`
                    : ` · ${text(locale, "projectNone")}`}
                </span>
                <label className="tag-edit">
                  <span className="hint">{text(locale, "tagsLabel")}</span>
                  <input
                    type="text"
                    value={tagDrafts[item.doc_id] ?? (item.tags || []).join(", ")}
                    placeholder={text(locale, "tagsPlaceholder")}
                    disabled={busy}
                    onChange={(event) =>
                      setTagDrafts((prev) => ({ ...prev, [item.doc_id]: event.target.value }))
                    }
                  />
                </label>
                {knownTags.length ? (
                  <div className="tag-chips">
                    {knownTags.map((tag) => (
                      <button
                        key={`${item.doc_id}-${tag}`}
                        type="button"
                        className="tag-chip"
                        disabled={busy}
                        onClick={() => {
                          const current = parseTags(tagDrafts[item.doc_id] ?? "");
                          if (!current.includes(tag)) {
                            setTagDrafts((prev) => ({
                              ...prev,
                              [item.doc_id]: [...current, tag].join(", "),
                            }));
                          }
                        }}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                ) : null}
                <p className="hint">{text(locale, "tagsHint")}</p>
                <div className="project-row">
                  <select
                    value={item.project_id || ""}
                    disabled={busy}
                    onChange={(event) => void onMoveProject(item.doc_id, event.target.value)}
                  >
                    <option value="">{text(locale, "projectNone")}</option>
                    {projects.map((project) => (
                      <option key={project.project_id} value={project.project_id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                  <button type="button" disabled={busy} onClick={() => void onSaveTags(item.doc_id)}>
                    {text(locale, "tagsSave")}
                  </button>
                  <button type="button" disabled={busy} onClick={() => void onDelete(item.doc_id)}>
                    {text(locale, "deleteMaterial")}
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
