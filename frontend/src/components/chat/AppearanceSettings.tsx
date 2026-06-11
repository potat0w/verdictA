"use client";

import { Monitor, Moon, Palette, Sun, X } from "lucide-react";
import { ACCENT_PRESETS } from "@/lib/theme-settings";
import { useTheme } from "@/components/ThemeProvider";
import type { ThemeMode } from "@/lib/theme-settings";

interface AppearanceSettingsProps {
  open: boolean;
  onClose: () => void;
}

const MODES: { id: ThemeMode; label: string; icon: typeof Sun }[] = [
  { id: "light", label: "Light", icon: Sun },
  { id: "dark", label: "Dark", icon: Moon },
  { id: "system", label: "System", icon: Monitor },
];

export default function AppearanceSettings({
  open,
  onClose,
}: AppearanceSettingsProps) {
  const { settings, setMode, setAccent } = useTheme();

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-md rounded-2xl border border-[var(--chat-border)] bg-[var(--chat-surface)] p-6 shadow-2xl">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Palette className="h-5 w-5 text-[var(--accent)]" />
            <h3 className="text-lg font-semibold text-[var(--chat-text)]">
              Appearance
            </h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[var(--chat-text-muted)] hover:bg-[var(--chat-hover)]"
            aria-label="Close settings"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mb-6">
          <p className="mb-3 text-sm font-medium text-[var(--chat-text-muted)]">
            Color mode
          </p>
          <div className="grid grid-cols-3 gap-2">
            {MODES.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setMode(id)}
                className={`flex flex-col items-center gap-2 rounded-xl border px-3 py-3 text-sm transition-colors ${
                  settings.mode === id
                    ? "border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--chat-text)]"
                    : "border-[var(--chat-border)] text-[var(--chat-text-muted)] hover:bg-[var(--chat-hover)]"
                }`}
              >
                <Icon className="h-5 w-5" />
                {label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="mb-3 text-sm font-medium text-[var(--chat-text-muted)]">
            Accent color
          </p>
          <div className="grid grid-cols-4 gap-3">
            {ACCENT_PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => setAccent(preset.color)}
                title={preset.label}
                className={`group flex flex-col items-center gap-1.5 ${
                  settings.accent.toLowerCase() === preset.color.toLowerCase()
                    ? "opacity-100"
                    : "opacity-80 hover:opacity-100"
                }`}
              >
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-full transition-transform group-hover:scale-105 ${
                    settings.accent.toLowerCase() === preset.color.toLowerCase()
                      ? "ring-2 ring-[var(--chat-text)] ring-offset-2 ring-offset-[var(--chat-surface)]"
                      : ""
                  }`}
                  style={{ backgroundColor: preset.color }}
                />
                <span className="text-[10px] text-[var(--chat-text-muted)]">
                  {preset.label}
                </span>
              </button>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-3">
            <label className="text-sm text-[var(--chat-text-muted)]">
              Custom
            </label>
            <input
              type="color"
              value={settings.accent}
              onChange={(e) => setAccent(e.target.value)}
              className="h-9 w-14 cursor-pointer rounded-lg border border-[var(--chat-border)] bg-transparent"
            />
            <span className="text-xs font-mono text-[var(--chat-text-muted)]">
              {settings.accent}
            </span>
          </div>
        </div>

        <div className="mt-6 rounded-xl border border-[var(--chat-border)] p-4">
          <p className="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--chat-text-muted)]">
            Preview
          </p>
          <div className="flex flex-col gap-2">
            <div
              className="self-end rounded-2xl rounded-tr-sm px-4 py-2 text-sm font-medium"
              style={{
                background: `linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 80%, #000))`,
                color: "var(--accent-text)",
              }}
            >
              Your message
            </div>
            <div className="flex gap-2">
              <div
                className="flex h-7 w-7 items-center justify-center rounded-lg"
                style={{
                  background: "color-mix(in srgb, var(--accent) 15%, transparent)",
                  color: "var(--accent)",
                }}
              >
                <span className="text-xs">AI</span>
              </div>
              <div className="flex-1 rounded-2xl rounded-tl-sm border border-[var(--chat-border)] bg-[var(--chat-bubble-assistant)] px-4 py-2 text-sm text-[var(--chat-text)]">
                Assistant reply preview
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
