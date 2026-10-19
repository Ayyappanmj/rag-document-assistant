import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MessageBubble } from "@/components/chat/MessageBubble";
import type { ChatMessage } from "@/types";

describe("MessageBubble", () => {
  it("renders a user message correctly", () => {
    const userMsg: ChatMessage = {
      id: "m-1",
      role: "user",
      content: "What is our Q3 revenue?",
      citations: [],
      grounded: true,
      confidence: 1.0,
      unsupportedClaims: [],
      citationCoverage: 1.0,
      invalidCitations: [],
      retrievalMs: null,
      generationMs: null,
      totalMs: null,
    };

    render(
      <MessageBubble
        message={userMsg}
        isLast={true}
        busy={false}
        onRegenerate={vi.fn()}
        onRetry={vi.fn()}
        onOpenSource={vi.fn()}
      />
    );

    expect(screen.getByText("What is our Q3 revenue?")).toBeInTheDocument();
  });

  it("renders assistant message with answer, sources and grounding evaluation", () => {
    const assistantMsg: ChatMessage = {
      id: "m-2",
      role: "assistant",
      content: "Q3 revenue was 10 million dollars.",
      citations: [
        {
          chunk_id: "c-1",
          document: "q3_report.pdf",
          page: 5,
          score: 0.95,
          retrieval_type: "dense",
          text: "Total revenue reached $10M in Q3.",
        },
      ],
      grounded: true,
      confidence: 0.95,
      unsupportedClaims: [],
      citationCoverage: 1.0,
      invalidCitations: [],
      retrievalMs: 120,
      generationMs: 450,
      totalMs: 570,
    };

    render(
      <MessageBubble
        message={assistantMsg}
        isLast={true}
        busy={false}
        onRegenerate={vi.fn()}
        onRetry={vi.fn()}
        onOpenSource={vi.fn()}
      />
    );

    expect(screen.getByText("Q3 revenue was 10 million dollars.")).toBeInTheDocument();
    expect(screen.getByText(/Grounded/i)).toBeInTheDocument();
    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByText("q3_report.pdf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Regenerate/i })).toBeInTheDocument();
  });

  it("renders streaming indicator while streaming and hides grounding badge", () => {
    const streamingMsg: ChatMessage = {
      id: "m-3",
      role: "assistant",
      content: "Generating answer partially...",
      streaming: true,
      citations: [],
      grounded: false,
      confidence: 0,
      unsupportedClaims: [],
      citationCoverage: 0,
      invalidCitations: [],
      retrievalMs: 100,
      generationMs: 0,
      totalMs: null,
    };

    const { container } = render(
      <MessageBubble
        message={streamingMsg}
        isLast={true}
        busy={true}
        onRegenerate={vi.fn()}
        onRetry={vi.fn()}
        onOpenSource={vi.fn()}
      />
    );

    expect(screen.getByText("Generating answer partially...")).toBeInTheDocument();
    // Grounding badge shouldn't show while streaming
    expect(screen.queryByText("Grounded")).not.toBeInTheDocument();
    // Pulse cursor indicator is rendered
    const pulseCursor = container.querySelector(".animate-pulse");
    expect(pulseCursor).toBeInTheDocument();
  });

  it("renders error state with retry button", () => {
    const onRetry = vi.fn();
    const errorMsg: ChatMessage = {
      id: "m-4",
      role: "assistant",
      content: "",
      error: "Ollama connection timeout",
      citations: [],
      grounded: false,
      confidence: 0,
      unsupportedClaims: [],
      citationCoverage: 0,
      invalidCitations: [],
      retrievalMs: null,
      generationMs: null,
      totalMs: null,
    };

    render(
      <MessageBubble
        message={errorMsg}
        isLast={true}
        busy={false}
        onRegenerate={vi.fn()}
        onRetry={onRetry}
        onOpenSource={vi.fn()}
      />
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("The answer could not be generated.")).toBeInTheDocument();
    expect(screen.getByText("Ollama connection timeout")).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: /Try again/i });
    fireEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
