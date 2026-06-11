import type { Metadata } from "next";
import "./globals.css";
import { raleway, merriweather } from "@/lib/fonts";
import { THEME_INIT_SCRIPT } from "@/lib/theme-init-script";
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
      data-theme="dark"
      suppressHydrationWarning
    >
      <body
        className="min-h-screen bg-legal-gradient font-raleway antialiased text-[var(--page-text)]"
        suppressHydrationWarning
      >
        <script
          dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }}
          suppressHydrationWarning
        />
        <ThemeProvider>
          <ToastProvider />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
