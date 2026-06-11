"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

export default function ThemeToggle({ className = "" }: { className?: string }) {
  const { resolvedMode, setMode } = useTheme();

  return (
    <button
      onClick={() => setMode(resolvedMode === "dark" ? "light" : "dark")}
      className={`rounded-xl border border-[var(--page-border)] p-2 text-[var(--page-text-muted)] hover:bg-[var(--page-hover)] hover:text-[var(--page-text)] ${className}`}
      aria-label={`Switch to ${resolvedMode === "dark" ? "light" : "dark"} mode`}
    >
      {resolvedMode === "dark" ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
    </button>
  );
}
