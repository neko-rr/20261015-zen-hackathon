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
  type Mannequin,
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
import { sanitizeLocale, text, type Locale, type MessageKey } from "@/lib/messages";
import { sanitizeTheme, THEME_OPTIONS, type ThemeId } from "@/lib/themes";
import { CompareSources } from "@/components/EditorSources";
import { AnatomyViewer, type CameraId, type DollView } from "@/components/AnatomyViewer";
import { MannequinLegend, MannequinOverlay } from "@/components/MannequinOverlay";
import { PERSPECTIVE_IDS, PerspectiveGuide, type PerspectiveMode } from "@/components/PerspectiveGuide";
import { buildFigure } from "@/lib/figure";
import { buildGuides } from "@/lib/figureGuides";
import { applyHandShape, HAND_IDS, type HandId } from "@/lib/handShape";
import { applyBends, applyMirror, applyTwist, limitHingeBend } from "@/lib/mannequinPose";
import { applyProportion, BUILD_IDS, HEAD_IDS, type BuildId, type HeadId } from "@/lib/proportions";

const THEME_KEY = "drawref:themeId";
const LOCALE_KEY = "drawref:locale";
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

type BodyView = "photo" | "mask" | "skeleton" | "muscle" | "view3d";
type ComparePanel = { view: BodyView; camera: CameraId };

const PANEL_LIMIT = 4;
const CAMERA_IDS: CameraId[] = ["front", "threeQuarter", "side", "back"];
const VIEW_IDS: BodyView[] = ["photo", "mask", "skeleton", "muscle", "view3d"];

/** 増やすマスは、まだ無い角度の3D。同じ角度はあとから各マスで選べる。 */
function addedPanel(existing: ComparePanel[]): ComparePanel {
  const used = new Set(
    existing.filter((panel) => panel.view === "view3d").map((panel) => panel.camera),
  );
  const camera = CAMERA_IDS.find((id) => !used.has(id)) ?? CAMERA_IDS[existing.length % CAMERA_IDS.length];
  return { view: "view3d", camera };
}

function viewMessage(view: BodyView): MessageKey {
  if (view === "mask") {
    return "viewMask";
  }
  if (view === "skeleton") {
    return "skeleton";
  }
  if (view === "muscle") {
    return "muscle";
  }
  if (view === "view3d") {
    return "view3d";
  }
  return "viewPhoto";
}

function cameraMessage(camera: CameraId): MessageKey {
  if (camera === "threeQuarter") {
    return "viewThreeQuarter";
  }
  if (camera === "side") {
    return "viewSide";
  }
  if (camera === "back") {
    return "viewBack";
  }
  return "viewFront";
}

function perspectiveMessage(mode: PerspectiveMode): MessageKey {
  if (mode === "horizon") {
    return "perspectiveHorizon";
  }
  if (mode === "one") {
    return "perspectiveOne";
  }
  if (mode === "two") {
    return "perspectiveTwo";
  }
  return "perspectiveOff";
}

function compareMessage(count: number): MessageKey {
  if (count === 2) {
    return "compare2";
  }
  if (count === 3) {
    return "compare3";
  }
  if (count === 4) {
    return "compare4";
  }
  return "compare1";
}

function headLabel(id: HeadId): MessageKey {
  switch (id) {
    case "9":
      return "head9";
    case "8":
      return "head8";
    case "7":
      return "head7";
    case "6":
      return "head6";
    case "5":
      return "head5";
    case "4":
      return "head4";
    default:
      return "proportionPhoto";
  }
}

function buildLabel(id: BuildId): MessageKey {
  switch (id) {
    case "slim":
      return "buildSlim";
    case "standard":
      return "buildStandard";
    case "sturdy":
      return "buildSturdy";
    case "broad_shoulder":
      return "buildBroad";
    case "wide_hip":
      return "buildHip";
    default:
      return "buildPhoto";
  }
}

function handLabel(id: HandId): MessageKey {
  if (id === "open") {
    return "handOpen";
  }
  if (id === "fist") {
    return "handFist";
  }
  return "handNatural";
}

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

type Adjust = {
  headCount: HeadId;
  build: BuildId;
  hand: HandId;
  bends: Record<string, number>;
  upperDeg: number;
  lowerDeg: number;
  mirrored: boolean;
};

const FRESH_ADJUST: Adjust = {
  headCount: "photo",
  build: "photo",
  hand: "natural",
  bends: {},
  upperDeg: 0,
  lowerDeg: 0,
  mirrored: false,
};

type DollSource = { id: string; mannequin: Mannequin; tone: number };

function dollSources(pose: PoseData, objects: PhotoObject[]): DollSource[] {
  const people = pose.people ?? [];
  const personObjects = objects.filter((item) => item.kind === "person");
  const fromPeople = people.flatMap((person, index) => {
    const mannequin = person.mannequin;
    const id = person.object_id || personObjects[index]?.object_id || "";
    if (!id || !mannequin?.joints.length) {
      return [];
    }
    return [{ id, mannequin, tone: index % 4 }];
  });
  if (fromPeople.length) {
    return fromPeople;
  }
  if (pose.mannequin?.joints.length) {
    const id = personObjects[0]?.object_id ?? "obj_1";
    return [{ id, mannequin: pose.mannequin, tone: 0 }];
  }
  return [];
}

function poseDoll(mannequin: Mannequin, adjust: Adjust): Mannequin {
  const proportioned = applyProportion(mannequin, adjust.headCount, adjust.build);
  const shaped = applyHandShape(proportioned, adjust.hand);
  const bent = applyBends(shaped, adjust.bends);
  const twisted = applyTwist(bent, (adjust.upperDeg * Math.PI) / 180, (adjust.lowerDeg * Math.PI) / 180);
  return applyMirror(twisted, adjust.mirrored);
}

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
  const [adjusts, setAdjusts] = useState<Record<string, Adjust>>({});
  const [editId, setEditId] = useState("");
  const [showRuler, setShowRuler] = useState(true);
  const [showBalance, setShowBalance] = useState(true);
  const [dollOpacity, setDollOpacity] = useState(100);
  const [perspective, setPerspective] = useState<PerspectiveMode>("off");
  const [horizonY, setHorizonY] = useState(0.5);
  const [vpOne, setVpOne] = useState(0.5);
  const [vpLeft, setVpLeft] = useState(0.22);
  const [vpRight, setVpRight] = useState(0.78);
  const [photoFlip, setPhotoFlip] = useState(false);
  const [grayscale, setGrayscale] = useState(false);
  const [selectedId, setSelectedId] = useState<string>("");
  const [step, setStep] = useState<"pick" | "detail">("pick");
  const [panels, setPanels] = useState<ComparePanel[]>([{ view: "photo", camera: "front" }]);
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
  const sources = useMemo(() => dollSources(pose, objects), [pose, objects]);
  const activeId = sources.some((item) => item.id === editId) ? editId : (sources[0]?.id ?? "");
  const activeAdjust = adjusts[activeId] ?? FRESH_ADJUST;
  const figures = useMemo<DollView[]>(() => {
    const ordered = [...sources].sort((a, b) => Number(a.id === activeId) - Number(b.id === activeId));
    return ordered.map((source) => {
      const adjust = adjusts[source.id] ?? FRESH_ADJUST;
      return {
        id: source.id,
        mannequin: source.mannequin,
        posed: poseDoll(source.mannequin, adjust),
        tone: source.tone,
        active: source.id === activeId,
      };
    });
  }, [sources, adjusts, activeId]);
  const activeFigure = figures.find((item) => item.active) ?? null;
  const guides = useMemo(
    () => buildGuides(activeFigure?.posed ?? { joints: [], bones: [], head: null }, activeAdjust.headCount, showRuler, showBalance),
    [activeFigure, activeAdjust.headCount, showRuler, showBalance],
  );
  const showsDoll = panels.some(
    (panel) => panel.view === "skeleton" || panel.view === "muscle" || panel.view === "view3d",
  );
  const showsFlatDoll = panels.some((panel) => panel.view === "skeleton" || panel.view === "muscle");

  function setPanelCount(count: number) {
    const nextCount = Math.min(PANEL_LIMIT, Math.max(1, count));
    setPanels((prev) => {
      if (nextCount === prev.length) {
        return prev;
      }
      if (nextCount < prev.length) {
        return prev.slice(0, nextCount);
      }
      const next = [...prev];
      while (next.length < nextCount) {
        next.push(addedPanel(next));
      }
      return next;
    });
  }

  function updatePanel(index: number, patch: Partial<ComparePanel>) {
    setPanels((prev) => prev.map((panel, item) => (item === index ? { ...panel, ...patch } : panel)));
  }

  function selectPerson(id: string) {
    setSelectedId(id);
    setEditId(id);
  }

  function patchAdjust(patch: Partial<Adjust>) {
    if (!activeId) {
      return;
    }
    setAdjusts((prev) => ({ ...prev, [activeId]: { ...(prev[activeId] ?? FRESH_ADJUST), ...patch } }));
  }

  function bendJoint(id: string, angle: number) {
    const source = sources.find((item) => item.id === activeId);
    if (!source) {
      return;
    }
    setAdjusts((prev) => {
      const current = prev[activeId] ?? FRESH_ADJUST;
      const shaped = applyHandShape(
        applyProportion(source.mannequin, current.headCount, current.build),
        current.hand,
      );
      return {
        ...prev,
        [activeId]: {
          ...current,
          bends: { ...current.bends, [id]: limitHingeBend(shaped, current.bends, id, angle) },
        },
      };
    });
  }

  function resetPose() {
    patchAdjust({ bends: {}, upperDeg: 0, lowerDeg: 0, mirrored: false });
  }

  function changeHand(next: HandId) {
    if (!activeId) {
      return;
    }
    setAdjusts((prev) => {
      const current = prev[activeId] ?? FRESH_ADJUST;
      const kept: Record<string, number> = {};
      for (const [id, value] of Object.entries(current.bends)) {
        if (!/^[lr]_(thumb|index|middle|ring|pinky)_/.test(id)) {
          kept[id] = value;
        }
      }
      return { ...prev, [activeId]: { ...current, hand: next, bends: kept } };
    });
  }

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
    setAdjusts({});
    setEditId("");
    setPanels([{ view: "photo", camera: "front" }]);
    setPerspective("off");
    setHorizonY(0.5);
    setVpOne(0.5);
    setVpLeft(0.22);
    setVpRight(0.78);
    setPhotoFlip(false);
    setGrayscale(false);
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
      setPanels([{ view: "mask", camera: "front" }]);
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
          <div className="modes" aria-label={text(locale, "compareCount")}>
            {([1, 2, 3, 4] as const).map((count) => (
              <button
                key={count}
                type="button"
                aria-pressed={panels.length === count}
                onClick={() => setPanelCount(count)}
              >
                {text(locale, compareMessage(count))}
              </button>
            ))}
          </div>
          {busy === "analyze" ? <p>{text(locale, "analyzing")}</p> : null}
          {(showsDoll && sources.length) || previewUrl ? (
            <div className="doll-controls">
              {sources.length > 1 ? <p className="hint">{text(locale, "multiPersonHint")}</p> : null}
              {showsDoll && sources.length ? (
              <fieldset className="doll-group">
                <legend>{text(locale, "groupBody")}</legend>
                <div className="proportion-row">
                  <label className="proportion-field">
                    <span>{text(locale, "proportion")}</span>
                    <select
                      value={activeAdjust.headCount}
                      onChange={(event) => patchAdjust({ headCount: event.target.value as HeadId })}
                    >
                      {HEAD_IDS.map((id) => (
                        <option key={id} value={id}>
                          {text(locale, headLabel(id))}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="proportion-field">
                    <span>{text(locale, "build")}</span>
                    <select
                      value={activeAdjust.build}
                      onChange={(event) => patchAdjust({ build: event.target.value as BuildId })}
                    >
                      {BUILD_IDS.map((id) => (
                        <option key={id} value={id}>
                          {text(locale, buildLabel(id))}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="proportion-field">
                    <span>{text(locale, "handShape")}</span>
                    <select value={activeAdjust.hand} onChange={(event) => changeHand(event.target.value as HandId)}>
                      {HAND_IDS.map((id) => (
                        <option key={id} value={id}>
                          {text(locale, handLabel(id))}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </fieldset>
              ) : null}
              <fieldset className="doll-group">
                <legend>{text(locale, "groupGuides")}</legend>
                <div className="guide-row">
                  {showsDoll && sources.length ? (
                    <>
                      <button type="button" aria-pressed={showRuler} onClick={() => setShowRuler((value) => !value)}>
                        {text(locale, "ruler")}
                      </button>
                      <button type="button" aria-pressed={showBalance} onClick={() => setShowBalance((value) => !value)}>
                        {text(locale, "balance")}
                      </button>
                    </>
                  ) : null}
                  {showsFlatDoll ? (
                    <label className="twist-field">
                      <span>{text(locale, "dollOpacity")}</span>
                      <input
                        type="range"
                        min={20}
                        max={100}
                        step={5}
                        value={dollOpacity}
                        aria-label={text(locale, "dollOpacity")}
                        onChange={(event) => setDollOpacity(Number(event.target.value))}
                      />
                      <span>{dollOpacity}%</span>
                    </label>
                  ) : null}
                  <button type="button" aria-pressed={photoFlip} onClick={() => setPhotoFlip((value) => !value)}>
                    {text(locale, "photoFlip")}
                  </button>
                  <button type="button" aria-pressed={grayscale} onClick={() => setGrayscale((value) => !value)}>
                    {text(locale, "grayscale")}
                  </button>
                  <div className="modes" aria-label={text(locale, "perspective")}>
                    {PERSPECTIVE_IDS.map((id) => (
                      <button
                        key={id}
                        type="button"
                        aria-pressed={perspective === id}
                        onClick={() => setPerspective(id)}
                      >
                        {text(locale, perspectiveMessage(id))}
                      </button>
                    ))}
                  </div>
                </div>
              </fieldset>
              {showsDoll && sources.length ? (
              <fieldset className="doll-group">
                <legend>{text(locale, "groupFacing")}</legend>
                <div className="guide-row">
                  <button
                    type="button"
                    aria-pressed={activeAdjust.mirrored}
                    onClick={() => patchAdjust({ mirrored: !activeAdjust.mirrored })}
                  >
                    {text(locale, "mirror")}
                  </button>
                  <label className="twist-field">
                    <span>{text(locale, "twistUpper")}</span>
                    <input
                      type="range"
                      min={-70}
                      max={70}
                      step={1}
                      value={activeAdjust.upperDeg}
                      aria-label={text(locale, "twistUpper")}
                      onChange={(event) => patchAdjust({ upperDeg: Number(event.target.value) })}
                    />
                    <span>{activeAdjust.upperDeg}°</span>
                  </label>
                  <label className="twist-field">
                    <span>{text(locale, "twistLower")}</span>
                    <input
                      type="range"
                      min={-70}
                      max={70}
                      step={1}
                      value={activeAdjust.lowerDeg}
                      aria-label={text(locale, "twistLower")}
                      onChange={(event) => patchAdjust({ lowerDeg: Number(event.target.value) })}
                    />
                    <span>{activeAdjust.lowerDeg}°</span>
                  </label>
                  <button type="button" onClick={resetPose}>
                    {text(locale, "poseReset")}
                  </button>
                </div>
              </fieldset>
              ) : null}
            </div>
          ) : null}
          {showsFlatDoll && sources.length ? (
            <div className="mannequin-tools">
              <MannequinLegend
                observed={text(locale, "poseObserved")}
                inferred={text(locale, "poseInferred")}
              />
            </div>
          ) : null}
          {showsFlatDoll && sources.length ? (
            <p className="hint">{text(locale, "poseBendHint")}</p>
          ) : null}
          {previewUrl ? (
            <div className={`view-grid is-${panels.length}`}>
              {panels.map((panel, index) => (
                <div className="compare-panel" key={index}>
                  <div className="compare-panel-bar">
                    <select
                      aria-label={text(locale, "compareView")}
                      value={panel.view}
                      onChange={(event) => updatePanel(index, { view: event.target.value as BodyView })}
                    >
                      {VIEW_IDS.map((id) => (
                        <option key={id} value={id}>
                          {text(locale, viewMessage(id))}
                        </option>
                      ))}
                    </select>
                    {panel.view === "view3d" ? (
                      <div className="modes" aria-label={text(locale, "compareCamera")}>
                        {CAMERA_IDS.map((id) => (
                          <button
                            key={id}
                            type="button"
                            aria-pressed={panel.camera === id}
                            onClick={() => updatePanel(index, { camera: id })}
                          >
                            {text(locale, cameraMessage(id))}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  {panel.view === "view3d" ? (
                    <AnatomyViewer
                      figures={figures}
                      bends={activeAdjust.bends}
                      onBend={bendJoint}
                      onSelect={selectPerson}
                      guides={guides}
                      camera={panel.camera}
                      photoFlip={photoFlip}
                      hint={
                        sources.length ? text(locale, "anatomyHint") : text(locale, "poseEmpty")
                      }
                      observedLabel={text(locale, "poseObserved")}
                      inferredLabel={text(locale, "poseInferred")}
                    />
                  ) : (
                    <div className={`stage-wrap${photoFlip ? " is-flipped" : ""}`}>
                      {/* blob URL は next/image に載せない */}
                      <img src={previewUrl} alt="" className={grayscale ? "is-gray" : undefined} />
                      <div className="overlay">
                        {panel.view === "mask"
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
                        {panel.view === "skeleton" || panel.view === "muscle" ? (
                          figures.length ? (
                            figures.map((figure) => (
                              <MannequinOverlay
                                key={figure.id}
                                mannequin={figure.posed}
                                bends={figure.active ? activeAdjust.bends : {}}
                                guides={figure.active ? guides : []}
                                opacity={dollOpacity / 100}
                                photoFlip={photoFlip}
                                tone={figure.tone}
                                active={figure.active}
                                onBend={bendJoint}
                                onSelect={() => selectPerson(figure.id)}
                              />
                            ))
                          ) : (
                            <svg className="contour pose-lines" viewBox="0 0 1 1" preserveAspectRatio="none">
                              {figure.bones.map((edge) => (
                                <line
                                  key={edge.id}
                                  x1={edge.x1}
                                  y1={edge.y1}
                                  x2={edge.x2}
                                  y2={edge.y2}
                                  className={`pose-bone pose-bone-${edge.part}${panel.view === "muscle" ? " is-muscle" : ""}`}
                                />
                              ))}
                              {figure.joints.map((point, pointIndex) => (
                                <circle
                                  key={`joint-${pointIndex}`}
                                  cx={point.x}
                                  cy={point.y}
                                  r={panel.view === "muscle" ? 0.012 : 0.007}
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
                          )
                        ) : null}
                        {panel.view === "muscle" && !figure.bones.length
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
                        {panel.view === "muscle"
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
                        <PerspectiveGuide
                          mode={perspective}
                          horizonY={horizonY}
                          vpOne={vpOne}
                          vpLeft={vpLeft}
                          vpRight={vpRight}
                          onHorizon={setHorizonY}
                          onVpOne={setVpOne}
                          onVpLeft={setVpLeft}
                          onVpRight={setVpRight}
                          photoFlip={photoFlip}
                        />
                      </div>
                    </div>
                  )}
                </div>
              ))}
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
                  onClick={() => {
                    setSelectedId(item.object_id);
                    if (item.kind === "person" && item.joints.length) {
                      setEditId(item.object_id);
                    }
                  }}
                >
                  {item.kind === "person" && item.joints.length ? (
                    <i
                      className={`swatch tone-${sources.find((doll) => doll.id === item.object_id)?.tone ?? 0}`}
                    />
                  ) : null}
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
                  <p className="hint">{text(locale, "similarNote")}</p>
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
