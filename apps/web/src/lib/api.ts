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

export type PoseData = {
  landmarks: PoseLandmark[];
  edges: PoseEdge[];
  muscles: Joint[];
};

export type PhotoObject = {
  object_id: string;
  label: string;
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
};

export type Project = {
  project_id: string;
  name: string;
  created_at: string;
};

export type Lookup = {
  object_id: string;
  object_label?: string;
  viewed_at?: string;
  summary: string;
  sources: LookupSource[];
  search_suggestions_html: string;
};

export type ChatTurn = {
  object_id: string;
  object_label?: string;
  viewed_at?: string;
  message: string;
  answer: string;
  sources: Source[];
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

export async function ensureSession(): Promise<{ session_id: string; kind: string }> {
  try {
    const response = await apiFetch("/sessions", {
      method: "POST",
      signal: AbortSignal.timeout(SESSION_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as { session_id: string; kind: string };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("session request failed", error);
    throw new ApiError("セッションを開始できませんでした。", "session_failed");
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

export async function analyzePhoto(file: File): Promise<{
  photo_id: string;
  objects: PhotoObject[];
  pose: PoseData;
}> {
  if (!file || file.size <= 0) {
    throw new ApiError("写真が空です。", "invalid_image");
  }

  const body = new FormData();
  body.append("file", file);

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
    };
    return {
      photo_id: raw.photo_id,
      objects: raw.objects,
      pose: raw.pose ?? { landmarks: [], edges: [], muscles: [] },
    };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("analyze request failed", error);
    throw new ApiError("解析に失敗しました。", "analysis_failed");
  }
}

export async function lookupObject(
  photoId: string,
  objectId: string,
  options: { tags?: string[]; project_id?: string } = {},
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
