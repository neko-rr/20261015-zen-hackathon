"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  ApiError,
  analyzePhoto,
  askQuestion,
  checkHealth,
  getPhoto,
  currentSession,
  listMaterials,
  listProjects,
  lookupObject,
  type Material,
  speakPose,
  transcribePose,
  sourceHref,
  type ChatTurn,
  type FileFacts,
  type Lookup,
  type Mannequin,
  type PhotoObject,
  type PoseData,
  type SpokenPoseOption,
  type Project,
  type WebPage,
  type WebImage,
} from "@/lib/api";
import {
  buildExportMarkdown,
  downloadText,
  formatViewedAt,
  kindCounts,
  type SourceChecklist,
} from "@/lib/editorAssist";
import { AccountGate, SignedIn } from "@/components/AccountGate";
import { hydrateAccountPrefs, LOCALE_KEY, persistLocale, persistTheme, THEME_KEY } from "@/lib/accountPrefs";
import { sanitizeLocale, text, type Locale, type MessageKey } from "@/lib/messages";
import { startPoseMic } from "@/lib/poseMic";
import { preparePhotoFile } from "@/lib/preparePhoto";
import { sanitizeTheme, THEME_OPTIONS, type ThemeId } from "@/lib/themes";
import { CompareSources } from "@/components/EditorSources";
import { MaterialDesk } from "@/components/MaterialDesk";
import { ProjectMemo } from "@/components/ProjectMemo";
import { AnatomyViewer, type CameraId, type DollView } from "@/components/AnatomyViewer";
import { DOLL_BODIES, type DollBodyId } from "@/lib/mixamoBody";
import { CaptureGuide } from "@/components/CaptureGuide";
import { MannequinLegend, MannequinOverlay } from "@/components/MannequinOverlay";
import { PERSPECTIVE_IDS, PerspectiveGuide, type PerspectiveMode } from "@/components/PerspectiveGuide";
import { buildFigure } from "@/lib/figure";
import { buildGuides } from "@/lib/figureGuides";
import { applyHandShape, HAND_IDS, type HandId } from "@/lib/handShape";
import { applyBends, applyMirror, applyTwist, limitHingeBend } from "@/lib/mannequinPose";
import { applyProportion, BUILD_IDS, HEAD_IDS, type BuildId, type HeadId } from "@/lib/proportions";

const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;

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

function personIsSmall(pose: PoseData): boolean {
  const people = pose.people?.length ? pose.people : pose.landmarks.length ? [{ landmarks: pose.landmarks }] : [];
  return people.some((person) => {
    const ys = person.landmarks.map((point) => point.y);
    if (ys.length < 4) {
      return false;
    }
    return Math.max(...ys) - Math.min(...ys) < 0.45;
  });
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

function fileFactValue(locale: Locale, value: string): string {
  if (value === "present") {
    return text(locale, "fileFactsPresent");
  }
  if (value === "absent") {
    return text(locale, "fileFactsAbsent");
  }
  if (!value || value === "unknown") {
    return text(locale, "unknown");
  }
  return value;
}

export function Studio() {
  const [locale, setLocale] = useState<Locale>("ja");
  const [themeId, setThemeId] = useState<ThemeId>("default");
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [accountName, setAccountName] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [photoId, setPhotoId] = useState<string>("");
  const [fileFacts, setFileFacts] = useState<FileFacts | null>(null);
  const [webPages, setWebPages] = useState<WebPage[]>([]);
  const [webImages, setWebImages] = useState<WebImage[]>([]);
  const [rightsQuery, setRightsQuery] = useState("");
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
  const [dollBody, setDollBody] = useState<DollBodyId>("x-bot");
  const [selectedId, setSelectedId] = useState<string>("");
  const [step, setStep] = useState<"pick" | "detail">("pick");
  const [panels, setPanels] = useState<ComparePanel[]>([{ view: "photo", camera: "front" }]);
  const [busy, setBusy] = useState<"analyze" | "lookup" | "chat" | "speak" | null>(null);
  const [poseDraft, setPoseDraft] = useState("");
  const [listening, setListening] = useState(false);
  const micRef = useRef<{ stop: () => Promise<Blob> } | null>(null);
  const [poseChoices, setPoseChoices] = useState<SpokenPoseOption[]>([]);
  const [posePick, setPosePick] = useState(0);
  const [poseFromCatalog, setPoseFromCatalog] = useState(false);
  const [spokenQuery, setSpokenQuery] = useState("");
  const [labelsPending, setLabelsPending] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [error, setError] = useState<string>("");
  const [sourcesOpen, setSourcesOpen] = useState(true);
  const [history, setHistory] = useState<Lookup[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatTurn[]>([]);
  const [chatDraft, setChatDraft] = useState<string>("");
  const [checks, setChecks] = useState<Record<string, SourceChecklist>>({});
  const [favorites, setFavorites] = useState<Record<string, true>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [projects, setProjects] = useState<Project[]>([]);
  const [library, setLibrary] = useState<Material[]>([]);
  const [openMaterialIds, setOpenMaterialIds] = useState<string[]>([]);
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
    const previous = locale;
    setLocale(next);
    localStorage.setItem(LOCALE_KEY, next);
    document.documentElement.lang = next;
    if (!sessionReady) {
      return;
    }
    void persistLocale(next).catch((caught) => {
      setLocale(previous);
      localStorage.setItem(LOCALE_KEY, previous);
      document.documentElement.lang = previous;
      const message = caught instanceof ApiError ? caught.message : text(previous, "prefsSaveFailed");
      setError(message);
    });
  }

  function applyTheme(next: ThemeId) {
    const previous = themeId;
    setThemeId(next);
    localStorage.setItem(THEME_KEY, next);
    document.documentElement.setAttribute("data-theme", next);
    if (!sessionReady) {
      return;
    }
    void persistTheme(next).catch((caught) => {
      setThemeId(previous);
      localStorage.setItem(THEME_KEY, previous);
      document.documentElement.setAttribute("data-theme", previous);
      const message = caught instanceof ApiError ? caught.message : text(locale, "prefsSaveFailed");
      setError(message);
    });
  }

  async function loadPersonalMeta() {
    const [materialBody, projectItems] = await Promise.all([listMaterials(""), listProjects()]);
    setKnownTags(materialBody.tags);
    setLibrary(materialBody.materials);
    setProjects(projectItems);
  }

  async function refreshProjects() {
    try {
      setProjects(await listProjects());
    } catch {
      // 作業そのものは続ける。記録の再表示だけ失敗する。
    }
  }

  function markSession(_kind: string, username?: string) {
    setAccountName(username || "");
    setSessionReady(true);
  }

  useEffect(() => {
    void (async () => {
      try {
        const current = await currentSession();
        if (!current) {
          return;
        }
        markSession(current.kind, current.username);
        try {
          const prefs = await hydrateAccountPrefs();
          setLocale(prefs.locale);
          setThemeId(prefs.themeId);
          await loadPersonalMeta();
        } catch (metaError) {
          console.error("personal meta load failed", metaError);
        }
      } catch (caught) {
        console.error("session resume failed", caught);
      }
    })();
  }, []);

  function enterAccount(session: { kind: string; username?: string }) {
    markSession(session.kind, session.username);
    void hydrateAccountPrefs()
      .then((prefs) => {
        setLocale(prefs.locale);
        setThemeId(prefs.themeId);
      })
      .catch((prefError) => {
        console.error("preference load failed", prefError);
      });
    void loadPersonalMeta().catch((metaError) => {
      console.error("personal meta load failed", metaError);
    });
  }

  useEffect(() => {
    return () => {
      const mic = micRef.current;
      micRef.current = null;
      if (mic) {
        void mic.stop();
      }
    };
  }, []);

  async function submitSpoken(message: string) {
    if (message === spokenQuery && poseChoices.length > 1) {
      showSpokenChoice((posePick + 1) % poseChoices.length);
      return;
    }
    const result = await speakPose(message);
    const first = result.options[0];
    setSpokenQuery(message);
    setPoseChoices(result.options);
    setPosePick(0);
    setPoseFromCatalog(result.pose_source === "catalog");
    applySpoken(first, result.mannequin, sources.length === 0);
  }

  async function onSpeak() {
    const message = poseDraft.trim();
    if (!message) {
      setError(text(locale, "speakPlaceholder"));
      return;
    }
    if (!sessionReady) {
      setError(text(locale, "sessionNeeded"));
      return;
    }
    setBusy("speak");
    setError("");
    try {
      await submitSpoken(message);
    } catch (caught) {
      const messageText = caught instanceof ApiError ? caught.message : "ポーズを読めませんでした。";
      setError(messageText);
    } finally {
      setBusy(null);
    }
  }

  async function onMic() {
    if (!sessionReady) {
      setError(text(locale, "sessionNeeded"));
      return;
    }
    if (listening && micRef.current) {
      const mic = micRef.current;
      micRef.current = null;
      setListening(false);
      setBusy("speak");
      setError("");
      try {
        const heard = (await transcribePose(await mic.stop(), locale)).trim();
        if (!heard) {
          setError(text(locale, "speakMicEmpty"));
          return;
        }
        setPoseDraft(heard);
        await submitSpoken(heard);
      } catch (caught) {
        const messageText = caught instanceof ApiError ? caught.message : text(locale, "speakMicDenied");
        setError(messageText);
      } finally {
        setBusy(null);
      }
      return;
    }
    try {
      micRef.current = await startPoseMic();
      setListening(true);
      setError("");
    } catch {
      setError(text(locale, "speakMicDenied"));
    }
  }

  function showSpokenChoice(index: number) {
    const option = poseChoices[index];
    if (!option) {
      return;
    }
    setPosePick(index);
    applySpoken(option, { joints: [], bones: [], head: null }, false);
  }

  function cancelSpoken() {
    setPoseChoices([]);
    setPosePick(0);
    setPoseFromCatalog(false);
    setSpokenQuery("");
    const spokenOnly = !previewUrl && objects.every((item) => item.object_id === "spoken_1");
    if (spokenOnly) {
      setPose(EMPTY_POSE);
      setObjects([]);
      setAdjusts({});
      setEditId("");
      setSelectedId("");
      setPanels([{ view: "photo", camera: "front" }]);
      return;
    }
    if (activeId) {
      setAdjusts((prev) => ({ ...prev, [activeId]: { ...FRESH_ADJUST } }));
    }
  }

  function applySpoken(option: SpokenPoseOption, mannequin: Mannequin, install: boolean) {
    const target = install || !sources.length ? "spoken_1" : activeId;
    if (install) {
      setPose({
        landmarks: [],
        edges: [],
        muscles: [],
        mannequin,
        people: [
          {
            object_id: "spoken_1",
            mannequin,
            landmarks: [],
            edges: [],
            muscles: [],
          },
        ],
      });
      setObjects([
        {
          object_id: "spoken_1",
          label: option.summary,
          kind: "person",
          is_primary: true,
          box: null,
          joints: [],
          muscles: [],
          contour: [],
        },
      ]);
      setEditId("spoken_1");
      setSelectedId("spoken_1");
      setPanels([{ view: "view3d", camera: "threeQuarter" }]);
    } else if (target === "spoken_1") {
      setObjects((prev) => prev.map((item) => (item.object_id === target ? { ...item, label: option.summary } : item)));
    }
    setAdjusts((prev) => ({
      ...prev,
      [target]: {
        ...(prev[target] ?? FRESH_ADJUST),
        bends: option.bends,
        upperDeg: option.upper_deg,
        lowerDeg: option.lower_deg,
        mirrored: option.mirrored,
      },
    }));
  }

  async function onFile(file: File | undefined) {
    if (!file) {
      return;
    }
    if (!sessionReady) {
      setError(text(locale, "sessionNeeded"));
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setError(text(locale, "photoTooLarge"));
      return;
    }
    setBusy("analyze");
    setError("");
    const prepared = await preparePhotoFile(file);
    setHistory([]);
    setChatHistory([]);
    setChatDraft("");
    setChecks({});
    setFavorites({});
    setNotes({});
    setSelectedId("");
    setStep("pick");
    setPose(EMPTY_POSE);
    setPoseChoices([]);
    setPosePick(0);
    setPoseFromCatalog(false);
    setSpokenQuery("");
    setAdjusts({});
    setEditId("");
    setLabelsPending(false);
    setFileFacts(null);
    setWebPages([]);
    setWebImages([]);
    setRightsQuery("");
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
    setPreviewUrl(URL.createObjectURL(prepared));
    try {
      const result = await analyzePhoto(prepared);
      setPhotoId(result.photo_id);
      if (activeProjectId) {
        void refreshProjects();
      }
      setFileFacts(result.file_facts);
      setWebPages(result.web_pages);
      setWebImages(result.web_images);
      setPose(result.pose ?? EMPTY_POSE);
      setObjects(
        result.objects.map((item) => ({
          ...item,
          joints: item.joints ?? [],
          muscles: item.muscles ?? [],
          contour: item.contour ?? [],
        })),
      );
      const hasDoll = Boolean(
        result.pose.people?.some((person) => person.mannequin?.joints?.length) ||
          result.pose.mannequin?.joints?.length,
      );
      setPanels([{ view: hasDoll ? "skeleton" : "mask", camera: "front" }]);
      setLabelsPending(result.labels_pending);
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

  useEffect(() => {
    if (!labelsPending || !photoId) {
      return;
    }
    let stopped = false;
    let tries = 0;
    const timer = window.setInterval(() => {
      tries += 1;
      void getPhoto(photoId)
        .then((next) => {
          if (stopped || next.labels_pending) {
            if (tries >= 20 && !stopped) {
              setLabelsPending(false);
            }
            return;
          }
          setObjects(
            next.objects.map((item) => ({
              ...item,
              joints: item.joints ?? [],
              muscles: item.muscles ?? [],
              contour: item.contour ?? [],
            })),
          );
          setLabelsPending(false);
        })
        .catch((error) => {
          console.error("label poll failed", error);
          if (tries >= 20 && !stopped) {
            setLabelsPending(false);
          }
        });
    }, 1000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [labelsPending, photoId]);

  async function runLookup(objectId: string) {
    if (!photoId || !objectId) {
      return;
    }
    setBusy("lookup");
    setError("");
    try {
      const result = await lookupObject(photoId, objectId, {
        ...ragOptions,
        query: rightsQuery.trim(),
      });
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
      const opened = (result.materials ?? []).map((item) => item.doc_id).filter(Boolean);
      if (opened.length) {
        setOpenMaterialIds((prev) => {
          const next = [...prev];
          for (const id of opened) {
            if (!next.includes(id)) {
              next.push(id);
            }
          }
          return next;
        });
      }
      if (activeProjectId) {
        void refreshProjects();
      }
    } catch (caught) {
      const next = caught instanceof ApiError ? caught.message : "調べものに失敗しました。";
      setError(next);
    } finally {
      setBusy(null);
    }
  }

  if (!sessionReady) {
    return <AccountGate locale={locale} onLocale={applyLocale} onSignedIn={enterAccount} />;
  }

  return (
    <main className="app">
      <header className="top">
        <div>
          <h1>{text(locale, "title")}</h1>
          <p className="lead">{text(locale, "lead")}</p>
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
          <div>
            <Link href="/library">{text(locale, "library")}</Link>
          </div>
          <div>
            <Link href="/licenses">{text(locale, "licenses")}</Link>
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

      <div className={`layout${sourcesOpen ? "" : " is-focus"}`}>
        <section className="card">
          <div className="file-row">
            <label className="file">
              <input
                type="file"
                accept="image/*"
                disabled={busy !== null || !sessionReady}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  void onFile(file);
                  event.target.value = "";
                }}
              />
              <span>{text(locale, "pickPhoto")}</span>
            </label>
            <button
              type="button"
              disabled={busy !== null || !sessionReady}
              onClick={() => setCameraOpen(true)}
            >
              {text(locale, "shoot")}
            </button>
          </div>
          <p className="hint">{text(locale, "guideNote")}</p>
          <p className="hint">{text(locale, "pickHint")}</p>
          <form
            className="speak-row"
            onSubmit={(event) => {
              event.preventDefault();
              void onSpeak();
            }}
          >
            <input
              type="text"
              value={poseDraft}
              maxLength={500}
              placeholder={text(locale, "speakPlaceholder")}
              disabled={busy !== null || !sessionReady}
              onChange={(event) => setPoseDraft(event.target.value)}
            />
            <button type="submit" disabled={busy !== null || listening || !sessionReady}>
              {busy === "speak" ? text(locale, "speakBusy") : text(locale, "speakPose")}
            </button>
            <button
              type="button"
              disabled={busy !== null || !sessionReady}
              onClick={() => void onMic()}
            >
              {listening ? text(locale, "speakMicStop") : text(locale, "speakMic")}
            </button>
          </form>
          <p className="hint">{text(locale, "speakHint")}</p>
          {cameraOpen ? (
            <CaptureGuide
              title={text(locale, "shoot")}
              note={text(locale, "guideNote")}
              takeLabel={text(locale, "shootTake")}
              closeLabel={text(locale, "shootClose")}
              deniedLabel={text(locale, "shootDenied")}
              onShot={(file) => {
                setCameraOpen(false);
                void onFile(file);
              }}
              onClose={() => setCameraOpen(false)}
            />
          ) : null}
          {previewUrl && personIsSmall(pose) ? <p className="hint">{text(locale, "guideWarn")}</p> : null}
          {fileFacts ? (
            <div className="facts">
              <p className="hint">{text(locale, "fileFactsNote")}</p>
              <div>
                <span>{text(locale, "fileArtist")}</span>
                <span>{fileFactValue(locale, fileFacts.artist)}</span>
              </div>
              <div>
                <span>{text(locale, "fileCopyright")}</span>
                <span>{fileFactValue(locale, fileFacts.copyright)}</span>
              </div>
              <div>
                <span>{text(locale, "fileCopyrightUrl")}</span>
                <span>{fileFactValue(locale, fileFacts.copyright_url)}</span>
              </div>
              <div>
                <span>{text(locale, "fileImageId")}</span>
                <span>{fileFactValue(locale, fileFacts.image_id)}</span>
              </div>
              <div>
                <span>{text(locale, "fileCredit")}</span>
                <span>{fileFactValue(locale, fileFacts.credit)}</span>
              </div>
              <div>
                <span>{text(locale, "fileC2pa")}</span>
                <span>
                  {fileFactValue(locale, fileFacts.c2pa)}
                  {fileFacts.c2pa === "present" && fileFacts.c2pa_generator !== "unknown"
                    ? ` ${fileFacts.c2pa_generator}`
                    : ""}
                </span>
              </div>
            </div>
          ) : null}
          {webPages.length > 0 || webImages.length > 0 ? (
            <div className="facts">
              <WebImageGrid locale={locale} images={webImages} />
              {webPages.length > 0 ? <p className="hint">{text(locale, "webPagesNote")}</p> : null}
              <ul>
                {webPages.map((page) => (
                  <li key={page.url}>
                    <a href={page.url} target="_blank" rel="noreferrer">
                      {page.title || page.url}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
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
          {busy === "analyze" ? <p className="hint">{text(locale, "analyzing")}</p> : null}
          {labelsPending ? <p className="hint">{text(locale, "naming")}</p> : null}
          {busy === "lookup" || busy === "chat" ? <p className="hint">{text(locale, busy === "lookup" ? "looking" : "asking")}</p> : null}
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
                    <span>{text(locale, "dollBody")}</span>
                    <select value={dollBody} onChange={(event) => setDollBody(event.target.value as DollBodyId)}>
                      {DOLL_BODIES.map((id) => (
                        <option key={id} value={id}>
                          {text(locale, id === "x-bot" ? "dollXBot" : "dollCh36")}
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
          {poseChoices.length ? (
            <div className="speak-picks" role="group" aria-label={text(locale, "speakPick")}>
              <p className="hint">
                {poseFromCatalog ? text(locale, "speakCatalog") : text(locale, "speakPick")}
                {` ${posePick + 1} / ${poseChoices.length}`}
              </p>
              <div className="speak-pick-row">
                {poseChoices.map((item, index) => (
                  <button
                    type="button"
                    key={`${item.summary}-${index}`}
                    className={index === posePick ? "is-on" : undefined}
                    aria-pressed={index === posePick}
                    onClick={() => showSpokenChoice(index)}
                  >
                    {item.summary}
                  </button>
                ))}
                <button type="button" onClick={() => showSpokenChoice((posePick + 1) % poseChoices.length)} disabled={poseChoices.length < 2}>
                  {text(locale, "speakNext")}
                </button>
                <button type="button" onClick={cancelSpoken}>
                  {text(locale, "speakCancel")}
                </button>
              </div>
            </div>
          ) : null}
          {previewUrl || sources.length ? (
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
                      bodyId={dollBody}
                      bodyLoading={text(locale, "dollLoading")}
                      bodyFailed={text(locale, "dollFailed")}
                      hint={
                        sources.length ? text(locale, "anatomyHint") : text(locale, "poseEmpty")
                      }
                      observedLabel={text(locale, "poseObserved")}
                      inferredLabel={text(locale, "poseInferred")}
                    />
                  ) : (
                    <div className={`stage-wrap${photoFlip ? " is-flipped" : ""}`}>
                      {/* blob URL は next/image に載せない */}
                      {previewUrl ? (
                        <img src={previewUrl} alt="" className={grayscale ? "is-gray" : undefined} />
                      ) : (
                        <div className="stage-blank" />
                      )}
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

        <section
          className={`card sources-pane${sourcesOpen ? "" : " is-collapsed"}`}
          aria-label={text(locale, "sourcesPane")}
        >
          <div className="sources-pane-head">
            <button
              type="button"
              className="sources-toggle"
              aria-expanded={sourcesOpen}
              aria-controls="sources-pane-body"
              onClick={() => setSourcesOpen((open) => !open)}
            >
              {sourcesOpen ? text(locale, "hideSources") : text(locale, "showSources")}
            </button>
          </div>
          <div id="sources-pane-body" hidden={!sourcesOpen}>
          <MaterialDesk
            locale={locale}
            materials={library}
            openIds={openMaterialIds}
            projectId={activeProjectId}
            onOpenIds={setOpenMaterialIds}
            onRecorded={() => {
              void refreshProjects();
            }}
            disabled={busy !== null}
          />
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
            {activeProjectId ? (
              <>
                <EvidenceLog
                  locale={locale}
                  project={projects.find((item) => item.project_id === activeProjectId)}
                />
                {projects.find((item) => item.project_id === activeProjectId) ? (
                  <ProjectMemo
                    locale={locale}
                    project={projects.find((item) => item.project_id === activeProjectId)!}
                    onSaved={(next) => {
                      setProjects((prev) =>
                        prev.map((item) => (item.project_id === next.project_id ? next : item)),
                      );
                    }}
                  />
                ) : null}
              </>
            ) : (
              <p className="hint">{text(locale, "evidenceOff")}</p>
            )}
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

          <label className="rights-query">
            <span>{text(locale, "rightsQuery")}</span>
            <input
              type="text"
              value={rightsQuery}
              maxLength={80}
              placeholder={text(locale, "rightsQueryPlaceholder")}
              disabled={!selected || busy !== null}
              onChange={(event) => setRightsQuery(event.target.value)}
            />
          </label>
          <p className="hint">{text(locale, "rightsQueryHint")}</p>

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
                  {item.cached ? <p className="hint">{text(locale, "cachedLookup")}</p> : null}
                  {item.search_skipped ? <p className="hint">{text(locale, "rightsSkipped")}</p> : null}
                  <p>{item.summary}</p>
                  <WebImageGrid locale={locale} images={item.web_images ?? []} />
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
                  {(item.materials ?? []).length ? (
                    <p className="hint">
                      {text(locale, "libraryDesk")}: {(item.materials ?? []).map((row) => row.title).join("、")}
                    </p>
                  ) : null}
                  {(item.memory ?? []).length ? (
                    <p className="hint">
                      {text(locale, "chatMemory")}:{" "}
                      {(item.memory ?? [])
                        .map((row) => `${row.project_name} / ${row.title}`)
                        .join("、")}
                    </p>
                  ) : null}
                  {item.sources.length ? (
                    <>
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
                    </>
                  ) : null}
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
          </div>
        </section>
      </div>
      <p className="status">
        {apiUp === null ? "" : apiUp ? text(locale, "apiOk") : text(locale, "apiDown")}
      </p>
    </main>
  );
}

function EvidenceLog({
  locale,
  project,
}: {
  locale: Locale;
  project: Project | undefined;
}) {
  const photos = project?.photos ?? [];
  const calls = project?.library_calls ?? [];
  const prompts = project?.prompts ?? [];
  const citations = project?.citations ?? [];
  if (!photos.length && !calls.length && !prompts.length && !citations.length) {
    return <p className="hint">{text(locale, "evidenceEmpty")}</p>;
  }
  return (
    <div className="evidence-log">
      <p className="hint">{text(locale, "evidencePhotos")}</p>
      <ul>
        {photos.map((item) => (
          <li key={item.photo_id}>
            {item.photo_id.slice(0, 8)} {formatViewedAt(item.at)}
          </li>
        ))}
      </ul>
      <p className="hint">{text(locale, "evidenceLibrary")}</p>
      <ul>
        {calls.map((item) => (
          <li key={item.doc_id}>
            {item.title}（{text(locale, item.via === "chat" ? "evidenceViaChat" : "evidenceViaOpen")}）
          </li>
        ))}
      </ul>
      <p className="hint">{text(locale, "evidencePrompts")}</p>
      <ul>
        {prompts.map((item, index) => (
          <li key={`${item.at}-${index}`}>
            <details>
              <summary>
                {item.label} {formatViewedAt(item.at)}
              </summary>
              <p className="prompt-text">{item.message}</p>
              <p className="hint prompt-text">{item.answer}</p>
            </details>
          </li>
        ))}
      </ul>
      <p className="hint">{text(locale, "evidenceCitations")}</p>
      <ul>
        {citations.map((item, index) => (
          <li key={`${item.doc_id}-${item.at}-${index}`}>
            {item.title} / {item.term}
            {item.cached ? `（${text(locale, "evidenceCached")}）` : ""}
            <ul>
              {item.sources.map((source) => (
                <li key={source.url || source.title}>
                  {source.title || source.url} / {shown(locale, source.license)} / {shown(locale, source.copyright)} / {shown(locale, source.created)}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}

function shown(locale: Locale, value: string | undefined): string {
  const textValue = (value || "").trim();
  if (!textValue || textValue === "unknown") {
    return text(locale, "unknown");
  }
  return textValue;
}

function WebImageGrid({ locale, images }: { locale: Locale; images: WebImage[] }) {
  if (!images.length) {
    return null;
  }
  return (
    <div className="web-images">
      <p className="hint">{text(locale, "webImagesNote")}</p>
      <ul>
        {images.map((image) => {
          const href = image.page_url || image.url;
          const label =
            image.match === "full"
              ? text(locale, "webImageFull")
              : image.match === "partial"
                ? text(locale, "webImagePartial")
                : text(locale, "webImageSimilar");
          return (
            <li key={image.url}>
              <a href={href} target="_blank" rel="noreferrer">
                <img src={image.url} alt={label} />
                <span>{label}</span>
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
