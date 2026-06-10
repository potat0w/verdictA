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
    base: "text-[var(--primary-off-white)]",
    muted: "text-white/70",
    gold: "text-[var(--primary-gold)]",
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
  heading: "font-merriweather font-bold text-[var(--primary-off-white)]",

  // Buttons
  button: {
    base:
      "inline-flex items-center justify-center rounded-lg font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-0",
    primary:
      "bg-[var(--primary-gold)] text-[#0f1c24] hover:brightness-110 focus-visible:ring-[var(--primary-gold)]",
    outline:
      "border-2 border-[var(--primary-gold)] text-[var(--primary-gold)] hover:bg-[var(--primary-gold)] hover:text-[#0f1c24]",
    ghost:
      "text-[var(--primary-off-white)] hover:bg-white/5",
    size: {
      sm: "px-3 py-2 text-sm",
      md: "px-5 py-2.5",
      lg: "px-8 py-4 text-lg",
    },
  },

  // Badges / Icon containers
  iconBadge:
    "w-16 h-16 rounded-xl flex items-center justify-center bg-[rgba(200,171,127,0.12)] text-[var(--primary-gold)]",
}; 