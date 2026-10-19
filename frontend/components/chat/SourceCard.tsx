import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Citation } from "@/types";

const capitalise = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

interface Props {
  citation: Citation;
  number: number;
  onOpen: (citation: Citation) => void;
}

export function SourceCard({ citation, number, onOpen }: Props) {
  return (
    <button
      type="button"
      onClick={() => onOpen(citation)}
      className="w-full rounded-lg border border-border bg-card/60 p-3 text-left transition-colors hover:border-primary/50 hover:bg-muted/40"
    >
      <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-semibold tracking-wide">SOURCE {number}</span>
      </div>
      <div className="flex items-center gap-1.5 text-sm font-medium">
        <FileText className="size-3.5 shrink-0 text-primary" />
        <span className="truncate" title={citation.document}>{citation.document}</span>
      </div>
      <p className="text-xs text-muted-foreground">Page {citation.page}</p>
      <p className="mt-2 line-clamp-3 text-xs italic text-muted-foreground">&ldquo;{citation.text}&rdquo;</p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        <Badge variant="secondary">Similarity {citation.score.toFixed(2)}</Badge>
        <Badge variant="outline">Retrieval: {capitalise(citation.retrieval_type)}</Badge>
      </div>
    </button>
  );
}
