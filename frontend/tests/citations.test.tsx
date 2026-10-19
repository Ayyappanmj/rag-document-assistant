import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { linkifyCitations, CITE_PREFIX } from "@/lib/citations";
import { SourceDialog } from "@/components/chat/SourceDialog";
import { AnswerMarkdown } from "@/components/chat/AnswerMarkdown";
import type { Citation } from "@/types";

const mockCitations: Citation[] = [
  {
    chunk_id: "chunk-1",
    document: "annual_report.pdf",
    page: 12,
    score: 0.89,
    retrieval_type: "hybrid",
    text: "Net profit grew by 15% year-over-year.",
  },
  {
    chunk_id: "chunk-2",
    document: "guide.pdf",
    page: 3,
    score: 0.74,
    retrieval_type: "dense",
    text: "To reset your password, visit account settings.",
  },
];

describe("linkifyCitations", () => {
  it("converts matching source markers to markdown links", () => {
    const text = "Company grew revenue significantly [Source: annual_report.pdf, Page 12].";
    const linked = linkifyCitations(text, mockCitations);
    expect(linked).toBe("Company grew revenue significantly [annual_report.pdf · p.12](#cite-0).");
  });

  it("leaves unmatched citation markers untouched", () => {
    const text = "Unmatched citation [Source: unknown.pdf, Page 99].";
    const linked = linkifyCitations(text, mockCitations);
    expect(linked).toBe(text);
  });
});

describe("SourceDialog", () => {
  it("renders citation details when open", () => {
    const onClose = vi.fn();
    render(<SourceDialog citation={mockCitations[0]} onClose={onClose} />);

    expect(screen.getByText("annual_report.pdf")).toBeInTheDocument();
    expect(screen.getByText(/Page 12/)).toBeInTheDocument();
    expect(screen.getByText("Similarity 0.89")).toBeInTheDocument();
    expect(screen.getByText("Retrieval: hybrid")).toBeInTheDocument();
    expect(screen.getByText("Net profit grew by 15% year-over-year.")).toBeInTheDocument();
  });

  it("does not render modal contents when citation is null", () => {
    const onClose = vi.fn();
    render(<SourceDialog citation={null} onClose={onClose} />);

    expect(screen.queryByText("Net profit grew by 15% year-over-year.")).not.toBeInTheDocument();
  });
});

describe("AnswerMarkdown", () => {
  it("renders text and converts citation links into clickable buttons", () => {
    const onOpenSource = vi.fn();
    const content = "Revenue grew [Source: annual_report.pdf, Page 12].";

    render(<AnswerMarkdown content={content} citations={mockCitations} onOpenSource={onOpenSource} />);

    const chip = screen.getByRole("button", { name: "annual_report.pdf · p.12" });
    expect(chip).toBeInTheDocument();

    fireEvent.click(chip);
    expect(onOpenSource).toHaveBeenCalledWith(mockCitations[0]);
  });
});
