import { Badge } from "@/components/ui/badge";
import { formatMs, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { EvaluationRow } from "@/types";

function Outcome({ row }: { row: EvaluationRow }) {
  if (row.refused) {
    return row.answerable ? (
      <Badge variant="outline" className="border-amber-500/30 text-amber-400">Declined (should answer)</Badge>
    ) : (
      <Badge variant="outline" className="border-emerald-500/30 text-emerald-400">Correctly declined</Badge>
    );
  }
  if (row.grounded === true) {
    return <Badge variant="outline" className="border-emerald-500/30 text-emerald-400">Grounded</Badge>;
  }
  if (row.grounded === false) {
    return <Badge variant="outline" className="border-amber-500/30 text-amber-400">Flagged</Badge>;
  }
  return <Badge variant="outline">Unchecked</Badge>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border px-2 py-1.5">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}

/** One expandable block per question: expected vs generated answer, retrieved context and scores. */
export function ResultsList({ rows }: { rows: EvaluationRow[] }) {
  return (
    <div className="divide-y divide-border rounded-xl border border-border">
      {rows.map((row, i) => (
        <details key={row.id ?? i} className="group p-3">
          <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-sm">
            <span className="min-w-0 flex-1 font-medium">{row.question}</span>
            <Badge variant="secondary">{row.type.replace("_", "-")}</Badge>
            <Outcome row={row} />
            <span className="text-xs text-muted-foreground">{formatMs(row.latency_ms)}</span>
          </summary>

          <div className="mt-3 space-y-3 text-sm">
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Expected answer</p>
                <p className="rounded-lg border border-border p-3">{row.expected_answer}</p>
              </div>
              <div>
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Generated answer</p>
                <p className={cn("whitespace-pre-wrap rounded-lg border border-border p-3")}>{row.generated_answer}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
              <Metric label="Faithfulness" value={formatPercent(row.faithfulness)} />
              <Metric label="Relevance" value={formatPercent(row.answer_relevance)} />
              <Metric label="Context relevance" value={formatPercent(row.context_relevance)} />
              <Metric label="Citation coverage" value={formatPercent(row.citation_coverage)} />
              <Metric label="Precision" value={formatPercent(row.retrieval_precision)} />
              <Metric label="Recall" value={formatPercent(row.retrieval_recall)} />
            </div>

            <details>
              <summary className="cursor-pointer text-xs text-muted-foreground">
                Retrieved context ({row.retrieved_context.length} passages)
              </summary>
              <ul className="mt-2 space-y-2">
                {row.retrieved_context.map((c, j) => (
                  <li key={j} className="rounded-lg border border-border p-2 text-xs">
                    <span className="font-medium">{c.document}, page {c.page}</span>
                    <span className="text-muted-foreground"> · score {c.score.toFixed(2)}</span>
                    <p className="mt-1 text-muted-foreground">{c.text}</p>
                  </li>
                ))}
              </ul>
            </details>
          </div>
        </details>
      ))}
    </div>
  );
}
