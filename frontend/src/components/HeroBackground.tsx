export default function HeroBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden>
      <div className="absolute inset-0 bg-[var(--page-bg)]" />
      <div
        className="absolute -top-1/4 -right-1/4 h-[70%] w-[70%] rounded-full blur-[120px]"
        style={{
          background: "color-mix(in srgb, var(--accent) 8%, transparent)",
        }}
      />
      <div className="absolute -bottom-1/4 -left-1/4 h-[60%] w-[60%] rounded-full bg-[color-mix(in_srgb,var(--page-text)_4%,transparent)] blur-[100px]" />
      <div
        className="absolute inset-0 opacity-[0.04] [data-theme=light]:opacity-[0.06]"
        style={{
          backgroundImage:
            "linear-gradient(color-mix(in srgb, var(--accent) 50%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, var(--accent) 50%, transparent) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[var(--page-bg)]/50 to-[var(--page-bg)]" />
    </div>
  );
}
