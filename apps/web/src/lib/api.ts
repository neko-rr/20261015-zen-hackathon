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

export type Source = {
  url: string;
  title: string;
  license: string;
  created: string;
  copyright: string;
};

export type Lookup = {
  object_id: string;
  summary: string;
  sources: Source[];
  search_suggestions_html: string;
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
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8000";
  return raw.replace(/\/$/, "");
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
}> {
  if (!file || file.size <= 0) {
    throw new ApiError("写真が空です。", "invalid_image");
  }

  const body = new FormData();
  body.append("file", file);

  try {
    const response = await fetch(`${apiBase()}/photos`, {
      method: "POST",
      body,
      signal: AbortSignal.timeout(ANALYZE_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw await readFailure(response);
    }
    return (await response.json()) as { photo_id: string; objects: PhotoObject[] };
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error("analyze request failed", error);
    throw new ApiError("解析に失敗しました。", "analysis_failed");
  }
}

export async function lookupObject(photoId: string, objectId: string): Promise<Lookup> {
  if (!photoId.trim() || !objectId.trim()) {
    throw new ApiError("物体が見つかりません。", "object_not_found");
  }

  try {
    const response = await fetch(`${apiBase()}/photos/${encodeURIComponent(photoId)}/lookups`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ object_id: objectId }),
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
