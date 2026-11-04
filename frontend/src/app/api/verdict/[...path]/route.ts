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

function backendOrigin() {
  const configured =
    process.env.VERDICT_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "https://verdicta-1.onrender.com";
  return configured.replace(/\/$/, "");
}

function unavailable() {
  return Response.json(
    { detail: "The legal service is unavailable. Try again in a minute." },
    { status: 503 }
  );
}

async function forward(request: NextRequest, path: string[]) {
  if (path.some((part) => part === ".." || part === "." || part === "")) {
    return Response.json({ detail: "Not found." }, { status: 404 });
  }

  const target = `${backendOrigin()}/${path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.arrayBuffer();

  let upstream: Response | null = null;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      upstream = await fetch(target, {
        method: request.method,
        headers,
        body,
        redirect: "manual",
        cache: "no-store",
      });
    } catch {
      upstream = null;
    }
    if (upstream && upstream.status !== 502 && upstream.status !== 503) break;
    if (attempt === 0) await new Promise((resolve) => setTimeout(resolve, 2500));
  }

  if (!upstream) return unavailable();

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) responseHeaders.set(key, value);
  });

  const payload = await upstream.arrayBuffer();
  if (
    (upstream.status === 502 || upstream.status === 503) &&
    payload.byteLength === 0
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
