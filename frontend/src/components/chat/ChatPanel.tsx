"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowUp, Menu, Moon, Plus, Scale, Sun, X } from "lucide-react";
import VoiceAskButton from "./VoiceAskButton";
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
  initialPrompt?: string | null;
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

export default function ChatPanel({
  onClose,
  initialPrompt = null,
}: ChatPanelProps) {
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
  const stickToBottom = useRef(true);
  const ignoreScrollUntil = useRef(0);
  const [closing, setClosing] = useState(false);

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
    if (initialPrompt) {
      setActiveSessionIdState(null);
      setActiveSessionId(null);
      setMessages([]);
      setInput(initialPrompt);
    } else {
      const savedActiveId = getActiveSessionId();
      const active = loaded.find((s) => s.id === savedActiveId);
      if (active) {
        setActiveSessionIdState(active.id);
        setMessages(fromStored(active.messages));
      }
    }
    const savedLang = localStorage.getItem(LANG_KEY);
    if (savedLang === "bn" || savedLang === "en") setLanguage(savedLang);
    setHistoryReady(true);
  }, [initialPrompt]);

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
    if (!historyReady || !activeSessionId || messages.length === 0 || streamingId) {
      return;
    }
    persistSession(activeSessionId, messages);
  }, [messages, activeSessionId, historyReady, persistSession, streamingId]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      if (performance.now() < ignoreScrollUntil.current) return;
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
      stickToBottom.current = distance < 96;
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !stickToBottom.current) return;
    const frame = requestAnimationFrame(() => {
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
      const instant = Boolean(streamingId) || distance > 640;
      ignoreScrollUntil.current = performance.now() + (instant ? 80 : 420);
      if (instant) {
        el.scrollTop = el.scrollHeight;
        return;
      }
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    });
    return () => cancelAnimationFrame(frame);
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
    stickToBottom.current = true;
    setActiveSessionIdState(session.id);
    setActiveSessionId(session.id);
    setMessages(fromStored(session.messages));
    setInput("");
    setSidebarOpen(false);
  };

  const recordVoiceLine = useCallback(
    (id: string, role: "user" | "assistant", text: string) => {
      if (!activeSessionId) {
        const sessionId = createSessionId();
        setActiveSessionIdState(sessionId);
        setActiveSessionId(sessionId);
      }
      setMessages((prev) => {
        const index = prev.findIndex((message) => message.id === id);
        if (index >= 0) {
          return prev.map((message) =>
            message.id === id ? { ...message, content: text } : message
          );
        }
        return [
          ...prev,
          { id, content: text, role, timestamp: new Date() },
        ];
      });
    },
    [activeSessionId]
  );

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

    stickToBottom.current = true;
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    persistSession(sessionId, nextMessages);
    setInput("");
    setIsLoading(true);
    setStreamingId(null);

    const assistantId = (Date.now() + 1).toString();

    try {
      const history = messages
        .filter((message) => message.content.trim())
        .slice(-6)
        .map((message) => ({
          role: message.role,
          content: message.content.slice(0, 1000),
        }));
      const data = await askLegalQuestion(text.trim(), language, history);
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
      let index = 0;
      while (index < chunks.length) {
        const step = chunks[index]?.trim() ? 2 : 1;
        acc += chunks.slice(index, index + step).join("");
        index += step;
        const snapshot = acc;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: snapshot } : m
          )
        );
        await new Promise<void>((resolve) => {
          requestAnimationFrame(() => resolve());
        });
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

  const requestClose = () => {
    if (closing) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      onClose();
      return;
    }
    setClosing(true);
    window.setTimeout(onClose, 240);
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
    <div className={`chat-overlay${closing ? " is-closing" : ""}`}>
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
            <button type="button" className="sidebar-link" onClick={requestClose}>
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
                onClick={requestClose}
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
                <VoiceAskButton
                  language={language}
                  disabled={isLoading || !!streamingId}
                  onTranscript={recordVoiceLine}
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
