/** 画面は公開 API の URL だけを知る。Gemini は呼ばない。 */

export type Box = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type Joint = {
  name: string;
  x: number;
  y: number;
};

export type ContourPoint = {
  x: number;
  y: number;
};

export type PoseLandmark = {
  index: number;
  name: string;
  x: number;
  y: number;
  z: number;
  visibility: number;
};

export type PoseEdge = {
  start: number;
  end: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

export type MannequinJoint = {
  id: string;
  parent: string | null;
  x: number;
  y: number;
  z: number;
  inferred: boolean;
  hinge: [number, number, number];
};

export type MannequinBone = {
  id: string;
  start: string;
  end: string;
  part: string;
  inferred: boolean;
  radius: number;
};

export type MannequinHead = {
  joint_id: string;
  radius: number;
  inferred: boolean;
};

export type Mannequin = {
  joints: MannequinJoint[];
  bones: MannequinBone[];
  head: MannequinHead | null;
  aspect?: number;
};

export type HandDetection = {
  side: string;
  score: number;
  landmarks: Array<{ index: number; x: number; y: number; z: number }>;
};

export type PosePerson = {
  object_id?: string;
  landmarks: PoseLandmark[];
  edges: PoseEdge[];
  muscles: Joint[];
  hands?: HandDetection[];
  mannequin?: Mannequin;
};

export type PoseData = {
  landmarks: PoseLandmark[];
  edges: PoseEdge[];
  muscles: Array<Joint & { person_index?: number }>;
  hands?: HandDetection[];
  mannequin?: Mannequin;
  people?: PosePerson[];
};

export type PhotoObject = {
  object_id: string;
  label: string;
  public_name?: string;
  work_title?: string;
  kind: string;
  is_primary: boolean;
  box: Box | null;
  joints: Joint[];
  muscles: Joint[];
  contour: ContourPoint[];
};

export type JevScores = {
  about: number | null;
  license: number | null;
  created: number | null;
  copyright: number | null;
};

export type MaterialKind = "own_work" | "third_party" | "web";

export type RiskLevel = "easy" | "conditional" | "review";

export type LookupSource = {
  url: string;
  title: string;
  material_kind?: MaterialKind;
  license?: string;
  created?: string;
  copyright?: string;
  rights_code?: string;
  risk_level?: RiskLevel;
  credit_memo?: string;
};

export type Source = {
  url: string;
  title: string;
  license: string;
  created: string;
  copyright: string;
  material_kind?: MaterialKind;
  rights_code?: string;
  protection_until?: string;
  risk_level?: RiskLevel;
  credit_memo?: string;
  jev: JevScores;
};

export type Material = {
  doc_id: string;
  material_kind: "own_work" | "third_party";
  media_type: string;
  title: string;
  byte_size: number;
  page: string;
  project_id: string;
  tags: string[];
  created_at: string;
  text?: string;
  citation?: {
    term: string;
    searched_at: string;
    summary: string;
    sources: LookupSource[];
  } | null;
};

export type LibraryHit = {
  doc_id: string;
  title: string;
  material_kind: "own_work" | "third_party" | "web";
  text: string;
};

export type ProjectPhoto = {
  photo_id: string;
  at: string;
};

export type ProjectLibraryCall = {
  doc_id: string;
  title: string;
  via: "open" | "chat";
  at: string;
};

export type ProjectCitation = {
  doc_id: string;
  title: string;
  term: string;
  searched_at: string;
  at: string;
  cached: boolean;
  sources: LookupSource[];
};

export type ProjectPrompt = {
  at: string;
  label: string;
  message: string;
  answer: string;
};

export type Project = {
  project_id: string;
  name: string;
  created_at: string;
  photos?: ProjectPhoto[];
  library_calls?: ProjectLibraryCall[];
  citations?: ProjectCitation[];
  prompts?: ProjectPrompt[];
  memo?: string;
};

export type WebPage = {
  url: string;
  title: string;
};

export type Lookup = {
  object_id: string;
  object_label?: string;
  viewed_at?: string;
  summary: string;
  sources: LookupSource[];
  search_suggestions_html: string;
  cached?: boolean;
  search_skipped?: boolean;
  searched_at?: string;
};

export type ProjectMemoryHit = {
  source: "memo" | "prompt" | "citation";
  project_id: string;
  project_name: string;
  title: string;
  text: string;
};

export type ChatTurn = {
  object_id: string;
  object_label?: string;
  viewed_at?: string;
  message: string;
  answer: string;
  sources: Source[];
  materials?: LibraryHit[];
  memory?: ProjectMemoryHit[];
  search_suggestions_html?: string;
};

export class ApiError extends Error {
  readonly code: string;

  constructor(message: string, code: string) {
    super(message);
    this.code = code;
  }
}

const ANALYZE_TIMEOUT_MS = 90_000;
const LOOKUP_TIMEOUT_MS = 90_000;
const HEALTH_TIMEOUT_MS = 5_000;

export function apiBase(): string {
  const raw = (process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8000").replace(
    /\/$/,
    "",
  );
  if (raw.startsWith("/")) {
    if (typeof window === "undefined") {
      return raw;
    }
    return `${window.location.origin}${raw}`;
  }
  // localhost と 127.0.0.1 は別オリジン。Cookie が乗らないので画面のホストに揃える
  if (typeof window === "undefined") {
    return raw;
  }
  try {
    const api = new URL(raw);
    const pageHost = window.location.hostname;
    const localHosts = new Set(["localhost", "127.0.0.1"]);
    if (localHosts.has(pageHost) && localHosts.has(api.hostname)) {
      api.hostname = pageHost;
    }
    return api.origin;
  } catch {
    return raw;
  }
}

function httpsUrl(raw: string): string | null {
  if (!raw) {
    return null;
  }
  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== "https:") {
      return null;
    }
    return parsed.toString();
  } catch {
    return null;
  }
}

export function sourceHref(raw: string): string | null {
  if (!raw || raw.startsWith("material://")) {
    return null;
  }
  return httpsUrl(raw);
}

async function readFailure(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as {
      error?: { code?: string; message?: string };
    };
    const message = body.error?.message?.trim() || "失敗しました。";
    const code = body.error?.code?.trim() || "request_failed";
    return new ApiError(message, code);
  } catch (error) {
    console.error("api error body unreadable", error);
    return new ApiError("失敗しました。", "request_failed");
  }
}

const SESSION_TIMEOUT_MS = 10_000;

/** Cookie 付き。セッション必須の API で使う。 */
function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${apiBase()}${path}`, {
    ...init,
    credentials: "include",
  });
}

export type SessionInfo = { session_id: string; kind: string; username?: string };

export async function currentSession(): Promise<SessionInfo | null> {
  try {
    const response = await apiFetch("/sessions/me", {
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (response.status === 401) {
      return null;
    }
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as SessionInfo;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("session read failed", error);
    return null;
  }
}

export async function loginAccount(username: string, password: string): Promise<SessionInfo> {
  return postAccount("/accounts/login", username, password);
}

export async function registerAccount(username: string, password: string): Promise<SessionInfo> {
  return postAccount("/accounts", username, password);
}

export async function suggestUsername(): Promise<string> {
  try {
    const response = await apiFetch("/accounts/suggestions", {
      method: "POST",
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const body = (await response.json()) as { username?: string };
    const name = body.username?.trim() || "";
    if (!name) {
      throw new ApiError("空いている名前を用意できませんでした。", "username_unavailable");
    }
    return name;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("username suggestion failed", error);
    throw new ApiError("空いている名前を用意できませんでした。", "username_unavailable");
  }
}

export async function logoutAccount(): Promise<void> {
  try {
    const response = await apiFetch("/accounts/logout", {
      method: "POST",
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("logout failed", error);
    throw new ApiError("ログアウトに失敗しました。", "logout_failed");
  }
}

async function postAccount(path: string, username: string, password: string): Promise<SessionInfo> {
  try {
    const response = await apiFetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as SessionInfo;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("account request failed", error);
    throw new ApiError("ログインに失敗しました。", "account_failed");
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${apiBase()}/health`, {
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });
    return response.ok;
  } catch (error) {
    console.error("health check failed", error);
    return false;
  }
}

export type FileFacts = {
  artist: string;
  copyright: string;
  copyright_url: string;
  image_id: string;
  credit: string;
  c2pa: "present" | "absent" | string;
  c2pa_generator: string;
};

function emptyFileFacts(): FileFacts {
  return {
    artist: "unknown",
    copyright: "unknown",
    copyright_url: "unknown",
    image_id: "unknown",
    credit: "unknown",
    c2pa: "absent",
    c2pa_generator: "unknown",
  };
}

export async function analyzePhoto(
  file: File,
  projectId = "",
): Promise<{
  photo_id: string;
  objects: PhotoObject[];
  pose: PoseData;
  labels_pending: boolean;
  file_facts: FileFacts;
  web_pages: WebPage[];
}> {
  if (!file || file.size <= 0) {
    throw new ApiError("写真が空です。", "invalid_image");
  }

  const body = new FormData();
  body.append("file", file);
  if (projectId.trim()) {
    body.append("project_id", projectId.trim());
  }

  try {
    const response = await apiFetch("/photos", {
      method: "POST",
      body,
      signal: AbortSignal.timeout(ANALYZE_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const raw = (await response.json()) as {
      photo_id: string;
      objects: PhotoObject[];
      pose?: PoseData;
      labels_pending?: boolean;
      file_facts?: FileFacts;
      web_pages?: WebPage[];
    };
    return {
      photo_id: raw.photo_id,
      objects: raw.objects,
      pose: raw.pose ?? { landmarks: [], edges: [], muscles: [] },
      labels_pending: Boolean(raw.labels_pending),
      file_facts: raw.file_facts ?? emptyFileFacts(),
      web_pages: raw.web_pages ?? [],
    };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("analyze request failed", error);
    throw new ApiError("解析に失敗しました。", "analysis_failed");
  }
}

export type SpokenPoseOption = {
  summary: string;
  mirrored: boolean;
  upper_deg: number;
  lower_deg: number;
  bends: Record<string, number>;
};

export type SpokenPose = {
  mannequin: Mannequin;
  options: SpokenPoseOption[];
  pose_source?: "catalog" | "cache" | "new";
};

export async function speakPose(message: string): Promise<SpokenPose> {
  const text = message.trim();
  if (!text) {
    throw new ApiError("言葉を入れてください。", "empty_message");
  }
  try {
    const response = await apiFetch("/poses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
      signal: AbortSignal.timeout(ANALYZE_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const raw = (await response.json()) as SpokenPose;
    const options = (raw.options ?? [])
      .slice(0, 3)
      .map((item) => ({
        summary: item.summary || "言葉のポーズ",
        mirrored: Boolean(item.mirrored),
        upper_deg: Number(item.upper_deg) || 0,
        lower_deg: Number(item.lower_deg) || 0,
        bends: item.bends ?? {},
      }));
    return {
      mannequin: raw.mannequin ?? { joints: [], bones: [], head: null },
      options: options.length ? options : [{ summary: "言葉のポーズ", mirrored: false, upper_deg: 0, lower_deg: 0, bends: {} }],
      pose_source: raw.pose_source,
    };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("spoken pose failed", error);
    throw new ApiError("ポーズを読めませんでした。", "spoken_pose_failed");
  }
}

export async function transcribePose(audio: Blob, language: "ja" | "en"): Promise<string> {
  if (!audio.size) {
    throw new ApiError("録音が空です。もう一度話すか、言葉を入力してください。", "speech_empty");
  }
  const body = new FormData();
  body.set("file", audio, "pose.wav");
  body.set("language", language);
  try {
    const response = await apiFetch("/poses/speech", {
      method: "POST",
      body,
      signal: AbortSignal.timeout(ANALYZE_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const raw = (await response.json()) as { text?: string };
    return (raw.text ?? "").trim();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("speech failed", error);
    throw new ApiError("音声認識を使えませんでした。言葉を入力してください。", "speech_unavailable");
  }
}

export async function getPhoto(photoId: string): Promise<{
  photo_id: string;
  objects: PhotoObject[];
  pose: PoseData;
  labels_pending: boolean;
  file_facts: FileFacts;
  web_pages: WebPage[];
}> {
  if (!photoId.trim()) {
    throw new ApiError("写真が見つかりません。", "object_not_found");
  }
  try {
    const response = await apiFetch(`/photos/${encodeURIComponent(photoId)}`, {
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const raw = (await response.json()) as {
      photo_id: string;
      objects: PhotoObject[];
      pose?: PoseData;
      labels_pending?: boolean;
      file_facts?: FileFacts;
      web_pages?: WebPage[];
    };
    return {
      photo_id: raw.photo_id,
      objects: raw.objects,
      pose: raw.pose ?? { landmarks: [], edges: [], muscles: [] },
      labels_pending: Boolean(raw.labels_pending),
      file_facts: raw.file_facts ?? emptyFileFacts(),
      web_pages: raw.web_pages ?? [],
    };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("photo read failed", error);
    throw new ApiError("写真を読み直せませんでした。", "analysis_failed");
  }
}

export async function lookupObject(
  photoId: string,
  objectId: string,
  options: { tags?: string[]; project_id?: string; query?: string } = {},
): Promise<Lookup> {
  if (!photoId.trim() || !objectId.trim()) {
    throw new ApiError("物体が見つかりません。", "object_not_found");
  }

  try {
    const response = await apiFetch(`/photos/${encodeURIComponent(photoId)}/lookups`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        object_id: objectId,
        tags: options.tags ?? [],
        project_id: options.project_id ?? "",
        query: options.query ?? "",
      }),
      signal: AbortSignal.timeout(LOOKUP_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as Lookup;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("lookup request failed", error);
    throw new ApiError("調べものに失敗しました。", "lookup_failed");
  }
}

export async function askQuestion(
  photoId: string,
  objectId: string,
  message: string,
  options: { tags?: string[]; project_id?: string } = {},
): Promise<ChatTurn> {
  if (!photoId.trim() || !objectId.trim()) {
    throw new ApiError("物体が見つかりません。", "object_not_found");
  }
  const trimmed = message.trim();
  if (!trimmed) {
    throw new ApiError("質問を入力してください。", "empty_message");
  }

  try {
    const response = await apiFetch(`/photos/${encodeURIComponent(photoId)}/questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        object_id: objectId,
        message: trimmed,
        tags: options.tags ?? [],
        project_id: options.project_id ?? "",
      }),
      signal: AbortSignal.timeout(LOOKUP_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as ChatTurn;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("question request failed", error);
    throw new ApiError("調べものに失敗しました。", "lookup_failed");
  }
}

const MATERIAL_TIMEOUT_MS = 120_000;

export async function listMaterials(
  projectId = "",
): Promise<{ materials: Material[]; tags: string[] }> {
  try {
    const query = projectId.trim()
      ? `?project_id=${encodeURIComponent(projectId.trim())}`
      : "";
    const response = await apiFetch(`/materials${query}`, {
      method: "GET",
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const body = (await response.json()) as { materials: Material[]; tags?: string[] };
    return { materials: body.materials ?? [], tags: body.tags ?? [] };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("list materials failed", error);
    throw new ApiError("資料一覧を取得できませんでした。", "material_failed");
  }
}

export async function uploadMaterials(
  kind: "own_work" | "third_party",
  files: File[],
  projectId = "",
): Promise<{ materials: Material[]; errors: { filename: string; message: string }[] }> {
  if (!files.length) {
    throw new ApiError("ファイルを選んでください。", "invalid_material");
  }
  const body = new FormData();
  for (const file of files) {
    body.append("files", file);
  }
  const params = new URLSearchParams({ material_kind: kind });
  if (projectId.trim()) {
    params.set("project_id", projectId.trim());
  }
  try {
    const response = await apiFetch(`/materials?${params.toString()}`, {
      method: "POST",
      body,
      signal: AbortSignal.timeout(MATERIAL_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as {
      materials: Material[];
      errors: { filename: string; message: string }[];
    };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("upload materials failed", error);
    throw new ApiError("資料の保存に失敗しました。", "material_failed");
  }
}

export async function patchMaterial(
  docId: string,
  patch: { tags?: string[]; project_id?: string },
): Promise<Material> {
  if (!docId.trim()) {
    throw new ApiError("資料が見つかりません。", "object_not_found");
  }
  try {
    const response = await apiFetch(`/materials/${encodeURIComponent(docId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const body = (await response.json()) as { material: Material };
    return body.material;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("patch material failed", error);
    throw new ApiError("資料の更新に失敗しました。", "material_failed");
  }
}

export async function deleteMaterial(docId: string): Promise<void> {
  if (!docId.trim()) {
    throw new ApiError("資料が見つかりません。", "object_not_found");
  }
  try {
    const response = await apiFetch(`/materials/${encodeURIComponent(docId)}`, {
      method: "DELETE",
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("delete material failed", error);
    throw new ApiError("資料の削除に失敗しました。", "material_failed");
  }
}

export async function readMaterial(docId: string): Promise<Material> {
  if (!docId.trim()) {
    throw new ApiError("資料が見つかりません。", "object_not_found");
  }
  try {
    const response = await apiFetch(`/materials/${encodeURIComponent(docId)}`, {
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const body = (await response.json()) as { material: Material };
    return body.material;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("read material failed", error);
    throw new ApiError("資料を開けませんでした。", "material_failed");
  }
}

export async function citeMaterial(docId: string, query = "", projectId = ""): Promise<Lookup> {
  if (!docId.trim()) {
    throw new ApiError("資料が見つかりません。", "object_not_found");
  }
  try {
    const response = await apiFetch(`/materials/${encodeURIComponent(docId)}/lookups`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, project_id: projectId }),
      signal: AbortSignal.timeout(LOOKUP_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as Lookup;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("cite material failed", error);
    throw new ApiError("出典を確認できませんでした。", "lookup_failed");
  }
}

export type AccountPreferences = {
  citation_refresh_days: number;
  locale: string;
  theme_id: string;
};

export async function accountPreferences(): Promise<AccountPreferences> {
  try {
    const response = await apiFetch("/preferences", {
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as AccountPreferences;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("preference read failed", error);
    throw new ApiError("設定を読めませんでした。", "preference_failed");
  }
}

export async function saveAccountPreferences(patch: {
  citation_refresh_days?: number;
  locale?: string;
  theme_id?: string;
}): Promise<AccountPreferences> {
  try {
    const response = await apiFetch("/preferences", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as AccountPreferences;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("preference write failed", error);
    throw new ApiError("設定を保存できませんでした。", "preference_failed");
  }
}

export async function citationRefreshDays(): Promise<number> {
  try {
    const response = await apiFetch("/preferences", {
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const body = (await response.json()) as { citation_refresh_days: number };
    return body.citation_refresh_days;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("preference read failed", error);
    throw new ApiError("設定を読めませんでした。", "material_failed");
  }
}

export async function saveCitationRefreshDays(days: number): Promise<number> {
  try {
    const response = await apiFetch("/preferences", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ citation_refresh_days: days }),
      signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const body = (await response.json()) as { citation_refresh_days: number };
    return body.citation_refresh_days;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("preference write failed", error);
    throw new ApiError("設定を保存できませんでした。", "material_failed");
  }
}

export async function listProjects(): Promise<Project[]> {
  try {
    const response = await apiFetch("/projects", {
      method: "GET",
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const body = (await response.json()) as { projects: Project[] };
    return body.projects ?? [];
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("list projects failed", error);
    throw new ApiError("案件一覧を取得できませんでした。", "material_failed");
  }
}

export async function noteProjectLibrary(projectId: string, docId: string): Promise<void> {
  if (!projectId.trim() || !docId.trim()) {
    return;
  }
  try {
    const response = await apiFetch(`/projects/${encodeURIComponent(projectId)}/library-calls`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_id: docId }),
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("note library call failed", error);
    throw new ApiError("資料の記録を残せませんでした。", "material_failed");
  }
}

export async function saveProjectMemo(projectId: string, memo: string): Promise<Project> {
  if (!projectId.trim()) {
    throw new ApiError("案件が見つかりません。", "object_not_found");
  }
  if (memo.length > 20000) {
    throw new ApiError("メモが長すぎます。", "invalid_memo");
  }
  try {
    const response = await apiFetch(`/projects/${encodeURIComponent(projectId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ memo }),
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const body = (await response.json()) as { project: Project };
    return body.project;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("save project memo failed", error);
    throw new ApiError("メモを保存できませんでした。", "material_failed");
  }
}

export async function createProject(name: string): Promise<Project> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new ApiError("案件名を入力してください。", "invalid_project");
  }
  try {
    const response = await apiFetch("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: trimmed }),
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    const body = (await response.json()) as { project: Project };
    return body.project;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("create project failed", error);
    throw new ApiError("案件の作成に失敗しました。", "material_failed");
  }
}

export async function deleteProject(projectId: string): Promise<void> {
  if (!projectId.trim()) {
    throw new ApiError("案件が見つかりません。", "object_not_found");
  }
  try {
    const response = await apiFetch(`/projects/${encodeURIComponent(projectId)}`, {
      method: "DELETE",
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("delete project failed", error);
    throw new ApiError("案件の削除に失敗しました。", "material_failed");
  }
}
