import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { raleway, merriweather } from "@/lib/fonts";
import ToastProvider from "@/components/ui/Toast";
import { ThemeProvider } from "@/components/ThemeProvider";

export const metadata: Metadata = {
  title: "VerdictAI - AI-Powered Legal Assistance",
  description:
    "Smart, fast, and accurate legal solutions tailored to your needs. Get instant legal answers from trusted datasets with expert-reviewed solutions powered by AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${raleway.variable} ${merriweather.variable}`}
      suppressHydrationWarning
    >
      <head>
        <Script id="theme-init" strategy="beforeInteractive">
          {`
            try {
              var s = JSON.parse(localStorage.getItem('verdictai-theme') || '{}');
              var mode = s.mode || 'dark';
              var resolved = mode === 'system'
                ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
                : mode;
              document.documentElement.setAttribute('data-theme', resolved);
              if (s.accent) {
                document.documentElement.style.setProperty('--accent', s.accent);
                document.documentElement.style.setProperty('--primary-gold', s.accent);
              }
            } catch (e) {}
          `}
        </Script>
      </head>
      <body
        className="min-h-screen bg-legal-gradient font-raleway antialiased text-[var(--page-text)]"
        suppressHydrationWarning
      >
        <ThemeProvider>
          <ToastProvider />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
