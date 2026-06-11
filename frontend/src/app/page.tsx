"use client";

import {
  ArrowRight,
  Bot,
  Brain,
  MessageSquare,
  Quote,
  Sparkles,
  Star,
  Zap,
} from "lucide-react";
import { cn, tokens } from "@/lib/theme";
import Button from "@/components/ui/Button";
import HeroSection from "@/components/HeroSection";
import SpotlightCard from "@/components/SpotlightCard/SpotlightCard";
import SiteLayout from "@/components/layout/SiteLayout";
import { useChat } from "@/components/chat/ChatContext";

const CHAT_FEATURES = [
  {
    icon: MessageSquare,
    title: "Natural Conversation",
    description:
      "Type your question like you're texting a friend. No legal jargon required to get started.",
  },
  {
    icon: Brain,
    title: "Smart Legal AI",
    description:
      "Powered by a knowledge base of laws and regulations — answers are grounded in real legal texts.",
  },
  {
    icon: Zap,
    title: "Instant Responses",
    description:
      "Get answers in seconds, not days. Available 24/7 whenever you need guidance.",
  },
  {
    icon: Sparkles,
    title: "Easy to Use",
    description:
      "No appointments, no waiting rooms. Just open the chat and ask what you need to know.",
  },
  {
    icon: Bot,
    title: "Always Learning",
    description:
      "Our AI retrieves the most relevant legal information for every question you ask.",
  },
  {
    icon: MessageSquare,
    title: "Follow-Up Questions",
    description:
      "Keep the conversation going. Ask clarifications and dive deeper into any topic.",
  },
] as const;

const STEPS = [
  {
    step: "01",
    title: "Open the chat",
    desc: "Click the chat button anywhere on the site.",
  },
  {
    step: "02",
    title: "Ask your question",
    desc: "Type anything — contracts, rights, regulations, and more.",
  },
  {
    step: "03",
    title: "Get your answer",
    desc: "Receive a clear, detailed response powered by legal data.",
  },
];

export default function Home() {
  const { openChat } = useChat();

  return (
    <SiteLayout>
      <HeroSection />

      <section className={tokens.section}>
        <div className={tokens.container}>
          <div className="mb-16 text-center">
            <p className="mb-3 text-xs font-medium uppercase tracking-[0.2em] text-[var(--accent)]">
              Features
            </p>
            <h2 className={cn(tokens.heading, "mb-4 text-4xl md:text-5xl")}>
              Why Use VerdictAI Chat?
            </h2>
            <p className="mx-auto max-w-xl text-lg text-[var(--page-text-muted)]">
              A simple chatbot that gives you legal answers when you need them.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {CHAT_FEATURES.map((feature) => (
              <SpotlightCard
                key={feature.title}
                className="h-full rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-6 backdrop-blur-sm"
              >
                <div className={tokens.iconBadge}>
                  <feature.icon className="h-7 w-7" />
                </div>
                <h3 className="mt-4 text-xl font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm text-[var(--page-text-muted)]">
                  {feature.description}
                </p>
              </SpotlightCard>
            ))}
          </div>
        </div>
      </section>

      <section className={cn(tokens.section, "bg-[var(--page-section-alt)]")}>
        <div className={tokens.container}>
          <div className="mb-12 text-center">
            <h2 className={cn(tokens.heading, "mb-4 text-4xl")}>
              How It Works
            </h2>
            <p className="text-[var(--page-text-muted)]">
              Three steps to get your answer
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {STEPS.map((item) => (
              <div
                key={item.step}
                className="rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-8 text-center"
              >
                <p
                  className="mb-4 text-3xl font-bold"
                  style={{ color: "var(--accent)" }}
                >
                  {item.step}
                </p>
                <h3 className="mb-2 text-xl font-semibold">{item.title}</h3>
                <p className="text-sm text-[var(--page-text-muted)]">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
          <div className="mt-10 text-center">
            <Button onClick={openChat} size="lg" className="gap-2">
              Try It Now
              <ArrowRight className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </section>

      <section className={tokens.section}>
        <div className={tokens.container}>
          <div className="mb-12 text-center">
            <h2 className={cn(tokens.heading, "mb-4 text-4xl")}>
              What Users Say
            </h2>
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            {[
              {
                quote:
                  "I asked about contract terms and got a clear answer in seconds. Way faster than searching online.",
                name: "Sarah M.",
                role: "Startup Founder",
              },
              {
                quote:
                  "The chatbot understood my question and gave a detailed response. Best legal AI tool I've tried.",
                name: "Ahmed K.",
                role: "Freelancer",
              },
            ].map((t) => (
              <SpotlightCard
                key={t.name}
                className="h-full rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-8 backdrop-blur-sm"
              >
                <div className="mb-4 flex gap-1">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <Star
                      key={j}
                      className="h-4 w-4 fill-[var(--accent)] text-[var(--accent)]"
                    />
                  ))}
                </div>
                <Quote className="mb-3 h-6 w-6 text-[var(--accent)]/60" />
                <p className="mb-6 text-[var(--page-text-muted)]">
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div>
                  <p className="font-semibold">{t.name}</p>
                  <p className="text-sm text-[var(--page-text-muted)]">
                    {t.role}
                  </p>
                </div>
              </SpotlightCard>
            ))}
          </div>
        </div>
      </section>
    </SiteLayout>
  );
}
