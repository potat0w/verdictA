"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowUp, Menu, Moon, Plus, Scale, Sun, X } from "lucide-react";
import { askLegalQuestion } from "@/lib/api";
import {
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
import MessageContent from "./MessageContent";

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
}

interface ChatPanelProps {
  onClose: () => void;
}

const LANG_KEY = "verdictai-language";

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
  const [historyReady, setHistoryReady] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const [language, setLanguage] = useState<"en" | "bn">("en");
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const prevHtml = html.style.overflow;
    const prevBody = body.style.overflow;
    const prevTouch = body.style.touchAction;
    html.style.overflow = "hidden";
    body.style.overflow = "hidden";
    body.style.touchAction = "none";

    const setAppHeight = () => {
      const height = window.visualViewport?.height ?? window.innerHeight;
      html.style.setProperty("--app-height", `${height}px`);
    };
    setAppHeight();
    window.visualViewport?.addEventListener("resize", setAppHeight);
    window.visualViewport?.addEventListener("scroll", setAppHeight);
    window.addEventListener("resize", setAppHeight);

    return () => {
      html.style.overflow = prevHtml;
      body.style.overflow = prevBody;
      body.style.touchAction = prevTouch;
      html.style.removeProperty("--app-height");
      window.visualViewport?.removeEventListener("resize", setAppHeight);
      window.visualViewport?.removeEventListener("scroll", setAppHeight);
      window.removeEventListener("resize", setAppHeight);
    };
  }, []);

  useEffect(() => {
    const loaded = loadChatSessions();
    setSessions(loaded);
    const savedActiveId = getActiveSessionId();
    const active = loaded.find((s) => s.id === savedActiveId);
    if (active) {
      setActiveSessionIdState(active.id);
      setMessages(fromStored(active.messages));
    }
    const savedLang = localStorage.getItem(LANG_KEY);
    if (savedLang === "bn" || savedLang === "en") setLanguage(savedLang);
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
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading, streamingId]);

  useEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 140)}px`;
  }, [input]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [activeSessionId]);

  const toggleLanguage = () => {
    setLanguage((prev) => {
      const next = prev === "en" ? "bn" : "en";
      localStorage.setItem(LANG_KEY, next);
      return next;
    });
  };

  const startNewChat = () => {
    setActiveSessionIdState(null);
    setActiveSessionId(null);
    setMessages([]);
    setInput("");
    setSidebarOpen(false);
    inputRef.current?.focus();
  };

  const openSession = (session: ChatSession) => {
    setActiveSessionIdState(session.id);
    setActiveSessionId(session.id);
    setMessages(fromStored(session.messages));
    setInput("");
    setSidebarOpen(false);
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
    setStreamingId(null);

    const assistantId = (Date.now() + 1).toString();

    try {
      const data = await askLegalQuestion(text.trim(), language);
      const full = data.answer || "";

      setIsLoading(false);
      setStreamingId(assistantId);
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          content: "",
          role: "assistant" as const,
          timestamp: new Date(),
        },
      ]);

      const chunks = full.split(/(\s+)/);
      let acc = "";
      for (const chunk of chunks) {
        acc += chunk;
        const snapshot = acc;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: snapshot } : m
          )
        );
        await new Promise((r) => setTimeout(r, chunk.trim() ? 18 : 0));
      }

      setStreamingId(null);
      setMessages((prev) => {
        const finalMessages = prev.map((m) =>
          m.id === assistantId ? { ...m, content: full } : m
        );
        persistSession(sessionId!, finalMessages);
        return finalMessages;
      });
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : "Something went wrong.";
      setIsLoading(false);
      setStreamingId(null);
      setMessages((prev) => {
        const withError = [
          ...prev,
          {
            id: assistantId,
            content: `Sorry, I couldn't answer that: ${detail}`,
            role: "assistant" as const,
            timestamp: new Date(),
          },
        ];
        persistSession(sessionId!, withError);
        return withError;
      });
    }
  };

  const isEmpty = messages.length === 0;
  const bnSuggestions = QUICK_SUGGESTIONS.filter((s) =>
    /[\u0980-\u09FF]/.test(s)
  ).slice(0, 4);
  const enSuggestions = QUICK_SUGGESTIONS.filter(
    (s) => !/[\u0980-\u09FF]/.test(s)
  ).slice(0, 4);
  const displaySuggestions =
    language === "bn" ? bnSuggestions : enSuggestions;

  return (
    <div className="chat-overlay">
      <main className={`chat-app${dark ? " is-dark" : ""}`}>
        {sidebarOpen && (
          <button
            type="button"
            className="sidebar-backdrop"
            aria-label="Close menu"
            onClick={() => setSidebarOpen(false)}
          />
        )}
        <aside className={`sidebar${sidebarOpen ? " is-open" : ""}`}>
          <div className="sidebar-head">
            <a className="chat-logo" href="/" aria-label="VerdictAI home">
              <Scale size={17} />{" "}
              <span>
                verdict<span>ai</span>
              </span>
            </a>
            <button
              className="icon-button close-sidebar"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close menu"
              type="button"
            >
              <X />
            </button>
          </div>

          <button className="new-chat" type="button" onClick={startNewChat}>
            <Plus /> New chat
          </button>

          <div className="conversation-list">
            <p className="sidebar-label">Recent conversations</p>
            {sessions.length === 0 && (
              <p className="sidebar-version" style={{ marginTop: 8 }}>
                No chats yet
              </p>
            )}
            {sessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={`conversation${
                  session.id === activeSessionId ? " active" : ""
                }`}
                onClick={() => openSession(session)}
              >
                {session.title}
              </button>
            ))}
          </div>

          <div className="sidebar-bottom">
            <button
              type="button"
              className={`language-toggle${language === "bn" ? " is-bn" : ""}`}
              onClick={toggleLanguage}
            >
              <span>{language === "bn" ? "বাং" : "EN"}</span>
              <span className="toggle-track">
                <span />
              </span>
            </button>
            <button type="button" className="sidebar-link" onClick={onClose}>
              Back to site
            </button>
            <span className="sidebar-version">
              Constitution of Bangladesh · 2026
            </span>
          </div>
        </aside>

        <section className="chat-main">
          <div className="chat-float-controls">
            <button
              className="icon-button mobile-menu-button"
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              <Menu />
            </button>
            <div className="header-actions">
              <button
                className="theme-button"
                type="button"
                onClick={() => setDark((v) => !v)}
                aria-label={dark ? "Use light mode" : "Use dark mode"}
              >
                {dark ? <Sun /> : <Moon />}
              </button>
              <button
                className="icon-button"
                type="button"
                onClick={onClose}
                aria-label="Close chat"
              >
                <X />
              </button>
            </div>
          </div>

          <div className="chat-scroll" ref={scrollRef}>
            <div className="chat-scroll-inner">
              {isEmpty ? (
                <div className="empty-state">
                  <div className="empty-mark">
                    <Scale />
                  </div>
                  <p className="greeting-small">Good to meet you.</p>
                  <h1>
                    What would you like to know
                    <br className="desktop-only" /> about your rights?
                  </h1>
                  <p className="empty-description">
                    Ask a question about the Constitution of Bangladesh.
                    <br className="desktop-only" /> I&apos;ll explain it clearly
                    and show you the source.
                  </p>
                </div>
              ) : (
                <div className="message-list">
                  {messages.map((message) => (
                    <article
                      className={`message ${message.role}`}
                      key={message.id}
                    >
                      <div className="message-body">
                        {message.role === "assistant" ? (
                          <>
                            {message.content ? (
                              <div className="prose-chat">
                                <MessageContent content={message.content} />
                              </div>
                            ) : null}
                            {streamingId === message.id && (
                              <span className="stream-cursor" aria-hidden />
                            )}
                          </>
                        ) : (
                          <p>{message.content}</p>
                        )}
                      </div>
                    </article>
                  ))}
                  {isLoading && (
                    <div
                      className="typing-state"
                      aria-label="VerdictAI is thinking"
                    >
                      <span className="dot" />
                      <span className="dot" />
                      <span className="dot" />
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="composer-area">
            <div className="composer-inner">
              {isEmpty && (
                <div className="suggestions">
                  {displaySuggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      className="suggestion"
                      onClick={() => sendMessage(suggestion)}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
              <div className="composer">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (
                      e.key === "Enter" &&
                      !e.shiftKey &&
                      !e.nativeEvent.isComposing
                    ) {
                      e.preventDefault();
                      sendMessage(input);
                    }
                  }}
                  placeholder={
                    language === "bn"
                      ? "আপনার অধিকার সম্পর্কে জিজ্ঞাসা করুন…"
                      : "Ask about your rights…"
                  }
                  rows={1}
                  aria-label="Your question"
                />
                <button
                  className="send-button"
                  type="button"
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim() || isLoading || !!streamingId}
                  aria-label="Send message"
                >
                  <ArrowUp />
                </button>
              </div>
              <p className="disclaimer">
                VerdictAI provides constitutional information, not legal advice.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
