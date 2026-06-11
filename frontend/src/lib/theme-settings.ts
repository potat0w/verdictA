export type ThemeMode = "light" | "dark" | "system";

export type AccentPreset = {
  id: string;
  label: string;
  color: string;
};

export const ACCENT_PRESETS: AccentPreset[] = [
  { id: "gold", label: "Gold", color: "#c8ab7f" },
  { id: "green", label: "Green", color: "#10a37f" },
  { id: "blue", label: "Blue", color: "#3b82f6" },
  { id: "purple", label: "Purple", color: "#8b5cf6" },
  { id: "rose", label: "Rose", color: "#f43f5e" },
  { id: "orange", label: "Orange", color: "#f97316" },
  { id: "teal", label: "Teal", color: "#14b8a6" },
  { id: "slate", label: "Slate", color: "#64748b" },
];

export type ThemeSettings = {
  mode: ThemeMode;
  accent: string;
};

export const DEFAULT_THEME: ThemeSettings = {
  mode: "dark",
  accent: "#c8ab7f",
};

const STORAGE_KEY = "verdictai-theme";

export function loadThemeSettings(): ThemeSettings {
  if (typeof window === "undefined") return DEFAULT_THEME;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_THEME;
    const parsed = JSON.parse(raw) as Partial<ThemeSettings>;
    return {
      mode: parsed.mode ?? DEFAULT_THEME.mode,
      accent: parsed.accent ?? DEFAULT_THEME.accent,
    };
  } catch {
    return DEFAULT_THEME;
  }
}

export function saveThemeSettings(settings: ThemeSettings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function resolveThemeMode(mode: ThemeMode): "light" | "dark" {
  if (mode === "system" && typeof window !== "undefined") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return mode === "light" ? "light" : "dark";
}

export function getAccentTextColor(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.6 ? "#0f1c24" : "#ffffff";
}

export function applyThemeToDocument(settings: ThemeSettings) {
  const resolved = resolveThemeMode(settings.mode);
  const root = document.documentElement;
  root.setAttribute("data-theme", resolved);
  root.style.setProperty("--accent", settings.accent);
  root.style.setProperty("--accent-text", getAccentTextColor(settings.accent));
  root.style.setProperty("--primary-gold", settings.accent);
}
