"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bot, MessageSquare, Palette, Plus, Scale, Send, User, X } from "lucide-react";
import { askLegalQuestion } from "@/lib/api";
import {
  CHAT_RETENTION_DAYS,
  ChatSession,
  StoredMessage,
  createSessionId,
  getActiveSessionId,
  loadChatSessions,
  saveChatSessions,
  sessionTitleFromMessages,
  setActiveSessionId,
  upsertChatSession,
} from "@/lib/chat-history";
import { QUICK_SUGGESTIONS } from "@/lib/demo-questions";
import { cn } from "@/lib/theme";
import MessageContent from "./MessageContent";
import AppearanceSettings from "./AppearanceSettings";

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
}

interface ChatPanelProps {
  onClose: () => void;
}

function toStored(messages: Message[]): StoredMessage[] {
  return messages.map((m) => ({
    id: m.id,
    content: m.content,
    role: m.role,
    timestamp: m.timestamp.toISOString(),
  }));
}

function fromStored(messages: StoredMessage[]): Message[] {
  return messages.map((m) => ({
    id: m.id,
    content: m.content,
    role: m.role,
    timestamp: new Date(m.timestamp),
  }));
}

export default function ChatPanel({ onClose }: ChatPanelProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionIdState] = useState<string | null>(
    null
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [historyReady, setHistoryReady] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const loaded = loadChatSessions();
    setSessions(loaded);
    const savedActiveId = getActiveSessionId();
    const active = loaded.find((s) => s.id === savedActiveId);
    if (active) {
      setActiveSessionIdState(active.id);
      setMessages(fromStored(active.messages));
    }
    setHistoryReady(true);
  }, []);

  const persistSession = useCallback(
    (sessionId: string, nextMessages: Message[]) => {
      const stored = toStored(nextMessages);
      const session: ChatSession = {
        id: sessionId,
        title: sessionTitleFromMessages(stored),
        messages: stored,
        updatedAt: new Date().toISOString(),
      };
      setSessions((prev) => {
        const updated = upsertChatSession(prev, session);
        saveChatSessions(updated);
        return updated;
      });
    },
    []
  );

  useEffect(() => {
    if (!historyReady || !activeSessionId || messages.length === 0) return;
    persistSession(activeSessionId, messages);
  }, [messages, activeSessionId, historyReady, persistSession]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [activeSessionId]);

  const startNewChat = () => {
    setActiveSessionIdState(null);
    setActiveSessionId(null);
    setMessages([]);
    setInput("");
    inputRef.current?.focus();
  };

  const openSession = (session: ChatSession) => {
    setActiveSessionIdState(session.id);
    setActiveSessionId(session.id);
    setMessages(fromStored(session.messages));
    setInput("");
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    let sessionId = activeSessionId;
    if (!sessionId) {
      sessionId = createSessionId();
      setActiveSessionIdState(sessionId);
      setActiveSessionId(sessionId);
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text.trim(),
      role: "user",
      timestamp: new Date(),
    };

    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    persistSession(sessionId, nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      const data = await askLegalQuestion(text.trim());
      setMessages((prev) => {
        const withReply = [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            content: data.answer,
            role: "assistant" as const,
            timestamp: new Date(),
          },
        ];
        persistSession(sessionId!, withReply);
        return withReply;
      });
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : "Something went wrong.";
      setMessages((prev) => {
        const withError = [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            content: `Sorry, I couldn't answer that: ${detail}`,
            role: "assistant" as const,
            timestamp: new Date(),
          },
        ];
        persistSession(sessionId!, withError);
        return withError;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <>
      <div className="fixed inset-0 z-[100] flex min-h-0 bg-[var(--chat-bg)]">
        <aside className="hidden h-full w-[260px] shrink-0 flex-col border-r border-[var(--chat-border)] bg-[var(--chat-surface)] lg:flex">
          <div className="p-3">
            <button
              type="button"
              onClick={startNewChat}
              className="flex w-full items-center gap-2 rounded-xl border border-[var(--chat-border)] px-3 py-2.5 text-sm text-[var(--chat-text)] hover:bg-[var(--chat-hover)]"
            >
              <Plus className="h-4 w-4" />
              New chat
            </button>
          </div>

          <div className="chat-scroll flex-1 overflow-y-auto px-2 pb-2">
            {sessions.length > 0 ? (
              <div className="space-y-0.5">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => openSession(session)}
                    className={cn(
                      "flex w-full items-start gap-2 rounded-lg px-3 py-2.5 text-left text-sm hover:bg-[var(--chat-hover)]",
                      activeSessionId === session.id
                        ? "bg-[var(--chat-hover)] text-[var(--chat-text)]"
                        : "text-[var(--chat-text-muted)]"
                    )}
                  >
                    <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 opacity-60" />
                    <span className="line-clamp-2 leading-snug">
                      {session.title}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="px-3 py-2 text-xs text-[var(--chat-text-muted)]">
                No saved chats yet.
              </p>
            )}
          </div>

          <div className="border-t border-[var(--chat-border)] p-4">
            <div className="mb-2 flex items-center gap-2 px-1">
              <div className="chat-accent-icon flex h-8 w-8 items-center justify-center rounded-lg">
                <Scale className="h-4 w-4" />
              </div>
              <span className="text-sm font-semibold text-[var(--chat-text)]">
                VerdictAI
              </span>
            </div>
            <p className="text-[11px] leading-relaxed text-[var(--chat-text-muted)]">
              Chats saved for {CHAT_RETENTION_DAYS} days on this device. AI
              guidance only — not professional legal advice.
            </p>
          </div>
        </aside>

        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between px-4 py-3 md:px-6">
            <div className="flex items-center gap-2 lg:hidden">
              <button
                type="button"
                onClick={startNewChat}
                className="rounded-xl border border-[var(--chat-border)] p-2 text-[var(--chat-text-muted)] hover:bg-[var(--chat-hover)] hover:text-[var(--chat-text)]"
                aria-label="New chat"
              >
                <Plus className="h-5 w-5" />
              </button>
              <span className="text-sm font-semibold text-[var(--chat-text)]">
                VerdictAI
              </span>
            </div>
            <div className="hidden lg:block" />
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSettings(true)}
                className="rounded-xl border border-[var(--chat-border)] p-2 text-[var(--chat-text-muted)] hover:bg-[var(--chat-hover)] hover:text-[var(--chat-text)]"
                aria-label="Appearance settings"
              >
                <Palette className="h-5 w-5" />
              </button>
              <button
                onClick={onClose}
                className="rounded-xl border border-[var(--chat-border)] p-2 text-[var(--chat-text-muted)] hover:bg-[var(--chat-hover)] hover:text-[var(--chat-text)]"
                aria-label="Close chat"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </header>

          <div
            ref={scrollRef}
            className="chat-scroll flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4 md:px-6"
          >
            {isEmpty ? (
              <div className="flex min-h-full flex-col items-center justify-center px-4 text-center">
                <h3 className="font-merriweather text-2xl font-semibold text-[var(--chat-text)] md:text-3xl">
                  How can I help you today?
                </h3>
                <p className="mt-2 max-w-md text-sm text-[var(--chat-text-muted)]">
                  Ask about legal rights, constitutional law, or everyday
                  scenarios.
                </p>
              </div>
            ) : (
              <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-end">
                <div className="space-y-4">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={cn(
                        "flex gap-3",
                        message.role === "user"
                          ? "flex-row-reverse"
                          : "flex-row"
                      )}
                    >
                      <div
                        className={cn(
                          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                          message.role === "user"
                            ? "chat-accent-icon"
                            : "chat-bot-icon"
                        )}
                      >
                        {message.role === "user" ? (
                          <User className="h-4 w-4" />
                        ) : (
                          <Bot className="h-4 w-4" />
                        )}
                      </div>

                      <div
                        className={cn(
                          "min-w-0 flex-1",
                          message.role === "user"
                            ? "flex flex-col items-end"
                            : ""
                        )}
                      >
                        <div
                          className={cn(
                            message.role === "user"
                              ? "chat-user-bubble max-w-[85%] rounded-2xl rounded-tr-md px-4 py-3"
                              : "w-full rounded-2xl rounded-tl-md border border-[var(--chat-border)] bg-[var(--chat-bubble-assistant)] px-5 py-4"
                          )}
                        >
                          {message.role === "user" ? (
                            <p className="text-[15px] font-medium leading-relaxed">
                              {message.content}
                            </p>
                          ) : (
                            <MessageContent content={message.content} />
                          )}
                        </div>
                        <span className="mt-1.5 px-1 text-[11px] text-[var(--chat-text-muted)]">
                          {message.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </div>
                  ))}

                  {isLoading && (
                    <div className="flex gap-3">
                      <div className="chat-bot-icon flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
                        <Bot className="h-4 w-4" />
                      </div>
                      <div className="flex items-center gap-3 rounded-2xl rounded-tl-md border border-[var(--chat-border)] bg-[var(--chat-bubble-assistant)] px-4 py-3">
                        <div className="flex gap-1">
                          {[0, 150, 300].map((delay) => (
                            <span
                              key={delay}
                              className="h-2 w-2 animate-bounce rounded-full"
                              style={{
                                background:
                                  "color-mix(in srgb, var(--accent) 60%, transparent)",
                                animationDelay: `${delay}ms`,
                              }}
                            />
                          ))}
                        </div>
                        <span className="text-sm text-[var(--chat-text-muted)]">
                          Researching legal sources...
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="shrink-0 px-4 pb-4 md:px-6 md:pb-6">
            {isEmpty && (
              <div className="mx-auto mb-3 flex max-w-2xl flex-wrap justify-center gap-2">
                {QUICK_SUGGESTIONS.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => sendMessage(s.query)}
                    disabled={isLoading}
                    className="rounded-full border border-[var(--chat-border)] bg-[var(--chat-surface)] px-4 py-2 text-sm text-[var(--chat-text-muted)] hover:bg-[var(--chat-hover)] hover:text-[var(--chat-text)] disabled:opacity-50"
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}
            <form
              onSubmit={handleSubmit}
              className="mx-auto flex max-w-3xl items-end gap-2 rounded-[28px] border border-[var(--chat-border)] bg-[var(--chat-input-bg)] p-2 shadow-sm focus-within:ring-1"
              style={
                {
                  "--tw-ring-color":
                    "color-mix(in srgb, var(--accent) 20%, transparent)",
                } as React.CSSProperties
              }
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Message VerdictAI..."
                rows={1}
                className="max-h-32 min-h-[44px] flex-1 resize-none bg-transparent px-4 py-3 text-sm text-[var(--chat-text)] placeholder-[var(--chat-text-muted)] outline-none"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="chat-send-btn flex h-10 w-10 shrink-0 items-center justify-center rounded-full hover:brightness-110 disabled:opacity-30"
                aria-label="Send"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>
      </div>

      <AppearanceSettings
        open={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </>
  );
}
