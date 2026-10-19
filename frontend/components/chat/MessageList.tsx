"use client";

import { useEffect, useRef } from "react";

import type { ChatMessage, Citation } from "@/types";

import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

interface Props {
  messages: ChatMessage[];
  sending: boolean;
  onRegenerate: () => void;
  onRetry: () => void;
  onOpenSource: (citation: Citation) => void;
}

export function MessageList({ messages, sending, onRegenerate, onRetry, onOpenSource }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, sending]);

  return (
    <div className="space-y-4" aria-live="polite">
      {messages.map((message, i) => (
        <MessageBubble
          key={message.id}
          message={message}
          isLast={i === messages.length - 1}
          busy={sending}
          onRegenerate={onRegenerate}
          onRetry={onRetry}
          onOpenSource={onOpenSource}
        />
      ))}
      {sending && (
        <div className="rounded-2xl rounded-bl-sm border border-border bg-card/60 p-4">
          <TypingIndicator />
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
