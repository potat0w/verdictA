export const THEME_INIT_SCRIPT = `
(function () {
  try {
    var s = JSON.parse(localStorage.getItem("verdictai-theme") || "{}");
    var mode = s.mode || "dark";
    var resolved =
      mode === "system"
        ? window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light"
        : mode;
    document.documentElement.setAttribute("data-theme", resolved);
    if (s.accent) {
      document.documentElement.style.setProperty("--accent", s.accent);
      document.documentElement.style.setProperty("--primary-gold", s.accent);
      var hex = s.accent.replace("#", "");
      var r = parseInt(hex.slice(0, 2), 16);
      var g = parseInt(hex.slice(2, 4), 16);
      var b = parseInt(hex.slice(4, 6), 16);
      var lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
      document.documentElement.style.setProperty(
        "--accent-text",
        lum > 0.6 ? "#0f1c24" : "#ffffff"
      );
    }
  } catch (e) {}
})();
`;
