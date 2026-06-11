"use client";

import Link from "next/link";
import { ArrowUpRight, Bot, Mail, MapPin, Phone } from "lucide-react";
import { cn, tokens } from "@/lib/theme";
import Button from "@/components/ui/Button";

const FOOTER_LINKS = {
  pages: [
    { href: "/", label: "Home" },
    { href: "/product", label: "Product" },
    { href: "/services", label: "Service" },
    { href: "/contact", label: "Contact" },
  ],
  account: [
    { href: "/login", label: "Log in" },
    { href: "/signup", label: "Sign up" },
    { href: "/profile", label: "Profile" },
  ],
  legal: [
    { href: "#", label: "Privacy Policy" },
    { href: "#", label: "Terms of Service" },
    { href: "#", label: "Disclaimer" },
  ],
};

interface SiteFooterProps {
  onOpenChat?: () => void;
}

export default function SiteFooter({ onOpenChat }: SiteFooterProps) {
  return (
    <footer className="relative mt-8">
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{
          background:
            "linear-gradient(90deg, transparent, color-mix(in srgb, var(--accent) 50%, transparent), transparent)",
        }}
      />

      <div className={cn(tokens.container, "relative py-16 md:py-20")}>
        <div className="mb-12 overflow-hidden rounded-2xl border border-[var(--page-border)] bg-[var(--page-card)] p-8 backdrop-blur-md md:p-10">
          <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-[0.2em] text-[var(--accent)]">
                Ready to chat?
              </p>
              <h3 className="font-merriweather text-2xl font-bold text-[var(--page-text)] md:text-3xl">
                Open the AI chatbot
              </h3>
              <p className="mt-2 max-w-md text-sm text-[var(--page-text-muted)]">
                Ask any legal question and get an instant AI-powered answer.
              </p>
            </div>
            {onOpenChat && (
              <Button onClick={onOpenChat} size="lg" className="gap-2 shrink-0">
                Open Chatbot
                <ArrowUpRight className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-12 lg:gap-8">
          <div className="lg:col-span-4">
            <Link href="/" className="mb-5 inline-flex items-center gap-3">
              <div
                className="flex h-11 w-11 items-center justify-center rounded-xl"
                style={{
                  background:
                    "color-mix(in srgb, var(--accent) 14%, transparent)",
                }}
              >
                <Bot className="text-lg" style={{ color: "var(--accent)" }} />
              </div>
              <div>
                <p className="text-lg font-bold text-[var(--page-text)]">
                  VerdictAI
                </p>
                <p
                  className="text-[10px] uppercase tracking-[0.2em]"
                  style={{ color: "var(--accent)" }}
                >
                  AI Legal Chatbot
                </p>
              </div>
            </Link>
            <p className="max-w-xs text-sm leading-relaxed text-[var(--page-text-muted)]">
              Your intelligent legal chatbot — ask questions, get instant
              AI-powered answers anytime.
            </p>
          </div>

          <div className="lg:col-span-2">
            <p className="mb-4 text-sm font-semibold text-[var(--page-text)]">
              Navigate
            </p>
            <ul className="space-y-2.5">
              {FOOTER_LINKS.pages.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-[var(--page-text-muted)] hover:text-[var(--accent)]"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-2">
            <p className="mb-4 text-sm font-semibold text-[var(--page-text)]">
              Account
            </p>
            <ul className="space-y-2.5">
              {FOOTER_LINKS.account.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-[var(--page-text-muted)] hover:text-[var(--accent)]"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-4">
            <p className="mb-4 text-sm font-semibold text-[var(--page-text)]">
              Contact
            </p>
            <ul className="space-y-3">
              <li>
                <a
                  href="mailto:contact@verdictai.com"
                  className="flex items-center gap-3 text-sm text-[var(--page-text-muted)] hover:text-[var(--accent)]"
                >
                  <span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--page-border)]"
                    style={{
                      background:
                        "color-mix(in srgb, var(--accent) 8%, transparent)",
                    }}
                  >
                    <Mail className="h-4 w-4" style={{ color: "var(--accent)" }} />
                  </span>
                  contact@verdictai.com
                </a>
              </li>
              <li>
                <a
                  href="tel:+880123456789"
                  className="flex items-center gap-3 text-sm text-[var(--page-text-muted)] hover:text-[var(--accent)]"
                >
                  <span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--page-border)]"
                    style={{
                      background:
                        "color-mix(in srgb, var(--accent) 8%, transparent)",
                    }}
                  >
                    <Phone className="h-4 w-4" style={{ color: "var(--accent)" }} />
                  </span>
                  +880 123 456 789
                </a>
              </li>
              <li className="flex items-center gap-3 text-sm text-[var(--page-text-muted)]">
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--page-border)]"
                  style={{
                    background:
                      "color-mix(in srgb, var(--accent) 8%, transparent)",
                  }}
                >
                  <MapPin className="h-4 w-4" style={{ color: "var(--accent)" }} />
                </span>
                Dhaka, Bangladesh
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col gap-4 border-t border-[var(--page-border)] pt-8 md:flex-row md:items-center md:justify-between">
          <p className="text-xs text-[var(--page-text-muted)]">
            &copy; {new Date().getFullYear()} VerdictAI. All rights reserved.
          </p>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            {FOOTER_LINKS.legal.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="text-xs text-[var(--page-text-muted)] hover:text-[var(--accent)]"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
