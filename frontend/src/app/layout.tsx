import type { Metadata } from "next";
import "./globals.css";
import { raleway, merriweather } from "@/lib/fonts";
import ToastProvider from "@/components/ui/Toast";

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
    <html lang="en" className={`${raleway.variable} ${merriweather.variable}`}>
      <body 
        className="antialiased font-raleway bg-legal-gradient text-[var(--primary-off-white)] min-h-screen"
        suppressHydrationWarning
      >
        <ToastProvider />
        {children}
      </body>
    </html>
  );
}
