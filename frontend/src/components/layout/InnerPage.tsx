"use client";

import Link from "next/link";
import { ReactNode } from "react";
import SiteLayout from "@/components/layout/SiteLayout";
import { useChat } from "@/components/chat/ChatContext";

export default function InnerPage({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const { openChat } = useChat();

  return (
    <div className="page-shell">
      <header className="site-nav">
        <Link className="wordmark" href="/">
          verdict<span>ai</span>
        </Link>
        <nav className="desktop-nav" aria-label="Primary">
          <button type="button" onClick={openChat}>
            Chat
          </button>
          <Link href="/#about">About</Link>
          <Link href="/contact">Contact</Link>
        </nav>
        <button type="button" className="nav-cta" onClick={openChat}>
          Open chat
        </button>
      </header>
      <div className="content">
        <h1>{title}</h1>
        {children}
      </div>
      <footer className="site-footer">
        <div className="footer-top">
          <div className="footer-brand">
            <Link className="wordmark" href="/">
              verdict<span>ai</span>
            </Link>
            <p>Constitutional clarity, in two languages.</p>
          </div>
          <div className="footer-links">
            <button type="button" onClick={openChat}>
              Chat
            </button>
            <Link href="/#about">About</Link>
            <a href="mailto:hello@verdictai.bd">hello@verdictai.bd</a>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© 2026 VerdictAI</span>
          <span>Made for Bangladesh</span>
        </div>
      </footer>
    </div>
  );
}

export function withSiteChat(children: ReactNode) {
  return <SiteLayout>{children}</SiteLayout>;
}
