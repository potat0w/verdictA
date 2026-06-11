"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowRight,
  Briefcase,
  Building2,
  ChevronRight,
  FileText,
  Gavel,
  Heart,
  Mail,
  MapPin,
  Phone,
  Quote,
  Scale,
  Shield,
  Star,
  Target,
  TrendingUp,
} from "lucide-react";
import { clearToken, getToken } from "@/lib/api";
import { cn, tokens } from "@/lib/theme";
import Button from "@/components/ui/Button";
import HeroBackground from "@/components/HeroBackground";
import SpotlightCard from "@/components/SpotlightCard/SpotlightCard";
import Navbar from "@/components/layout/Navbar";
import ChatPanel from "@/components/chat/ChatPanel";

const SERVICES = [
  {
    name: "Contract Law",
    icon: FileText,
    description: "Drafting, reviewing, and negotiating contracts",
  },
  {
    name: "Property Law",
    icon: Building2,
    description: "Real estate transactions and property disputes",
  },
  {
    name: "Criminal Law",
    icon: Gavel,
    description: "Criminal defense and legal representation",
  },
  {
    name: "Business Law",
    icon: Briefcase,
    description: "Corporate legal services and compliance",
  },
  {
    name: "Family Law",
    icon: Heart,
    description: "Divorce, custody, and family matters",
  },
  {
    name: "Civil Litigation",
    icon: Scale,
    description: "Dispute resolution and court representation",
  },
] as const;

export default function Home() {
  const [showChat, setShowChat] = useState(false);
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(!!getToken());
    const onStorage = () => setHasToken(!!getToken());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <Navbar
        hasToken={hasToken}
        onLogout={() => {
          clearToken();
          setHasToken(false);
        }}
      />

      <section className="relative min-h-[92vh] overflow-hidden">
        <HeroBackground />

        <div className={cn(tokens.container, "relative z-10 py-20 lg:py-28")}>
          <div className="grid items-center gap-14 lg:grid-cols-2">
            <div className="text-center lg:text-left">
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-[var(--page-border)] bg-[var(--page-hover)] px-4 py-1.5 text-xs uppercase tracking-[0.25em] text-[var(--accent)]">
                AI-Powered Legal Platform
              </p>

              <h1
                className={cn(
                  tokens.heading,
                  "mb-6 text-5xl leading-[1.1] md:text-6xl lg:text-7xl"
                )}
              >
                Justice,{" "}
                <span className="bg-gradient-to-r from-[var(--accent)] to-[color-mix(in_srgb,var(--accent)_60%,#fff)] bg-clip-text text-transparent">
                  Reimagined
                </span>
              </h1>

              <p className="mb-10 max-w-xl text-lg text-[var(--page-text-muted)] md:text-xl">
                Instant legal guidance backed by comprehensive law databases.
                Ask questions, get answers — anytime.
              </p>

              <div className="flex flex-col items-center gap-4 sm:flex-row lg:justify-start">
                <Button
                  onClick={() => setShowChat(true)}
                  size="lg"
                  className="gap-2"
                >
                  Start Legal Chat
                  <ArrowRight className="h-5 w-5" />
                </Button>
                <a href="#services">
                  <Button variant="outline" size="lg">
                    Explore Services
                  </Button>
                </a>
              </div>

              <div className="mt-14 grid grid-cols-3 gap-6 border-t border-[var(--page-border)] pt-8">
                {[
                  { value: "18+", label: "Years" },
                  { value: "265+", label: "Cases" },
                  { value: "24/7", label: "Support" },
                ].map((stat) => (
                  <div key={stat.label}>
                    <div className="text-2xl font-bold text-[var(--accent)] md:text-3xl">
                      {stat.value}
                    </div>
                    <div className="text-xs uppercase tracking-wider text-[var(--page-text-muted)]">
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative hidden lg:block">
              <div className="absolute -inset-4 rounded-3xl bg-gradient-to-br from-[var(--primary-gold)]/15 to-transparent blur-2xl" />
              <div className="relative aspect-[4/5] overflow-hidden rounded-3xl border border-[var(--page-border)] shadow-2xl">
                <Image
                  src="/hero.jpg"
                  alt="Law firm"
                  fill
                  priority
                  className="object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#0f1c24] via-transparent to-transparent" />
              </div>
              <div className="absolute -bottom-6 -left-6 rounded-2xl border border-[var(--page-border)] bg-[rgba(15,28,36,0.95)] p-5 backdrop-blur-xl">
                <p className="text-sm text-[var(--page-text-muted)]">Success Rate</p>
                <p className="text-3xl font-bold text-[var(--accent)]">
                  99%
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="services" className={tokens.section}>
        <div className={tokens.container}>
          <div className="mb-16 text-center">
            <h2 className={cn(tokens.heading, "mb-4 text-4xl md:text-5xl")}>
              Our Services
            </h2>
            <p className="text-lg text-[var(--page-text-muted)]">
              Comprehensive legal solutions for every need
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {SERVICES.map((service) => (
              <SpotlightCard
                key={service.name}
                className="h-full rounded-2xl border border-[var(--page-border)] bg-[rgba(15,28,36,0.6)] p-6 backdrop-blur-sm"
              >
                <div className={tokens.iconBadge}>
                  <service.icon className="h-7 w-7" />
                </div>
                <h3 className="mt-4 text-xl font-semibold">{service.name}</h3>
                <p className="mt-2 text-sm text-[var(--page-text-muted)]">
                  {service.description}
                </p>
                <button className="mt-4 inline-flex items-center gap-1 text-sm text-[var(--accent)] hover:text-white">
                  Learn More <ChevronRight className="h-4 w-4" />
                </button>
              </SpotlightCard>
            ))}
          </div>
        </div>
      </section>

      <section id="about" className={cn(tokens.section, "bg-[var(--page-hover)]")}>
        <div className={tokens.container}>
          <div className="grid items-center gap-14 lg:grid-cols-2">
            <div className="relative aspect-[4/3] overflow-hidden rounded-3xl border border-[var(--page-border)]">
              <Image
                src="/hero1.jpg"
                alt="Trusted legal advisor"
                fill
                className="object-cover"
              />
            </div>

            <div>
              <h2 className={cn(tokens.heading, "mb-6 text-4xl")}>
                Trusted Legal Advisor
              </h2>
              <p className="mb-8 text-lg text-[var(--page-text-muted)]">
                Our AI-powered assistant provides comprehensive legal guidance
                backed by extensive knowledge of laws, regulations, and case
                precedents.
              </p>
              <div className="grid grid-cols-2 gap-6">
                {[
                  { value: "18+", label: "Years Experience" },
                  { value: "265+", label: "Cases Handled" },
                  { value: "24/7", label: "Availability" },
                  { value: "99%", label: "Success Rate" },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-xl border border-[var(--page-border)] bg-[var(--page-hover)] p-4 text-center"
                  >
                    <div className="text-2xl font-bold text-[var(--accent)]">
                      {stat.value}
                    </div>
                    <div className="text-sm text-[var(--page-text-muted)]">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className={tokens.section}>
        <div className={tokens.container}>
          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                icon: Target,
                value: "81%",
                title: "Legal Methods",
                desc: "Advanced legal analysis techniques",
              },
              {
                icon: TrendingUp,
                value: "68%",
                title: "Remote Advice",
                desc: "Digital legal consultation services",
              },
              {
                icon: Shield,
                value: "79%",
                title: "Strong Cases",
                desc: "Robust legal case preparation",
              },
            ].map((item) => (
              <SpotlightCard
                key={item.title}
                className="rounded-2xl border border-[var(--page-border)] bg-[rgba(15,28,36,0.6)] p-8 text-center backdrop-blur-sm"
              >
                <div className={cn(tokens.iconBadge, "mx-auto mb-4")}>
                  <item.icon className="h-7 w-7" />
                </div>
                <div className="mb-2 text-3xl font-bold text-[var(--accent)]">
                  {item.value}
                </div>
                <h3 className="mb-2 text-xl font-semibold">{item.title}</h3>
                <p className="text-sm text-[var(--page-text-muted)]">{item.desc}</p>
              </SpotlightCard>
            ))}
          </div>
        </div>
      </section>

      <section id="contact" className={cn(tokens.section, "bg-[var(--page-hover)]")}>
        <div className="mx-auto max-w-2xl px-4">
          <div className="mb-12 text-center">
            <h2 className={cn(tokens.heading, "mb-4 text-4xl")}>
              Get In Touch
            </h2>
            <p className="text-[var(--page-text-muted)]">
              Schedule a consultation with our legal team
            </p>
          </div>

          <form className="space-y-5 rounded-2xl border border-[var(--page-border)] bg-[rgba(15,28,36,0.6)] p-8 backdrop-blur-sm">
            <div className="grid gap-5 md:grid-cols-2">
              <input
                type="text"
                placeholder="Your name"
                className="rounded-xl border border-[var(--page-border)] bg-[rgba(8,14,18,0.8)] px-4 py-3 text-sm outline-none focus:border-[var(--primary-gold)]/50"
              />
              <input
                type="email"
                placeholder="your@email.com"
                className="rounded-xl border border-[var(--page-border)] bg-[rgba(8,14,18,0.8)] px-4 py-3 text-sm outline-none focus:border-[var(--primary-gold)]/50"
              />
            </div>
            <textarea
              rows={4}
              placeholder="Describe your legal matter..."
              className="w-full rounded-xl border border-[var(--page-border)] bg-[rgba(8,14,18,0.8)] px-4 py-3 text-sm outline-none focus:border-[var(--primary-gold)]/50"
            />
            <div className="text-center">
              <Button size="lg" className="w-full md:w-auto">
                Submit Request
              </Button>
            </div>
          </form>
        </div>
      </section>

      <section className={tokens.section}>
        <div className={tokens.container}>
          <div className="mb-12 text-center">
            <h2 className={cn(tokens.heading, "mb-4 text-4xl")}>
              Client Testimonials
            </h2>
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            {[
              {
                quote:
                  "VerdictAI provided clear, actionable legal guidance that saved me thousands in potential legal fees.",
                name: "Sarah M.",
                role: "Business Owner",
              },
              {
                quote:
                  "The best legal tool I've used. Fast, accurate, and affordable for complex legal questions.",
                name: "Ahmed K.",
                role: "Legal Consultant",
              },
            ].map((t) => (
              <SpotlightCard
                key={t.name}
                className="h-full rounded-2xl border border-[var(--page-border)] bg-[rgba(15,28,36,0.6)] p-8 backdrop-blur-sm"
              >
                <div className="mb-4 flex gap-1">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <Star
                      key={j}
                      className="h-4 w-4 fill-[var(--primary-gold)] text-[var(--accent)]"
                    />
                  ))}
                </div>
                <Quote className="mb-3 h-6 w-6 text-[var(--accent)]/60" />
                <p className="mb-6 text-[var(--page-text-muted)]">&ldquo;{t.quote}&rdquo;</p>
                <div>
                  <p className="font-semibold">{t.name}</p>
                  <p className="text-sm text-[var(--page-text-muted)]">{t.role}</p>
                </div>
              </SpotlightCard>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-white/5 bg-[#080f14] py-12">
        <div className={tokens.container}>
          <div className="grid gap-8 md:grid-cols-3">
            <div>
              <h3 className="mb-2 text-lg font-bold">VerdictAI</h3>
              <p className="text-sm text-[var(--page-text-muted)]">
                AI-powered legal assistance for everyone.
              </p>
            </div>
            <div>
              <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-white/40">
                Contact
              </h4>
              <ul className="space-y-2 text-sm text-[var(--page-text-muted)]">
                <li className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  <a href="mailto:contact@verdictai.com">contact@verdictai.com</a>
                </li>
                <li className="flex items-center gap-2">
                  <Phone className="h-4 w-4" />
                  <span>+880 123 456 789</span>
                </li>
                <li className="flex items-center gap-2">
                  <MapPin className="h-4 w-4" />
                  <span>Dhaka, Bangladesh</span>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="mb-3 text-sm font-semibold uppercase tracking-wider text-white/40">
                Quick Links
              </h4>
              <ul className="space-y-2 text-sm text-[var(--page-text-muted)]">
                <li>
                  <Link href="/login">Log in</Link>
                </li>
                <li>
                  <Link href="/signup">Sign up</Link>
                </li>
                <li>
                  <button
                    onClick={() => setShowChat(true)}
                    className="hover:text-[var(--accent)]"
                  >
                    Legal Chat
                  </button>
                </li>
              </ul>
            </div>
          </div>
          <p className="mt-10 text-center text-xs text-white/40">
            &copy; 2024 VerdictAI. All rights reserved.
          </p>
        </div>
      </footer>

      {showChat && <ChatPanel onClose={() => setShowChat(false)} />}

      {!showChat && (
        <button
          onClick={() => setShowChat(true)}
          className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--primary-gold)] text-[#0f1c24] shadow-lg shadow-[var(--primary-gold)]/20"
          aria-label="Open chat"
        >
          <Scale className="h-6 w-6" />
        </button>
      )}
    </div>
  );
}
