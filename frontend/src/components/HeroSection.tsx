"use client";

import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Sparkles,
  User,
} from "lucide-react";
import { cn, tokens } from "@/lib/theme";
import Button from "@/components/ui/Button";
import HeroBackground from "@/components/HeroBackground";
import { useChat } from "@/components/chat/ChatContext";

const TRUST_POINTS = [
  "Ask anything, anytime",
  "Powered by legal data",
  "Smart AI responses",
];

const PREVIEW_MESSAGES = [
  {
    role: "user" as const,
    text: "Do I have the right to remain silent?",
  },
  {
    role: "assistant" as const,
    text: "Yes — in many legal systems you may remain silent and are not required to answer police questions without a lawyer.",
  },
];

export default function HeroSection() {
  const { openChat } = useChat();

  return (
    <section className="relative overflow-hidden">
      <HeroBackground />

      <div className={cn(tokens.container, "relative z-10 py-20 md:py-28 lg:py-32")}>
        <div className="grid items-center gap-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-20 xl:gap-28">
          <div className="max-w-xl text-center lg:max-w-none lg:text-left">
            <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-[var(--page-border)] bg-[var(--page-card)] px-4 py-2 backdrop-blur-sm">
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
                "mb-7 text-4xl leading-[1.12] sm:text-5xl lg:text-[3.25rem] lg:leading-[1.1] xl:text-[3.5rem]"
              )}
            >
              Legal Answers,{" "}
              <span className="bg-gradient-to-r from-[var(--accent)] via-[color-mix(in_srgb,var(--accent)_80%,#fff)] to-[var(--accent)] bg-clip-text text-transparent">
                Instantly
              </span>
            </h1>

            <p className="mx-auto mb-10 max-w-lg text-base leading-relaxed text-[var(--page-text-muted)] sm:text-lg lg:mx-0">
              Chat with VerdictAI — your intelligent legal assistant. Type a
              question, get clear answers backed by real legal knowledge.
            </p>

            <ul className="mb-10 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:justify-center lg:justify-start">
              {TRUST_POINTS.map((point) => (
                <li
                  key={point}
                  className="flex items-center justify-center gap-2 text-sm text-[var(--page-text-muted)] sm:justify-start"
                >
                  <CheckCircle2
                    className="h-4 w-4 shrink-0"
                    style={{ color: "var(--accent)" }}
                  />
                  {point}
                </li>
              ))}
            </ul>

            <div className="flex justify-center lg:justify-start">
              <Button
                onClick={openChat}
                size="lg"
                className="w-full gap-2 sm:w-auto"
              >
                Open Chatbot
                <ArrowRight className="h-5 w-5" />
              </Button>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-sm lg:max-w-md xl:max-w-lg">
            <div
              className="absolute -inset-8 rounded-[2rem] opacity-40 blur-3xl"
              style={{
                background:
                  "color-mix(in srgb, var(--accent) 18%, transparent)",
              }}
            />

            <button
              type="button"
              onClick={openChat}
              className="group relative block w-full overflow-hidden rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] text-left shadow-xl backdrop-blur-md transition hover:border-[color-mix(in_srgb,var(--accent)_35%,transparent)]"
            >
              <div className="flex items-center gap-3 border-b border-[var(--page-border)] px-5 py-3.5">
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-lg"
                  style={{
                    background:
                      "color-mix(in srgb, var(--accent) 15%, transparent)",
                  }}
                >
                  <Bot className="h-4 w-4" style={{ color: "var(--accent)" }} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--page-text)]">
                    VerdictAI Chat
                  </p>
                  <p className="flex items-center gap-1.5 text-[11px] text-emerald-500">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    Online
                  </p>
                </div>
              </div>

              <div className="space-y-3 px-5 py-5">
                {PREVIEW_MESSAGES.map((msg, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex gap-2.5",
                      msg.role === "user" ? "flex-row-reverse" : "flex-row"
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-6 w-6 shrink-0 items-center justify-center rounded-md",
                        msg.role === "user"
                          ? "chat-accent-icon"
                          : "chat-bot-icon"
                      )}
                    >
                      {msg.role === "user" ? (
                        <User className="h-3 w-3" />
                      ) : (
                        <Bot className="h-3 w-3" />
                      )}
                    </div>
                    <div
                      className={cn(
                        "max-w-[88%] rounded-xl px-3 py-2 text-[13px] leading-relaxed",
                        msg.role === "user"
                          ? "chat-user-bubble rounded-tr-sm"
                          : "rounded-tl-sm border border-[var(--page-border)] bg-[var(--page-hover)] text-[var(--page-text)]"
                      )}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>

              <div className="border-t border-[var(--page-border)] px-5 py-3.5">
                <span className="flex items-center justify-center gap-2 text-sm font-medium text-[var(--accent)] group-hover:underline">
                  Start chatting
                  <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                </span>
              </div>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
