"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  analyzePhoto,
  askQuestion,
  checkHealth,
  ensureSession,
  listMaterials,
  listProjects,
  lookupObject,
  sourceHref,
  type ChatTurn,
  type Lookup,
  type PhotoObject,
  type PoseData,
  type Project,
} from "@/lib/api";
import {
  buildExportMarkdown,
  downloadText,
  formatViewedAt,
  kindCounts,
  type SourceChecklist,
} from "@/lib/editorAssist";
import { sanitizeLocale, text, type Locale } from "@/lib/messages";
import { sanitizeTheme, THEME_OPTIONS, type ThemeId } from "@/lib/themes";
import { CompareSources } from "@/components/EditorSources";
import { AnatomyViewer } from "@/components/AnatomyViewer";
import { buildFigure } from "@/lib/figure";

const THEME_KEY = "drawref:themeId";
const LOCALE_KEY = "drawref:locale";
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

type BodyView = "photo" | "mask" | "skeleton" | "muscle" | "view3d";

function kindKey(kind: string): "kindPerson" | "kindAnimal" | "kindObject" {
  if (kind === "person") {
    return "kindPerson";
  }
  if (kind === "animal") {
    return "kindAnimal";
  }
  return "kindObject";
}

function isLiving(kind: string): boolean {
  return kind === "person" || kind === "animal";
}

const EMPTY_POSE: PoseData = { landmarks: [], edges: [], muscles: [] };

export function Studio() {
  const [locale, setLocale] = useState<Locale>("ja");
  const [themeId, setThemeId] = useState<ThemeId>("default");
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [photoId, setPhotoId] = useState<string>("");
  const [objects, setObjects] = useState<PhotoObject[]>([]);
  const [pose, setPose] = useState<PoseData>(EMPTY_POSE);
  const [selectedId, setSelectedId] = useState<string>("");
  const [step, setStep] = useState<"pick" | "detail">("pick");
  const [bodyView, setBodyView] = useState<BodyView>("photo");
  const [busy, setBusy] = useState<"analyze" | "lookup" | "chat" | null>(null);
  const [error, setError] = useState<string>("");
  const [history, setHistory] = useState<Lookup[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatTurn[]>([]);
  const [chatDraft, setChatDraft] = useState<string>("");
  const [checks, setChecks] = useState<Record<string, SourceChecklist>>({});
  const [favorites, setFavorites] = useState<Record<string, true>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [projects, setProjects] = useState<Project[]>([]);
  const [knownTags, setKnownTags] = useState<string[]>([]);
  const [activeProjectId, setActiveProjectId] = useState("");
  const [activeTags, setActiveTags] = useState<string[]>([]);

  const objectLabels = useMemo(() => {
    const map: Record<string, string> = {};
    for (const item of objects) {
      map[item.object_id] = item.label;
    }
    return map;
  }, [objects]);

  const ragOptions = useMemo(
    () => ({ tags: activeTags, project_id: activeProjectId }),
    [activeTags, activeProjectId],
  );

  const favoriteEntries = useMemo(() => {
    const urls = Object.keys(favorites).filter((url) => favorites[url]);
    return urls.map((url) => ({
      url,
      note: notes[url] || "",
    }));
  }, [favorites, notes]);

  function setSourceCheck(key: string, next: SourceChecklist) {
    setChecks((prev) => ({ ...prev, [key]: next }));
  }

  function toggleFavorite(url: string) {
    if (!url.trim()) {
      return;
    }
    setFavorites((prev) => {
      const next = { ...prev };
      if (next[url]) {
        delete next[url];
      } else {
        next[url] = true;
      }
      return next;
    });
  }

  function setSourceNote(url: string, next: string) {
    if (!url.trim()) {
      return;
    }
    setNotes((prev) => ({ ...prev, [url]: next }));
  }

  function toggleActiveTag(tag: string) {
    setActiveTags((prev) =>
      prev.includes(tag) ? prev.filter((item) => item !== tag) : [...prev, tag],
    );
  }

  function onExportLog() {
    const body = buildExportMarkdown(
      history,
      chatHistory,
      checks,
      objectLabels,
      favorites,
      notes,
    );
    const stamp = new Date().toISOString().slice(0, 10);
    downloadText(`drawref-log-${stamp}.md`, body);
    downloadText(`drawref-log-${stamp}.txt`, body);
  }

  useEffect(() => {
    const nextLocale = sanitizeLocale(localStorage.getItem(LOCALE_KEY));
    const nextTheme = sanitizeTheme(localStorage.getItem(THEME_KEY));
    setLocale(nextLocale);
    setThemeId(nextTheme);
    document.documentElement.lang = nextLocale;
    document.documentElement.setAttribute("data-theme", nextTheme);
    void checkHealth().then(setApiUp);
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const figure = useMemo(() => buildFigure(pose), [pose]);

  const selected = useMemo(
    () => objects.find((item) => item.object_id === selectedId) ?? null,
    [objects, selectedId],
  );

  function applyLocale(next: Locale) {
    setLocale(next);
    localStorage.setItem(LOCALE_KEY, next);
    document.documentElement.lang = next;
  }

  function applyTheme(next: ThemeId) {
    setThemeId(next);
    localStorage.setItem(THEME_KEY, next);
    document.documentElement.setAttribute("data-theme", next);
  }

  async function loadPersonalMeta() {
    const [materialBody, projectItems] = await Promise.all([listMaterials(""), listProjects()]);
    setKnownTags(materialBody.tags);
    setProjects(projectItems);
  }

  async function onStartSession() {
    setSessionBusy(true);
    setError("");
    try {
      await ensureSession();
      setSessionReady(true);
      try {
        await loadPersonalMeta();
      } catch (metaError) {
        // 案件・タグは後からでもよい。ここで失敗しても写真は選べるようにする
        console.error("personal meta load failed", metaError);
      }
    } catch (caught) {
      const message =
        caught instanceof ApiError ? caught.message : text(locale, "sessionNeeded");
      setError(message);
      setSessionReady(false);
    } finally {
      setSessionBusy(false);
    }
  }

  async function onFile(file: File | undefined) {
    if (!file) {
      return;
    }
    if (!sessionReady) {
      setError(text(locale, "sessionNeeded"));
      return;
    }
    if (!ALLOWED_TYPES.has(file.type)) {
      setError("JPEG、PNG、WebP のいずれかを上げてください。");
      return;
    }
    setBusy("analyze");
    setError("");
    setHistory([]);
    setChatHistory([]);
    setChatDraft("");
    setChecks({});
    setFavorites({});
    setNotes({});
    setSelectedId("");
    setStep("pick");
    setPose(EMPTY_POSE);
    setBodyView("photo");
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(URL.createObjectURL(file));
    try {
      const result = await analyzePhoto(file);
      setPhotoId(result.photo_id);
      setPose(result.pose ?? EMPTY_POSE);
      setObjects(
        result.objects.map((item) => ({
          ...item,
          joints: item.joints ?? [],
          muscles: item.muscles ?? [],
          contour: item.contour ?? [],
        })),
      );
      setBodyView("mask");
      setStep("pick");
      setSelectedId("");
      await loadPersonalMeta();
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "解析に失敗しました。";
      setError(message);
    } finally {
      setBusy(null);
    }
  }

  async function runLookup(objectId: string) {
    if (!photoId || !objectId) {
      return;
    }
    setBusy("lookup");
    setError("");
    try {
      const result = await lookupObject(photoId, objectId, ragOptions);
      setHistory((prev) => [result, ...prev]);
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "調べものに失敗しました。";
      setError(message);
    } finally {
      setBusy(null);
    }
  }

  async function onLookup() {
    if (!selected) {
      return;
    }
    await runLookup(selected.object_id);
  }

  async function onAsk() {
    if (!photoId || !selected) {
      return;
    }
    const message = chatDraft.trim();
    if (!message) {
      setError(text(locale, "chatPlaceholder"));
      return;
    }
    setBusy("chat");
    setError("");
    try {
      const result = await askQuestion(photoId, selected.object_id, message, ragOptions);
      setChatHistory((prev) => [result, ...prev]);
      setChatDraft("");
    } catch (caught) {
      const next = caught instanceof ApiError ? caught.message : "調べものに失敗しました。";
      setError(next);
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="app">
      <header className="top">
        <div>
          <h1>{text(locale, "title")}</h1>
          <p className="lead">{text(locale, "lead")}</p>
        </div>
        <div className="prefs">
          <div className="demo">
            <strong>{text(locale, "demo")}</strong>
            <span className="hint">{text(locale, "demoHint")}</span>
            <button type="button" disabled={sessionBusy || sessionReady} onClick={() => void onStartSession()}>
              {sessionBusy ? text(locale, "starting") : text(locale, "start")}
            </button>
            {sessionReady ? <span className="hint">{text(locale, "sessionReady")}</span> : null}
          </div>
          <div>
            <Link href="/library">{text(locale, "library")}</Link>
          </div>
          <div>
            <p className="hint">{text(locale, "language")}</p>
            <div className="locale">
              <button type="button" aria-pressed={locale === "ja"} onClick={() => applyLocale("ja")}>
                日本語
              </button>
              <button type="button" aria-pressed={locale === "en"} onClick={() => applyLocale("en")}>
                English
              </button>
            </div>
          </div>
          <div>
            <p className="hint">{text(locale, "theme")}</p>
            <div className="swatches">
              {THEME_OPTIONS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  data-scheme={item.scheme}
                  aria-label={locale === "ja" ? item.ja : item.en}
                  aria-pressed={themeId === item.id}
                  style={{ background: item.swatch }}
                  onClick={() => applyTheme(item.id)}
                />
              ))}
            </div>
          </div>
        </div>
      </header>

      <div className="layout">
        <section className="card">
          <label className="file">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={busy !== null || !sessionReady || sessionBusy}
              onChange={(event) => {
                const file = event.target.files?.[0];
                void onFile(file);
                event.target.value = "";
              }}
            />
            <span>{text(locale, "pickPhoto")}</span>
          </label>
          <p className="hint">{text(locale, "pickHint")}</p>
          <div className="modes">
            <button type="button" aria-pressed={bodyView === "photo"} onClick={() => setBodyView("photo")}>
              {text(locale, "viewPhoto")}
            </button>
            <button type="button" aria-pressed={bodyView === "mask"} onClick={() => setBodyView("mask")}>
              {text(locale, "viewMask")}
            </button>
            <button type="button" aria-pressed={bodyView === "skeleton"} onClick={() => setBodyView("skeleton")}>
              {text(locale, "skeleton")}
            </button>
            <button type="button" aria-pressed={bodyView === "muscle"} onClick={() => setBodyView("muscle")}>
              {text(locale, "muscle")}
            </button>
            <button type="button" aria-pressed={bodyView === "view3d"} onClick={() => setBodyView("view3d")}>
              {text(locale, "view3d")}
            </button>
          </div>
          {busy === "analyze" ? <p>{text(locale, "analyzing")}</p> : null}
          {previewUrl && bodyView === "view3d" ? (
            <AnatomyViewer
              pose={pose}
              hint={
                pose.landmarks.length
                  ? text(locale, "anatomyHint")
                  : text(locale, "poseEmpty")
              }
              layerSkeleton={text(locale, "skeleton")}
              layerMuscle={text(locale, "muscle")}
            />
          ) : null}
          {previewUrl && bodyView !== "view3d" ? (
            <div className="stage-wrap">
              {/* blob URL は next/image に載せない */}
              <img src={previewUrl} alt="" />
              <div className="overlay">
                {bodyView === "mask"
                  ? objects.map((item) => {
                      if (item.contour.length < 3) {
                        return null;
                      }
                      if (step === "detail" && item.object_id !== selectedId) {
                        return null;
                      }
                      return (
                        <svg
                          key={item.object_id}
                          className={`contour${item.object_id === selectedId ? " is-selected" : ""}${
                            item.is_primary ? " is-primary" : ""
                          }`}
                          viewBox="0 0 1 1"
                          preserveAspectRatio="none"
                        >
                          <polygon
                            points={item.contour.map((point) => `${point.x},${point.y}`).join(" ")}
                            className="contour-hit"
                            onClick={() => setSelectedId(item.object_id)}
                          />
                          <title>{item.label}</title>
                        </svg>
                      );
                    })
                  : null}
                {bodyView === "skeleton" || bodyView === "muscle" ? (
                  <svg className="contour pose-lines" viewBox="0 0 1 1" preserveAspectRatio="none">
                    {figure.bones.map((edge) => (
                      <line
                        key={edge.id}
                        x1={edge.x1}
                        y1={edge.y1}
                        x2={edge.x2}
                        y2={edge.y2}
                        className={`pose-bone pose-bone-${edge.part}${bodyView === "muscle" ? " is-muscle" : ""}`}
                      />
                    ))}
                    {figure.joints.map((point, index) => (
                      <circle
                        key={`joint-${index}`}
                        cx={point.x}
                        cy={point.y}
                        r={bodyView === "muscle" ? 0.012 : 0.007}
                        className="pose-joint"
                      />
                    ))}
                    {figure.head ? (
                      <circle
                        cx={figure.head.x}
                        cy={figure.head.y}
                        r={figure.head.radius}
                        className="pose-head"
                      />
                    ) : null}
                  </svg>
                ) : null}
                {bodyView === "muscle" && !figure.bones.length
                  ? objects
                      .filter((item) => isLiving(item.kind))
                      .flatMap((item) => item.joints)
                      .map((point) => (
                        <span
                          key={`fallback-${point.name}-${point.x}`}
                          className="joint"
                          style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}
                          title={point.name}
                        />
                      ))
                  : null}
                {bodyView === "muscle"
                  ? (pose.muscles.length
                      ? pose.muscles
                      : objects.flatMap((item) => (isLiving(item.kind) ? item.muscles : []))
                    ).map((point) => (
                      <span
                        key={`muscle-${point.name}-${point.x}-${point.y}`}
                        className="joint muscle"
                        style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}
                        title={point.name}
                      >
                        <span>{point.name}</span>
                      </span>
                    ))
                  : null}
              </div>
            </div>
          ) : null}
        </section>

        <section className="card">
          <h2>{text(locale, "layers")}</h2>
          {objects.length === 0 ? <p className="hint">{text(locale, "noLayers")}</p> : null}
          <ul className="layers">
            {objects.map((item) => (
              <li key={item.object_id}>
                <button
                  type="button"
                  className="row"
                  aria-pressed={item.object_id === selectedId}
                  onClick={() => setSelectedId(item.object_id)}
                >
                  {item.label}
                  {item.is_primary ? <span className="badge">{text(locale, "primary")}</span> : null}
                  <span className="badge">{text(locale, kindKey(item.kind))}</span>
                  {!item.contour.length && !item.box ? (
                    <span className="badge">{text(locale, "noBox")}</span>
                  ) : null}
                </button>
              </li>
            ))}
          </ul>

          <div className="personal-filters">
            <label>
              <span className="hint">{text(locale, "activeProject")}</span>
              <select
                value={activeProjectId}
                disabled={!sessionReady || busy !== null}
                onChange={(event) => setActiveProjectId(event.target.value)}
              >
                <option value="">{text(locale, "projectAll")}</option>
                {projects.map((item) => (
                  <option key={item.project_id} value={item.project_id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <div>
              <p className="hint">{text(locale, "activeTags")}</p>
              {knownTags.length === 0 ? (
                <p className="hint">{text(locale, "emptyMaterials")}</p>
              ) : (
                <div className="tag-chips">
                  {knownTags.map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      className={`tag-chip${activeTags.includes(tag) ? " is-on" : ""}`}
                      aria-pressed={activeTags.includes(tag)}
                      disabled={busy !== null}
                      onClick={() => toggleActiveTag(tag)}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <button type="button" className="lookup" disabled={!selected || busy !== null} onClick={() => void onLookup()}>
            {busy === "lookup" ? text(locale, "looking") : text(locale, "lookup")}
          </button>

          <form
            className="chat-form"
            onSubmit={(event) => {
              event.preventDefault();
              void onAsk();
            }}
          >
            <label className="chat-label" htmlFor="chat-input">
              {text(locale, "chat")}
            </label>
            <textarea
              id="chat-input"
              rows={3}
              value={chatDraft}
              placeholder={text(locale, "chatPlaceholder")}
              disabled={!selected || busy !== null}
              onChange={(event) => setChatDraft(event.target.value)}
            />
            <button type="submit" className="lookup" disabled={!selected || busy !== null || !chatDraft.trim()}>
              {busy === "chat" ? text(locale, "asking") : text(locale, "ask")}
            </button>
          </form>

          {error ? <p className="error">{error}</p> : null}

          <button
            type="button"
            className="lookup"
            disabled={history.length === 0 && chatHistory.length === 0}
            onClick={onExportLog}
          >
            {text(locale, "exportLog")}
          </button>
          <p className="hint">{text(locale, "riskHint")}</p>

          <div className="history">
            <h2>{text(locale, "favorites")}</h2>
            {favoriteEntries.length === 0 ? (
              <p className="hint">{text(locale, "emptyFavorites")}</p>
            ) : (
              <ul className="favorite-list">
                {favoriteEntries.map((item) => {
                  const href = sourceHref(item.url);
                  return (
                    <li key={item.url}>
                      {href ? (
                        <a href={href} target="_blank" rel="noreferrer">
                          {item.url}
                        </a>
                      ) : (
                        <span>{item.url}</span>
                      )}
                      {item.note ? <span className="hint">{item.note}</span> : null}
                      <button type="button" onClick={() => toggleFavorite(item.url)}>
                        {text(locale, "favoriteUnpin")}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="history">
            <h2>{text(locale, "history")}</h2>
            {history.length === 0 ? <p className="hint">{text(locale, "emptyLookup")}</p> : null}
            {history.map((item, index) => {
              const label = item.object_label || objectLabels[item.object_id] || item.object_id;
              return (
                <article key={`${item.object_id}-lookup-${index}`}>
                  <p className="turn-meta">
                    {label}
                    {item.viewed_at ? ` · ${formatViewedAt(item.viewed_at)}` : ""}
                    {` · ${kindCounts(item.sources)}`}
                  </p>
                  <button
                    type="button"
                    className="lookup-again"
                    disabled={busy !== null || !photoId}
                    onClick={() => void runLookup(item.object_id)}
                  >
                    {text(locale, "lookupAgain")}
                  </button>
                  <h3>{text(locale, "summary")}</h3>
                  <p>{item.summary}</p>
                  <h3>{text(locale, "sources")}</h3>
                  <CompareSources
                    locale={locale}
                    sources={item.sources}
                    viewedAt={item.viewed_at}
                    checks={checks}
                    onCheck={setSourceCheck}
                    showFacts={false}
                    favorites={favorites}
                    onToggleFavorite={toggleFavorite}
                    notes={notes}
                    onNote={setSourceNote}
                  />
                  {item.search_suggestions_html ? (
                    <div>
                      <h3>{text(locale, "suggestions")}</h3>
                      <div
                        className="suggestions"
                        dangerouslySetInnerHTML={{ __html: item.search_suggestions_html }}
                      />
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>

          <div className="history">
            <h2>{text(locale, "chat")}</h2>
            {chatHistory.length === 0 ? <p className="hint">{text(locale, "emptyChat")}</p> : null}
            {chatHistory.map((item, index) => {
              const label = item.object_label || objectLabels[item.object_id] || item.object_id;
              return (
                <article key={`${item.object_id}-chat-${index}`}>
                  <p className="turn-meta">
                    {label}
                    {item.viewed_at ? ` · ${formatViewedAt(item.viewed_at)}` : ""}
                    {` · ${kindCounts(item.sources)}`}
                  </p>
                  <h3>{text(locale, "question")}</h3>
                  <p>{item.message}</p>
                  <h3>{text(locale, "answer")}</h3>
                  <p>{item.answer}</p>
                  <h3>{text(locale, "sources")}</h3>
                  <CompareSources
                    locale={locale}
                    sources={item.sources}
                    viewedAt={item.viewed_at}
                    checks={checks}
                    onCheck={setSourceCheck}
                    showFacts
                    favorites={favorites}
                    onToggleFavorite={toggleFavorite}
                    notes={notes}
                    onNote={setSourceNote}
                  />
                  {item.search_suggestions_html ? (
                    <div>
                      <h3>{text(locale, "suggestions")}</h3>
                      <div
                        className="suggestions"
                        dangerouslySetInnerHTML={{ __html: item.search_suggestions_html }}
                      />
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        </section>
      </div>
      <p className="status">
        {apiUp === null ? "" : apiUp ? text(locale, "apiOk") : text(locale, "apiDown")}
      </p>
    </main>
  );
}
