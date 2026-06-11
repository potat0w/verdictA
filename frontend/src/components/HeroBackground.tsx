export default function HeroBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden>
      <div
        className="absolute -left-[20%] top-[10%] h-[500px] w-[500px] rounded-full blur-[140px]"
        style={{
          background: "color-mix(in srgb, var(--accent) 18%, transparent)",
        }}
      />
      <div
        className="absolute -right-[10%] top-[20%] h-[400px] w-[400px] rounded-full blur-[120px]"
        style={{
          background: "color-mix(in srgb, var(--accent) 10%, transparent)",
        }}
      />
      <div
        className="absolute bottom-0 left-1/2 h-[300px] w-[600px] -translate-x-1/2 rounded-full blur-[100px]"
        style={{
          background: "color-mix(in srgb, var(--page-text) 5%, transparent)",
        }}
      />

      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, color-mix(in srgb, var(--accent) 35%, transparent) 1px, transparent 0)",
          backgroundSize: "40px 40px",
        }}
      />

      <div
        className="absolute inset-x-0 top-0 h-px opacity-60"
        style={{
          background:
            "linear-gradient(90deg, transparent, color-mix(in srgb, var(--accent) 60%, transparent), transparent)",
        }}
      />

      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[var(--page-bg)]" />
    </div>
  );
}
