"use client";

import ReactMarkdown from "react-markdown";

import { CITE_PREFIX, linkifyCitations } from "@/lib/citations";
import type { Citation } from "@/types";

interface Props {
  content: string;
  citations: Citation[];
  onOpenSource: (citation: Citation) => void;
}

/** Renders the answer as markdown; inline [Source: file, Page N] markers become clickable chips. */
export function AnswerMarkdown({ content, citations, onOpenSource }: Props) {
  return (
    <div className="space-y-3 text-sm leading-relaxed">
      <ReactMarkdown
        components={{
          p: ({ children }) => <p>{children}</p>,
          ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal space-y-1 pl-5">{children}</ol>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          code: ({ children }) => <code className="rounded bg-muted px-1 py-0.5 text-xs">{children}</code>,
          a: ({ href, children }) => {
            if (href?.startsWith(CITE_PREFIX)) {
              const citation = citations[Number(href.slice(CITE_PREFIX.length))];
              if (citation) {
                return (
                  <button
                    type="button"
                    onClick={() => onOpenSource(citation)}
                    className="mx-0.5 inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary hover:bg-primary/20"
                  >
                    {children}
                  </button>
                );
              }
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="underline">
                {children}
              </a>
            );
          },
        }}
      >
        {linkifyCitations(content, citations)}
      </ReactMarkdown>
    </div>
  );
}
