"use client";

import { useEffect, useState, ReactNode } from "react";
import { Scale } from "lucide-react";
import { clearToken, getToken } from "@/lib/api";
import Navbar from "@/components/layout/Navbar";
import SiteFooter from "@/components/layout/SiteFooter";
import ChatPanel from "@/components/chat/ChatPanel";
import { ChatContext } from "@/components/chat/ChatContext";

interface SiteLayoutProps {
  children: ReactNode;
  showChatFab?: boolean;
}

export default function SiteLayout({
  children,
  showChatFab = true,
}: SiteLayoutProps) {
  const [showChat, setShowChat] = useState(false);
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(!!getToken());
    const onStorage = () => setHasToken(!!getToken());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return (
    <ChatContext.Provider value={{ openChat: () => setShowChat(true) }}>
      <div className="relative min-h-screen overflow-x-hidden bg-legal-gradient">
        <Navbar
          hasToken={hasToken}
          onLogout={() => {
            clearToken();
            setHasToken(false);
          }}
        />
        <main>{children}</main>
        <SiteFooter onOpenChat={() => setShowChat(true)} />
        {showChat && <ChatPanel onClose={() => setShowChat(false)} />}
        {showChatFab && !showChat && (
          <button
            onClick={() => setShowChat(true)}
            className="chat-send-btn fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-2xl shadow-lg"
            style={{
              boxShadow:
                "0 8px 32px color-mix(in srgb, var(--accent) 25%, transparent)",
            }}
            aria-label="Open chat"
          >
            <Scale className="h-6 w-6" />
          </button>
        )}
      </div>
    </ChatContext.Provider>
  );
}
