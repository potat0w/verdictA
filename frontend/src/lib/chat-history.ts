export type StoredMessage = {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: string;
};

export type ChatSession = {
  id: string;
  title: string;
  messages: StoredMessage[];
  updatedAt: string;
};

export const CHAT_RETENTION_DAYS = 3;

const SESSIONS_KEY = "verdictai_chat_sessions";
const ACTIVE_SESSION_KEY = "verdictai_active_session";
const RETENTION_MS = CHAT_RETENTION_DAYS * 24 * 60 * 60 * 1000;

function isBrowser() {
  return typeof window !== "undefined";
}

function parseSessions(raw: string | null): ChatSession[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as ChatSession[];
    if (!Array.isArray(parsed)) return [];
    const cutoff = Date.now() - RETENTION_MS;
    return parsed
      .filter(
        (s) =>
          s?.id &&
          Array.isArray(s.messages) &&
          new Date(s.updatedAt).getTime() >= cutoff
      )
      .sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
  } catch {
    return [];
  }
}

export function loadChatSessions(): ChatSession[] {
  if (!isBrowser()) return [];
  const sessions = parseSessions(localStorage.getItem(SESSIONS_KEY));
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
  return sessions;
}

export function saveChatSessions(sessions: ChatSession[]) {
  if (!isBrowser()) return;
  const cutoff = Date.now() - RETENTION_MS;
  const valid = sessions
    .filter((s) => new Date(s.updatedAt).getTime() >= cutoff)
    .sort(
      (a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(valid));
}

export function getActiveSessionId(): string | null {
  if (!isBrowser()) return null;
  return localStorage.getItem(ACTIVE_SESSION_KEY);
}

export function setActiveSessionId(id: string | null) {
  if (!isBrowser()) return;
  if (id) localStorage.setItem(ACTIVE_SESSION_KEY, id);
  else localStorage.removeItem(ACTIVE_SESSION_KEY);
}

export function createSessionId() {
  return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export function sessionTitleFromMessages(messages: StoredMessage[]) {
  const firstUser = messages.find((m) => m.role === "user");
  if (!firstUser) return "New chat";
  const text = firstUser.content.trim();
  if (text.length <= 42) return text;
  return `${text.slice(0, 42)}…`;
}

export function upsertChatSession(
  sessions: ChatSession[],
  session: ChatSession
): ChatSession[] {
  const next = sessions.filter((s) => s.id !== session.id);
  next.unshift(session);
  return next;
}
