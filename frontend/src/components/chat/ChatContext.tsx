"use client";

import { createContext, useContext } from "react";

type ChatContextValue = {
  openChat: (prompt?: string) => void;
};

export const ChatContext = createContext<ChatContextValue>({
  openChat: () => {},
});

export function useChat() {
  return useContext(ChatContext);
}
