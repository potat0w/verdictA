"use client";

import { useEffect, useRef, useState } from "react";
import { ConversationProvider, useConversation } from "@elevenlabs/react";
import { Mic } from "lucide-react";
import { getVoiceSession } from "@/lib/api";

type Language = "en" | "bn";

interface VoiceAskButtonProps {
  language: Language;
  disabled?: boolean;
  onTranscript: (id: string, role: "user" | "assistant", text: string) => void;
}

export default function VoiceAskButton(props: VoiceAskButtonProps) {
  return (
    <ConversationProvider>
      <VoiceSession {...props} />
    </ConversationProvider>
  );
}

function VoiceSession({ language, disabled, onTranscript }: VoiceAskButtonProps) {
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  const languageRef = useRef(language);
  const onTranscriptRef = useRef(onTranscript);
  const showingToolAnswer = useRef(false);
  onTranscriptRef.current = onTranscript;

  const conversation = useConversation({
    stripAudioTags: true,
    onAgentToolResponse: (props) => {
      if (!("full_tool_result" in props) || props.is_error) return;
      let answer = props.full_tool_result;
      try {
        const parsed = JSON.parse(props.full_tool_result) as { answer?: unknown };
        if (typeof parsed.answer === "string") answer = parsed.answer;
      } catch {
        answer = props.full_tool_result;
      }
      const text = answer.trim();
      if (!text) return;
      showingToolAnswer.current = true;
      onTranscriptRef.current(`voice-tool-${props.tool_call_id}`, "assistant", text);
    },
    onMessage: ({ message, role, event_id }) => {
      if (role !== "user" && showingToolAnswer.current) return;
      if (role === "user") showingToolAnswer.current = false;
      const text = message
        .replace(/\[[^\[\]\n]{1,40}\]/g, " ")
        .replace(/[ \t]{2,}/g, " ")
        .trim();
      if (!text) return;
      onTranscriptRef.current(
        `voice-${role}-${event_id}`,
        role === "user" ? "user" : "assistant",
        text
      );
    },
    onError: (message) => {
      setError(message || "Voice failed.");
    },
    onDisconnect: (details) => {
      started.current = false;
      if (details.reason === "user") return;
      const message =
        details.reason === "error"
          ? details.message
          : details.context?.reason || "Voice disconnected.";
      setError(message);
    },
  });
  const { endSession, startSession, status, isSpeaking } = conversation;
  const endSessionRef = useRef(endSession);
  endSessionRef.current = endSession;

  useEffect(() => {
    return () => {
      if (started.current) endSessionRef.current();
    };
  }, []);

  useEffect(() => {
    if (languageRef.current !== language && started.current) endSessionRef.current();
    languageRef.current = language;
  }, [language]);

  const live = status === "connected" || status === "connecting";

  const statusText = error
    ? error
    : status === "connecting"
      ? language === "bn"
        ? "সংযোগ হচ্ছে…"
        : "Connecting…"
      : status === "connected" && isSpeaking
        ? language === "bn"
          ? "বলছে…"
          : "Speaking"
        : status === "connected"
          ? language === "bn"
            ? "শুনছি…"
            : "Listening"
          : null;

  const toggle = async () => {
    setError(null);
    if (live) {
      endSession();
      return;
    }
    try {
      const probe = await navigator.mediaDevices.getUserMedia({ audio: true });
      probe.getTracks().forEach((track) => track.stop());
      const session = await getVoiceSession();
      started.current = true;
      if (session.conversationToken) {
        startSession({
          conversationToken: session.conversationToken,
          dynamicVariables: { language },
          stripAudioTags: true,
        });
      } else if (session.agentId) {
        startSession({
          agentId: session.agentId,
          dynamicVariables: { language },
          stripAudioTags: true,
        });
      } else {
        started.current = false;
        setError("Voice agent is not configured.");
      }
    } catch (err) {
      started.current = false;
      const name = err instanceof DOMException ? err.name : "";
      const detail = err instanceof Error ? err.message : "Voice failed.";
      const denied =
        name === "NotAllowedError" ||
        detail.toLowerCase().includes("permission") ||
        detail.toLowerCase().includes("notallowed");
      setError(
        denied
          ? language === "bn"
            ? "মাইক্রোফোনের অনুমতি দিন।"
            : "Allow microphone access to use voice."
          : detail
      );
    }
  };

  return (
    <>
      <button
        className={`voice-button${live ? " is-live" : ""}`}
        type="button"
        onClick={toggle}
        disabled={disabled && !live}
        aria-pressed={live}
        aria-label={live ? "Stop voice" : "Start voice"}
      >
        <Mic />
      </button>
      {statusText ? (
        <p className="voice-status" role="status">
          {statusText}
        </p>
      ) : null}
    </>
  );
}
