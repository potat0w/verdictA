import { getToken } from "./api";

export interface DecodedTokenPayload {
  sub?: string;
  exp?: number;
  iat?: number;
  [key: string]: unknown;
}

export function decodeJwt(token: string): DecodedTokenPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const json = typeof window !== "undefined" ? atob(padded) : Buffer.from(padded, "base64").toString("binary");
    // atob may return binary string; ensure proper UTF-8 decode
    const utf8 = decodeURIComponent(
      Array.prototype.map
        .call(json, (c: string) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(utf8);
  } catch {
    return null;
  }
}

export function getCurrentUser() {
  const token = getToken();
  if (!token) return null;
  const payload = decodeJwt(token);
  if (!payload || !payload.sub) return null;
  const expiresAtMs = payload.exp ? payload.exp * 1000 : undefined;
  return {
    username: payload.sub as string,
    expiresAtMs,
    rawToken: token,
  } as const;
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeJwt(token);
  if (!payload || !payload.exp) return true;
  return payload.exp * 1000 <= Date.now();
} 