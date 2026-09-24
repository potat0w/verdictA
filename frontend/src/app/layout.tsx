import type { Metadata } from "next";
import "./globals.css";
import ToastProvider from "@/components/ui/Toast";

export const metadata: Metadata = {
  title: "VerdictAI — Your Constitution, explained.",
  description:
    "A calm, bilingual constitutional companion grounded in the official Constitution of Bangladesh.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased" suppressHydrationWarning>
        <ToastProvider />
        {children}
      </body>
    </html>
  );
}
