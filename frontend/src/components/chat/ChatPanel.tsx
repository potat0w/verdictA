"use client";

import { useEffect, useRef, useState } from "react";
import {
  Bot,
  MessageSquare,
  Palette,
  Scale,
  Send,
  Sparkles,
  User,
  X,
} from "lucide-react";
import { askLegalQuestion } from "@/lib/api";
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

const SUGGESTIONS = [
  { label: "Contract law basics", query: "What is contract law?" },
  { label: "Property rights", query: "Explain property rights" },
  { label: "Criminal defense", query: "What are criminal defense basics?" },
  { label: "Business compliance", query: "What is business law compliance?" },
];

export default function ChatPanel({ onClose }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: text.trim(),
      role: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const data = await askLegalQuestion(text.trim());
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          content: data.answer,
          role: "assistant",
          timestamp: new Date(),
        },
      ]);
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : "Something went wrong.";
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          content: `Sorry, I couldn't answer that: ${detail}`,
          role: "assistant",
          timestamp: new Date(),
        },
      ]);
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
      <div className="fixed inset-0 z-[100] flex bg-[var(--chat-bg)]">
        <aside className="hidden w-72 shrink-0 flex-col border-r border-[var(--chat-border)] bg-[var(--chat-surface)] lg:flex">
          <div className="border-b border-[var(--chat-border)] p-6">
            <div className="flex items-center gap-3">
              <div className="chat-accent-icon flex h-11 w-11 items-center justify-center rounded-2xl">
                <Scale className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-merriweather text-lg font-bold text-[var(--chat-text)]">
                  VerdictAI
                </h2>
                <p className="text-xs text-[var(--chat-text-muted)]">
                  Legal Assistant
                </p>
              </div>
            </div>
          </div>

          <div className="flex-1 p-4">
            <p className="mb-3 px-2 text-[11px] font-medium uppercase tracking-wider text-[var(--chat-text-muted)]">
              Try asking
            </p>
            <div className="space-y-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.query}
                  onClick={() => sendMessage(s.query)}
                  disabled={isLoading}
                  className="flex w-full items-start gap-3 rounded-xl border border-[var(--chat-border)] bg-[var(--chat-hover)] p-3 text-left text-sm text-[var(--chat-text-muted)] hover:border-[color-mix(in_srgb,var(--accent)_40%,transparent)] hover:text-[var(--chat-text)] disabled:opacity-50"
                >
                  <MessageSquare
                    className="mt-0.5 h-4 w-4 shrink-0"
                    style={{ color: "var(--accent)" }}
                  />
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-[var(--chat-border)] p-4">
            <p className="text-center text-[11px] leading-relaxed text-[var(--chat-text-muted)]">
              AI-generated guidance. Not a substitute for professional legal
              counsel.
            </p>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-[var(--chat-border)] bg-[var(--chat-surface)] px-4 py-3 backdrop-blur-xl md:px-6">
            <div className="flex items-center gap-3">
              <div className="chat-bot-icon flex h-9 w-9 items-center justify-center rounded-xl lg:hidden">
                <Scale className="h-4 w-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-merriweather text-base font-bold text-[var(--chat-text)] md:text-lg">
                    Legal Chat
                  </h2>
                  <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-500">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    Online
                  </span>
                </div>
                <p className="flex items-center gap-1 text-xs text-[var(--chat-text-muted)]">
                  <Sparkles className="h-3 w-3" style={{ color: "var(--accent)" }} />
                  Powered by legal knowledge base
                </p>
              </div>
            </div>
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
            className="chat-scroll flex-1 overflow-y-auto px-4 py-6 md:px-8"
          >
            {isEmpty ? (
              <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center text-center">
                <div
                  className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border"
                  style={{
                    borderColor: "color-mix(in srgb, var(--accent) 30%, transparent)",
                    background:
                      "color-mix(in srgb, var(--accent) 10%, transparent)",
                  }}
                >
                  <Bot className="h-8 w-8" style={{ color: "var(--accent)" }} />
                </div>
                <h3 className="font-merriweather mb-2 text-2xl font-bold text-[var(--chat-text)]">
                  How can I help you today?
                </h3>
                <p className="mb-8 max-w-md text-sm leading-relaxed text-[var(--chat-text-muted)]">
                  Ask about contracts, property law, criminal defense, business
                  compliance, and more.
                </p>
                <div className="grid w-full max-w-lg gap-2 sm:grid-cols-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s.query}
                      onClick={() => sendMessage(s.query)}
                      className="rounded-xl border border-[var(--chat-border)] bg-[var(--chat-hover)] px-4 py-3 text-left text-sm text-[var(--chat-text-muted)] hover:text-[var(--chat-text)]"
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-3xl space-y-6">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      "flex gap-4",
                      message.role === "user" ? "flex-row-reverse" : "flex-row"
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
                        message.role === "user" ? "flex flex-col items-end" : ""
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
                  <div className="flex gap-4">
                    <div className="chat-bot-icon flex h-8 w-8 shrink-0 items-center justify-center rounded-lg">
                      <Bot className="h-4 w-4" />
                    </div>
                    <div className="flex items-center gap-3 rounded-2xl rounded-tl-md border border-[var(--chat-border)] bg-[var(--chat-bubble-assistant)] px-5 py-4">
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
            )}
          </div>

          <div className="border-t border-[var(--chat-border)] bg-[var(--chat-surface)] p-4 md:p-6">
            <form
              onSubmit={handleSubmit}
              className="mx-auto flex max-w-3xl items-end gap-3"
            >
              <div
                className="relative flex-1 rounded-2xl border border-[var(--chat-border)] bg-[var(--chat-input-bg)] focus-within:ring-1"
                style={
                  {
                    borderColor: undefined,
                    "--tw-ring-color":
                      "color-mix(in srgb, var(--accent) 25%, transparent)",
                  } as React.CSSProperties
                }
              >
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a legal question..."
                  rows={1}
                  className="max-h-32 w-full resize-none bg-transparent px-5 py-3.5 text-sm text-[var(--chat-text)] placeholder-[var(--chat-text-muted)] outline-none"
                  disabled={isLoading}
                />
              </div>
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="chat-send-btn flex h-[50px] w-[50px] shrink-0 items-center justify-center rounded-2xl hover:brightness-110 disabled:opacity-30"
                aria-label="Send"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
            <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-[var(--chat-text-muted)]">
              Press Enter to send · Shift+Enter for new line
            </p>
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
