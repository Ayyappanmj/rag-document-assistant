import { ShieldAlert, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";

type Props = Pick<ChatMessage, "grounded" | "confidence" | "unsupportedClaims" | "citationCoverage" | "invalidCitations">;

/** Hallucination-check result for one answer, plus notes about missing or invalid citations. */
export function GroundingBadge({ grounded, confidence, unsupportedClaims, citationCoverage, invalidCitations }: Props) {
  if (grounded === null && !unsupportedClaims?.length && !invalidCitations?.length && (citationCoverage === null || citationCoverage > 0)) {
    return null;
  }

  return (
    <div className="space-y-2">
      {grounded !== null && (
        <Badge
          variant="outline"
          className={cn(
            "gap-1",
            grounded
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : "border-amber-500/30 bg-amber-500/10 text-amber-400",
          )}
        >
          {grounded ? <ShieldCheck className="size-3" /> : <ShieldAlert className="size-3" />}
          {grounded ? "Grounded" : "Possibly unsupported"}
          {confidence !== null && ` · ${formatPercent(confidence)} confidence`}
        </Badge>
      )}

      {grounded === false && unsupportedClaims.length > 0 && (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer">Why was this flagged?</summary>
          <p className="mt-1">These statements were not clearly supported by the retrieved passages:</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {unsupportedClaims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </details>
      )}

      {citationCoverage === 0 && (
        <p className="text-xs text-muted-foreground">
          This answer has no inline citations. The sources shown are the passages that were retrieved.
        </p>
      )}
      {invalidCitations.length > 0 && (
        <p className="text-xs text-muted-foreground">
          The model referenced sources that were not provided. Those references were removed.
        </p>
      )}
    </div>
  );
}
