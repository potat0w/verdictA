import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const HOP_BY_HOP = new Set([
  "host",
  "connection",
  "content-length",
  "transfer-encoding",
  "keep-alive",
  "upgrade",
  "proxy-connection",
  "te",
  "trailer",
]);

function backendOrigins() {
  const configured =
    process.env.VERDICT_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "https://verdicta-1.onrender.com";
  const origins = [configured.replace(/\/$/, "")];
  const fallback = "https://red-lemons-change.loca.lt";
  if (!origins.includes(fallback)) origins.push(fallback);
  return origins;
}

function unavailable() {
  return Response.json(
    { detail: "The legal service is unavailable. Try again in a minute." },
    { status: 503 }
  );
}

function isApiError(body: ArrayBuffer) {
  const text = new TextDecoder().decode(body).trim();
  if (!text.startsWith("{")) return false;
  try {
    const data = JSON.parse(text) as unknown;
    return data !== null && typeof data === "object";
  } catch {
    return false;
  }
}

async function forward(request: NextRequest, path: string[]) {
  if (path.some((part) => part === ".." || part === "." || part === "")) {
    return Response.json({ detail: "Not found." }, { status: 404 });
  }

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  headers.set("Bypass-Tunnel-Reminder", "true");

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  let upstream: Response | null = null;
  for (const origin of backendOrigins()) {
    try {
      upstream = await fetch(`${origin}/${path.join("/")}${request.nextUrl.search}`, {
        method: request.method,
        headers,
        body,
        redirect: "manual",
        cache: "no-store",
      });
    } catch {
      upstream = null;
      continue;
    }
    if (upstream.status !== 502 && upstream.status !== 503) break;
    const failed = await upstream.clone().arrayBuffer();
    // A JSON 503 is a real API error, such as a missing index. A plain
    // gateway page is not, so try the next origin.
    if (upstream.status === 503 && isApiError(failed)) break;
  }

  if (!upstream) return unavailable();

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) responseHeaders.set(key, value);
  });

  const payload = await upstream.arrayBuffer();
  if (
    (upstream.status === 502 || upstream.status === 503) &&
    !isApiError(payload)
  ) {
    return unavailable();
  }

  return new Response(payload, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

type Context = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: Context) {
  const { path } = await context.params;
  return forward(request, path);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
