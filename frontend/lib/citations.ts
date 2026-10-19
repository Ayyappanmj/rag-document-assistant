import type { Citation } from "@/types";

// The backend rewrites citations to "[Source: file.pdf, Page 42]".
const CITE_RE = /\[Source:\s*([^\]]+?),\s*Page\s+(\d+)\]/g;

/**
 * Turns "[Source: file.pdf, Page 42]" into a markdown link "#cite-<index>" that points at the matching
 * citation card. Markers with no matching citation are left as plain text.
 * (Fragment links are used on purpose: react-markdown strips unknown URL schemes.)
 */
export function linkifyCitations(text: string, citations: Citation[]): string {
  return text.replace(CITE_RE, (full: string, name: string, page: string) => {
    const index = citations.findIndex((c) => c.document === name.trim() && c.page === Number(page));
    if (index === -1) return full;
    const label = `${name.trim()} · p.${page}`.replace(/[[\]]/g, "");
    return `[${label}](#cite-${index})`;
  });
}

export const CITE_PREFIX = "#cite-";
