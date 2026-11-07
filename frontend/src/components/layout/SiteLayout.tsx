"use client";

import { ReactNode, useState } from "react";
import ChatPanel from "@/components/chat/ChatPanel";
import { ChatContext } from "@/components/chat/ChatContext";

interface SiteLayoutProps {
  children: ReactNode;
}

export default function SiteLayout({ children }: SiteLayoutProps) {
  const [showChat, setShowChat] = useState(false);
  const [seedPrompt, setSeedPrompt] = useState<string | null>(null);

  return (
    <ChatContext.Provider
      value={{
        openChat: (prompt?: string) => {
          const text = typeof prompt === "string" ? prompt.trim() : "";
          setSeedPrompt(text || null);
          setShowChat(true);
        },
      }}
    >
      {children}
      {showChat && (
        <ChatPanel
          initialPrompt={seedPrompt}
          onClose={() => {
            setShowChat(false);
            setSeedPrompt(null);
          }}
        />
      )}
    </ChatContext.Provider>
  );
}
