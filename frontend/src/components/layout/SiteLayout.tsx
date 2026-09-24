"use client";

import { ReactNode, useState } from "react";
import ChatPanel from "@/components/chat/ChatPanel";
import { ChatContext } from "@/components/chat/ChatContext";

interface SiteLayoutProps {
  children: ReactNode;
}

export default function SiteLayout({ children }: SiteLayoutProps) {
  const [showChat, setShowChat] = useState(false);

  return (
    <ChatContext.Provider value={{ openChat: () => setShowChat(true) }}>
      {children}
      {showChat && <ChatPanel onClose={() => setShowChat(false)} />}
    </ChatContext.Provider>
  );
}
