"use client";

import Link from "next/link";
import { FaGavel } from "react-icons/fa";
import Button from "@/components/ui/Button";
import ThemeToggle from "@/components/ThemeToggle";
import { tokens } from "@/lib/theme";

const NAV_LINKS = [
  { href: "#services", label: "Services" },
  { href: "#about", label: "About" },
  { href: "#contact", label: "Contact" },
] as const;

interface NavbarProps {
  hasToken: boolean;
  onLogout: () => void;
}

export default function Navbar({ hasToken, onLogout }: NavbarProps) {
  return (
    <nav className="sticky top-0 z-50 border-b border-[var(--page-border)] bg-[var(--page-surface)] backdrop-blur-xl">
      <div className={tokens.container}>
        <div className="flex items-center justify-between py-4">
          <Link href="/" className="group flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{
                background:
                  "color-mix(in srgb, var(--accent) 12%, transparent)",
              }}
            >
              <FaGavel className="text-xl" style={{ color: "var(--accent)" }} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-[var(--page-text)]">
                VerdictAI
              </h1>
              <p
                className="text-[10px] uppercase tracking-[0.2em]"
                style={{ color: "var(--accent)" }}
              >
                Legal Intelligence
              </p>
            </div>
          </Link>

          <div className="hidden items-center gap-8 text-sm text-[var(--page-text-muted)] md:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="hover:text-[var(--accent)]"
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            {hasToken ? (
              <>
                <Link
                  href="/profile"
                  className="text-sm text-[var(--page-text-muted)] hover:text-[var(--accent)]"
                >
                  Profile
                </Link>
                <Button variant="outline" size="sm" onClick={onLogout}>
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-sm text-[var(--page-text-muted)] hover:text-[var(--accent)]"
                >
                  Log in
                </Link>
                <Link href="/signup">
                  <Button variant="outline" size="sm">
                    Sign up
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
