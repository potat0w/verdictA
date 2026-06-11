"use client";

import {
  ArrowRight,
  Bot,
  CheckCircle2,
  MessageSquare,
  Sparkles,
  User,
  Zap,
} from "lucide-react";
import { cn, tokens } from "@/lib/theme";
import Button from "@/components/ui/Button";
import HeroBackground from "@/components/HeroBackground";
import { useChat } from "@/components/chat/ChatContext";

const STATS = [
  { value: "24/7", label: "Always Online" },
  { value: "< 30s", label: "Avg Response" },
  { value: "Free", label: "To Get Started" },
];

const TRUST_POINTS = [
  "Ask anything, anytime",
  "Powered by legal data",
  "Smart AI responses",
];

const PREVIEW_MESSAGES = [
  {
    role: "user" as const,
    text: "If I am accused of a crime, do I have the right to remain silent?",
  },
  {
    role: "assistant" as const,
    text: "Yes. In many legal systems you have the right to remain silent and not testify against yourself. You are generally not required to answer police questions without a lawyer present...",
  },
];

export default function HeroSection() {
  const { openChat } = useChat();

  return (
    <section className="relative min-h-[90vh] overflow-hidden">
      <HeroBackground />

      <div
        className={cn(
          tokens.container,
          "relative z-10 flex min-h-[90vh] items-center py-16 lg:py-20"
        )}
      >
        <div className="grid w-full items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <div className="text-center lg:text-left">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--page-border)] bg-[var(--page-card)] px-4 py-2 backdrop-blur-sm">
              <span className="relative flex h-2 w-2">
                <span
                  className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
                  style={{ background: "var(--accent)" }}
                />
                <span
                  className="relative inline-flex h-2 w-2 rounded-full"
                  style={{ background: "var(--accent)" }}
                />
              </span>
              <Sparkles
                className="h-3.5 w-3.5"
                style={{ color: "var(--accent)" }}
              />
              <span className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--accent)]">
                AI Legal Chatbot
              </span>
            </div>

            <h1
              className={cn(
                tokens.heading,
                "mb-6 text-[2.75rem] leading-[1.08] sm:text-5xl md:text-6xl lg:text-[4.25rem]"
              )}
            >
              Legal Answers,{" "}
              <span className="relative inline-block">
                <span className="bg-gradient-to-r from-[var(--accent)] via-[color-mix(in_srgb,var(--accent)_80%,#fff)] to-[var(--accent)] bg-clip-text text-transparent">
                  Instantly
                </span>
                <span
                  className="absolute -bottom-1 left-0 h-[3px] w-full rounded-full opacity-70"
                  style={{
                    background:
                      "linear-gradient(90deg, var(--accent), transparent)",
                  }}
                />
              </span>
            </h1>

            <p className="mx-auto mb-8 max-w-xl text-base leading-relaxed text-[var(--page-text-muted)] sm:text-lg lg:mx-0">
              Chat with VerdictAI — your intelligent legal assistant. Type a
              question, get clear answers backed by real legal knowledge.
            </p>

            <ul className="mb-8 flex flex-wrap justify-center gap-x-5 gap-y-2 lg:justify-start">
              {TRUST_POINTS.map((point) => (
                <li
                  key={point}
                  className="flex items-center gap-1.5 text-sm text-[var(--page-text-muted)]"
                >
                  <CheckCircle2
                    className="h-4 w-4 shrink-0"
                    style={{ color: "var(--accent)" }}
                  />
                  {point}
                </li>
              ))}
            </ul>

            <div className="flex flex-col items-center gap-3 sm:flex-row lg:justify-start">
              <Button
                onClick={openChat}
                size="lg"
                className="w-full gap-2 sm:w-auto"
              >
                Open Chatbot
                <ArrowRight className="h-5 w-5" />
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="w-full sm:w-auto"
                onClick={openChat}
              >
                Try a Free Question
              </Button>
            </div>

            <div className="mt-12 grid grid-cols-3 gap-3 sm:gap-4">
              {STATS.map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-xl border border-[var(--page-border)] bg-[var(--page-card)] px-3 py-4 backdrop-blur-sm sm:px-4"
                >
                  <p
                    className="text-xl font-bold sm:text-2xl"
                    style={{ color: "var(--accent)" }}
                  >
                    {stat.value}
                  </p>
                  <p className="mt-0.5 text-[10px] uppercase tracking-wider text-[var(--page-text-muted)] sm:text-xs">
                    {stat.label}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-md lg:max-w-none">
            <div
              className="absolute -inset-6 rounded-[2rem] opacity-50 blur-2xl"
              style={{
                background:
                  "color-mix(in srgb, var(--accent) 20%, transparent)",
              }}
            />

            <div className="relative overflow-hidden rounded-[1.75rem] border border-[var(--page-border)] bg-[var(--page-card)] shadow-2xl backdrop-blur-md">
              <div className="flex items-center gap-3 border-b border-[var(--page-border)] px-5 py-4">
                <div
                  className="flex h-9 w-9 items-center justify-center rounded-lg"
                  style={{
                    background:
                      "color-mix(in srgb, var(--accent) 15%, transparent)",
                  }}
                >
                  <Bot className="h-4 w-4" style={{ color: "var(--accent)" }} />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-[var(--page-text)]">
                    VerdictAI Chat
                  </p>
                  <p className="flex items-center gap-1.5 text-[11px] text-emerald-500">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    Online — ready to help
                  </p>
                </div>
                <MessageSquare
                  className="h-4 w-4 text-[var(--page-text-muted)]"
                />
              </div>

              <div className="space-y-4 p-5">
                {PREVIEW_MESSAGES.map((msg, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex gap-3",
                      msg.role === "user" ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg",
                        msg.role === "user"
                          ? "chat-accent-icon"
                          : "chat-bot-icon"
                      )}
                    >
                      {msg.role === "user" ? (
                        <User className="h-3.5 w-3.5" />
                      ) : (
                        <Bot className="h-3.5 w-3.5" />
                      )}
                    </div>
                    <div
                      className={cn(
                        "max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                        msg.role === "user"
                          ? "chat-user-bubble rounded-tr-sm"
                          : "rounded-tl-sm border border-[var(--page-border)] bg-[var(--page-hover)] text-[var(--page-text)]"
                      )}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}

                <div className="flex items-center gap-2 rounded-xl border border-[var(--page-border)] bg-[var(--page-hover)] px-4 py-3">
                  <Zap
                    className="h-4 w-4 shrink-0"
                    style={{ color: "var(--accent)" }}
                  />
                  <span className="text-sm text-[var(--page-text-muted)]">
                    Ask your question...
                  </span>
                </div>
              </div>

              <div className="border-t border-[var(--page-border)] p-4">
                <button
                  onClick={openChat}
                  className="chat-send-btn flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold"
                >
                  Start Chatting
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
