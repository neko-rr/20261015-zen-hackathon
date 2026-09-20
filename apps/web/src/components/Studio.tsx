"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ApiError,
  analyzePhoto,
  checkHealth,
  lookupObject,
  sourceHref,
  type Lookup,
  type PhotoObject,
  type Source,
} from "@/lib/api";
import { sanitizeLocale, text, type Locale } from "@/lib/messages";
import { sanitizeTheme, THEME_OPTIONS, type ThemeId } from "@/lib/themes";

const THEME_KEY = "drawref:themeId";
const LOCALE_KEY = "drawref:locale";
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

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

function rightLabel(locale: Locale, value: string): string {
  if (!value || value === "unknown") {
    return text(locale, "unknown");
  }
  return value;
}

function SourceFacts({ locale, source }: { locale: Locale; source: Source }) {
  const href = sourceHref(source.url);
  return (
    <article className="source">
      {href ? (
        <a href={href} target="_blank" rel="noreferrer">
          {source.title || href}
        </a>
      ) : (
        <p>{source.title || text(locale, "unknown")}</p>
      )}
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
    </article>
  );
}

export function Studio() {
  const [locale, setLocale] = useState<Locale>("ja");
  const [themeId, setThemeId] = useState<ThemeId>("default");
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [photoId, setPhotoId] = useState<string>("");
  const [objects, setObjects] = useState<PhotoObject[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [step, setStep] = useState<"pick" | "detail">("pick");
  const [bodyView, setBodyView] = useState<"skeleton" | "muscle" | "contour">("skeleton");
  const [busy, setBusy] = useState<"analyze" | "lookup" | null>(null);
  const [error, setError] = useState<string>("");
  const [history, setHistory] = useState<Lookup[]>([]);

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

  async function onFile(file: File | undefined) {
    if (!file) {
      return;
    }
    const mime = (file.type || "").split(";")[0].trim().toLowerCase();
    if (!ALLOWED_TYPES.has(mime)) {
      setError(locale === "ja" ? "JPEG、PNG、WebP のいずれかを上げてください。" : "Use JPEG, PNG, or WebP.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError(locale === "ja" ? "写真は 10MB 以下にしてください。" : "Use a photo under 10MB.");
      return;
    }

    setBusy("analyze");
    setError("");
    setHistory([]);
    setObjects([]);
    setSelectedId("");
    setStep("pick");
    setBodyView("skeleton");
    const nextUrl = URL.createObjectURL(file);
    setPreviewUrl((prev) => {
      if (prev) {
        URL.revokeObjectURL(prev);
      }
      return nextUrl;
    });

    try {
      const result = await analyzePhoto(file);
      if (!result.photo_id) {
        throw new ApiError("解析に失敗しました。", "analysis_failed");
      }
      setPhotoId(result.photo_id);
      setObjects(
        result.objects.map((item) => ({
          ...item,
          joints: item.joints ?? [],
          muscles: item.muscles ?? [],
          contour: item.contour ?? [],
        })),
      );
      setStep("pick");
      setSelectedId("");
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "解析に失敗しました。";
      setError(message);
    } finally {
      setBusy(null);
    }
  }

  async function onLookup() {
    if (!photoId || !selected) {
      return;
    }
    setBusy("lookup");
    setError("");
    try {
      const result = await lookupObject(photoId, selected.object_id);
      setHistory((prev) => [result, ...prev]);
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "調べものに失敗しました。";
      setError(message);
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
              disabled={busy !== null}
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
            <button type="button" aria-pressed={bodyView === "skeleton"} onClick={() => setBodyView("skeleton")}>
              {text(locale, "skeleton")}
            </button>
            <button type="button" aria-pressed={bodyView === "muscle"} onClick={() => setBodyView("muscle")}>
              {text(locale, "muscle")}
            </button>
            <button type="button" aria-pressed={bodyView === "contour"} onClick={() => setBodyView("contour")}>
              {text(locale, "contour")}
            </button>
          </div>
          {busy === "analyze" ? <p>{text(locale, "analyzing")}</p> : null}
          {previewUrl ? (
            <div className="stage-wrap">
              {/* blob URL は next/image に載せない */}
              <img src={previewUrl} alt="" />
              <div className="overlay">
                {objects.map((item) => {
                  if (!item.box || (step === "detail" && item.object_id !== selectedId)) {
                    return null;
                  }
                  return (
                    <button
                      key={item.object_id}
                      type="button"
                      className={`box${item.is_primary ? " is-primary" : ""}${
                        item.object_id === selectedId ? " is-selected" : ""
                      }`}
                      style={{
                        left: `${item.box.x * 100}%`,
                        top: `${item.box.y * 100}%`,
                        width: `${item.box.width * 100}%`,
                        height: `${item.box.height * 100}%`,
                      }}
                      onClick={() => setSelectedId(item.object_id)}
                    >
                      <span>
                        {item.label}
                        <span className="badge">{text(locale, kindKey(item.kind))}</span>
                      </span>
                    </button>
                  );
                })}
                {bodyView === "contour"
                  ? objects.map((item) =>
                      item.contour.length < 3 ? null : (
                        <svg key={item.object_id} className="contour" viewBox="0 0 1 1" preserveAspectRatio="none">
                          <polygon points={item.contour.map((point) => `${point.x},${point.y}`).join(" ")} />
                        </svg>
                      ),
                    )
                  : objects.map((item) => {
                      if (!isLiving(item.kind)) {
                        return null;
                      }
                      const points = bodyView === "skeleton" ? item.joints : item.muscles;
                      return points.map((point) => (
                        <span
                          key={`${item.object_id}-${bodyView}-${point.name}-${point.x}-${point.y}`}
                          className={`joint${bodyView === "muscle" ? " muscle" : ""}`}
                          style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}
                          title={point.name}
                        >
                          <span>{point.name}</span>
                        </span>
                      ));
                    })}
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
                  {!item.box ? <span className="badge">{text(locale, "noBox")}</span> : null}
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="lookup" disabled={!selected || busy !== null} onClick={() => void onLookup()}>
            {busy === "lookup" ? text(locale, "looking") : text(locale, "lookup")}
          </button>
          {error ? <p className="error">{error}</p> : null}

          <div className="history">
            <h2>{text(locale, "history")}</h2>
            {history.length === 0 ? <p className="hint">{text(locale, "emptyLookup")}</p> : null}
            {history.map((item, index) => (
              <article key={`${item.object_id}-${index}`}>
                <h3>{text(locale, "summary")}</h3>
                <p>{item.summary}</p>
                <h3>{text(locale, "sources")}</h3>
                {item.sources.map((source) => (
                  <SourceFacts key={source.url || source.title} locale={locale} source={source} />
                ))}
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
            ))}
          </div>
        </section>
      </div>
      <p className="status">
        {apiUp === null ? "" : apiUp ? text(locale, "apiOk") : text(locale, "apiDown")}
      </p>
    </main>
  );
}
