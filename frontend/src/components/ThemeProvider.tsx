"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  applyThemeToDocument,
  DEFAULT_THEME,
  loadThemeSettings,
  resolveThemeMode,
  saveThemeSettings,
  type ThemeMode,
  type ThemeSettings,
} from "@/lib/theme-settings";

type ThemeContextValue = {
  settings: ThemeSettings;
  resolvedMode: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
  setAccent: (accent: string) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<ThemeSettings>(DEFAULT_THEME);
  const [resolvedMode, setResolvedMode] = useState<"light" | "dark">("dark");
  const [mounted, setMounted] = useState(false);

  const apply = useCallback((next: ThemeSettings) => {
    setSettings(next);
    const resolved = resolveThemeMode(next.mode);
    setResolvedMode(resolved);
    applyThemeToDocument(next);
    saveThemeSettings(next);
  }, []);

  useEffect(() => {
    const loaded = loadThemeSettings();
    apply(loaded);
    setMounted(true);
  }, [apply]);

  useEffect(() => {
    if (!mounted || settings.mode !== "system") return;

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => apply(settings);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [mounted, settings, apply]);

  const setMode = (mode: ThemeMode) => apply({ ...settings, mode });
  const setAccent = (accent: string) => apply({ ...settings, accent });

  return (
    <ThemeContext.Provider
      value={{ settings, resolvedMode, setMode, setAccent }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
