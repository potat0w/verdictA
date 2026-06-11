import { clsx } from "clsx";

export function cn(...inputs: Array<string | undefined | false | null>) {
  return clsx(inputs.filter(Boolean));
}

// Reusable design tokens aligned to the dark navy + gold theme
export const tokens = {
  // Layout
  container: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
  section: "py-20 px-4 sm:px-6 lg:px-8",

  // Colors
  text: {
    base: "text-[var(--page-text)]",
    muted: "text-[var(--page-text-muted)]",
    gold: "text-[var(--accent)]",
  },
  bg: {
    base: "bg-[var(--primary-dark)]",
    gradient: "bg-legal-gradient",
  },
  border: {
    subtle: "border border-[rgba(200,171,127,0.15)]",
    gold: "border border-[var(--primary-gold)]",
  },

  // Surfaces
  surface: {
    panel:
      "bg-[rgba(15,28,36,0.85)] backdrop-blur-sm border border-[rgba(200,171,127,0.20)] rounded-xl",
    card:
      "bg-[rgba(15,28,36,0.75)] backdrop-blur-sm border border-[rgba(200,171,127,0.18)] rounded-xl",
  },

  // Typography
  heading: "font-merriweather font-bold text-[var(--page-text)]",

  // Buttons
  button: {
    base:
      "inline-flex items-center justify-center rounded-lg font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-0",
    primary:
      "bg-[var(--accent)] text-[var(--accent-text)] hover:brightness-110 focus-visible:ring-[var(--accent)]",
    outline:
      "border-2 border-[var(--accent)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-[var(--accent-text)]",
    ghost:
      "text-[var(--page-text)] hover:bg-[var(--page-hover)]",
    size: {
      sm: "px-3 py-2 text-sm",
      md: "px-5 py-2.5",
      lg: "px-8 py-4 text-lg",
    },
  },

  // Badges / Icon containers
  iconBadge:
    "w-16 h-16 rounded-xl flex items-center justify-center bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--accent)]",
}; 