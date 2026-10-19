"use client";

import { Check, Copy, RefreshCw, RotateCcw } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { formatMs } from "@/lib/format";
import type { ChatMessage, Citation } from "@/types";

import { AnswerMarkdown } from "./AnswerMarkdown";
import { GroundingBadge } from "./GroundingBadge";
import { SourceCard } from "./SourceCard";

interface Props {
  message: ChatMessage;
  isLast: boolean;
  busy: boolean;
  onRegenerate: () => void;
  onRetry: () => void;
  onOpenSource: (citation: Citation) => void;
}

export function MessageBubble({ message, isLast, busy, onRegenerate, onRetry, onOpenSource }: Props) {
  const [copied, setCopied] = useState(false);

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-sm text-primary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.error) {
    return (
      <div role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm">
        <p className="font-medium">The answer could not be generated.</p>
        <p className="mt-1 text-muted-foreground">{message.error}</p>
        {isLast && (
          <Button variant="outline" size="sm" className="mt-3" disabled={busy} onClick={onRetry}>
            <RotateCcw className="size-4" /> Try again
          </Button>
        )}
      </div>
    );
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Could not copy to the clipboard");
    }
  }

  return (
    <div className="max-w-full space-y-3 rounded-2xl rounded-bl-sm border border-border bg-card/60 p-4">
      <div className="relative">
        <AnswerMarkdown content={message.content} citations={message.citations} onOpenSource={onOpenSource} />
        {message.streaming && (
          <span className="inline-block h-4 w-1.5 ml-1 translate-y-0.5 animate-pulse bg-primary align-middle" />
        )}
      </div>

      {!message.streaming && (
        <GroundingBadge
          grounded={message.grounded}
          confidence={message.confidence}
          unsupportedClaims={message.unsupportedClaims}
          citationCoverage={message.citationCoverage}
          invalidCitations={message.invalidCitations}
        />
      )}

      {message.citations.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Sources</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {message.citations.map((citation, i) => (
              <SourceCard key={citation.chunk_id} citation={citation} number={i + 1} onOpen={onOpenSource} />
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={copy}>
            {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            {copied ? "Copied" : "Copy"}
          </Button>
          {isLast && (
            <Button variant="ghost" size="sm" disabled={busy} onClick={onRegenerate}>
              <RefreshCw className="size-4" /> Regenerate
            </Button>
          )}
        </div>
        {message.totalMs !== null && (
          <span className="text-xs text-muted-foreground">
            {formatMs(message.totalMs)} total
            {message.retrievalMs !== null && ` · retrieval ${formatMs(message.retrievalMs)}`}
            {message.generationMs !== null && message.generationMs > 0 && ` · generation ${formatMs(message.generationMs)}`}
          </span>
        )}
      </div>
    </div>
  );
}
