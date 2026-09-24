"use client";

import { useState } from "react";
import { ArrowUpRight, Menu, X } from "lucide-react";
import { useChat } from "@/components/chat/ChatContext";
import SiteLayout from "@/components/layout/SiteLayout";

const steps = [
  [
    "01",
    "Ask naturally",
    "Write your question in Bangla or English, just as you would ask it.",
  ],
  [
    "02",
    "Understand clearly",
    "VerdictAI explains the relevant constitutional principles in plain language.",
  ],
  [
    "03",
    "Read the source",
    "Every answer points you back to the article that grounds it.",
  ],
] as const;

function LandingPage() {
  const { openChat } = useChat();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <main className="site-shell">
      <header className="site-nav" aria-label="Main navigation">
        <a className="wordmark" href="#top" aria-label="VerdictAI home">
          verdict<span>ai</span>
        </a>
        <nav className="desktop-nav" aria-label="Primary">
          <button type="button" onClick={openChat}>
            Chat
          </button>
          <a href="#about">About</a>
          <a href="#contact">Contact</a>
        </nav>
        <button type="button" className="nav-cta" onClick={openChat}>
          Open chat <ArrowUpRight size={14} strokeWidth={1.5} />
        </button>
        <button
          className="mobile-menu"
          type="button"
          aria-label="Open navigation"
          onClick={() => setMobileOpen((v) => !v)}
        >
          {mobileOpen ? <X size={20} strokeWidth={1.5} /> : <Menu size={20} strokeWidth={1.5} />}
        </button>
      </header>

      {mobileOpen && (
        <div
          className="flex flex-col gap-4 px-6 pb-6 text-xs uppercase tracking-[0.12em] md:hidden"
          style={{ borderBottom: "1px solid var(--line)" }}
        >
          <button type="button" className="text-left" onClick={() => { openChat(); setMobileOpen(false); }}>
            Chat
          </button>
          <a href="#about" onClick={() => setMobileOpen(false)}>
            About
          </a>
          <a href="#contact" onClick={() => setMobileOpen(false)}>
            Contact
          </a>
        </div>
      )}

      <section id="top" className="hero" aria-labelledby="hero-title">
        <div
          className="hero-image"
          role="img"
          aria-label="Constitutional paper in soft afternoon light"
        />
        <div className="hero-copy">
          <p className="eyebrow">
            A constitutional companion / সংবিধানের সঙ্গী
          </p>
          <h1 id="hero-title">
            Your Constitution,
            <br />
            <em>explained.</em>
          </h1>
          <p className="hero-intro">
            A calm, careful way to understand the Constitution of Bangladesh —
            in Bangla or English.
          </p>
          <button type="button" className="button button-dark" onClick={openChat}>
            Ask a question <ArrowUpRight size={16} strokeWidth={1.5} />
          </button>
        </div>
        <p className="hero-note">
          Dhaka / Bangladesh
          <br />
          01 — 04
        </p>
      </section>

      <section className="intro-band" id="about" aria-labelledby="intro-title">
        <p className="section-label">01 / The approach</p>
        <div>
          <h2 id="intro-title">
            Make the law
            <br />
            <em>legible.</em>
          </h2>
          <p className="intro-text">
            VerdictAI brings the country&apos;s foundational text closer to
            everyday life. No jargon, no guessing — just thoughtful answers tied
            to the words that matter.
          </p>
        </div>
      </section>

      <section className="steps-section" aria-labelledby="steps-title">
        <div className="section-heading">
          <p className="section-label">02 / How it works</p>
          <h2 id="steps-title">
            Three steps
            <br />
            <em>to clarity.</em>
          </h2>
        </div>
        <div className="steps-list">
          {steps.map(([number, title, body]) => (
            <article className="step" key={number}>
              <span className="step-number">{number}</span>
              <div>
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
              <ArrowUpRight className="step-arrow" size={18} strokeWidth={1.5} />
            </article>
          ))}
        </div>
      </section>

      <section className="trust-section" aria-label="Trust and source">
        <p className="section-label">03 / The source</p>
        <blockquote>
          “Built on the official text
          <br />
          of the <em>Bangladesh Constitution.</em>”
        </blockquote>
        <div className="trust-meta">
          <p>
            Answers are grounded in the Constitution of the People&apos;s
            Republic of Bangladesh — with references to specific articles, in
            both languages.
          </p>
          <span>
            Established 2026
            <br />
            Dhaka, BD
          </span>
        </div>
      </section>

      <section className="chat-section" id="chat" aria-labelledby="chat-title">
        <div className="section-heading">
          <p className="section-label">04 / A small example</p>
          <h2 id="chat-title">
            Questions deserve
            <br />
            <em>good answers.</em>
          </h2>
        </div>
        <div className="chat-paper">
          <div className="chat-topline">
            <span>VerdictAI / sample exchange</span>
            <span>বাংলা + English</span>
          </div>
          <div className="question">
            <span className="chat-label">You asked</span>
            <p>
              “What does the Constitution say about equality before the law?”
            </p>
          </div>
          <div className="answer">
            <span className="chat-label">VerdictAI</span>
            <p>
              Article 27 establishes that all citizens are equal before law and
              are entitled to equal protection of law.
            </p>
            <p className="citation">
              Constitution of Bangladesh / Article 27{" "}
              <ArrowUpRight size={14} />
            </p>
          </div>
        </div>
        <button type="button" className="button button-outline" onClick={openChat}>
          Open the conversation <ArrowUpRight size={16} strokeWidth={1.5} />
        </button>
      </section>

      <footer id="contact" className="site-footer">
        <div>
          <a className="wordmark" href="#top">
            verdict<span>ai</span>
          </a>
          <p>
            Constitutional clarity,
            <br />
            in two languages.
          </p>
        </div>
        <div className="footer-links">
          <button type="button" onClick={openChat}>
            Chat
          </button>
          <a href="#about">About</a>
          <a href="mailto:hello@verdictai.bd">hello@verdictai.bd</a>
        </div>
        <div className="footer-bottom">
          <span>© 2026 VerdictAI</span>
          <span>Made for Bangladesh</span>
        </div>
      </footer>
    </main>
  );
}

export default function Home() {
  return (
    <SiteLayout>
      <LandingPage />
    </SiteLayout>
  );
}
