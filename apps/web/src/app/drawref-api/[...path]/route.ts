import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const SKIP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const base = process.env.API_BASE_URL?.trim().replace(/\/$/, "") ?? "";
  if (!base) {
    return NextResponse.json(
      { error: { code: "config_missing", message: "API の接続先が未設定です。" } },
      { status: 500 },
    );
  }
  const { path } = await context.params;
  const target = `${base}/${path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!SKIP.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers,
    redirect: "manual",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
    init.duplex = "half";
  }
  let response: Response;
  try {
    response = await fetch(target, init);
  } catch (error) {
    console.error("api proxy failed", error);
    return NextResponse.json(
      { error: { code: "api_unreachable", message: "API に接続できませんでした。" } },
      { status: 502 },
    );
  }
  const out = new Headers();
  response.headers.forEach((value, key) => {
    if (key.toLowerCase() === "set-cookie" || SKIP.has(key.toLowerCase())) {
      return;
    }
    out.set(key, value);
  });
  for (const cookie of response.headers.getSetCookie()) {
    out.append("set-cookie", cookie);
  }
  return new NextResponse(response.body, { status: response.status, headers: out });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
