import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { formatPercent } from "@/lib/format";
import type { EvaluationSummary } from "@/types";

export function EvaluationSummaryCard({ evaluation }: { evaluation: EvaluationSummary }) {
  const rows = [
    { label: "Faithfulness", value: evaluation.faithfulness },
    { label: "Answer relevance", value: evaluation.answer_relevance },
    { label: "Context relevance", value: evaluation.context_relevance },
    { label: "Citation coverage", value: evaluation.citation_coverage },
  ];
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Evaluation summary</CardTitle>
        <Link href="/evaluation" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          Details
        </Link>
      </CardHeader>
      <CardContent className="space-y-4">
        {evaluation.evaluated_answers === 0 ? (
          <p className="text-sm text-muted-foreground">
            No evaluated answers yet. Scores appear here after you ask questions about your documents.
          </p>
        ) : (
          <>
            {rows.map(({ label, value }) => (
              <div key={label}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{label}</span>
                  <span className="font-medium">{formatPercent(value)}</span>
                </div>
                <Progress value={value === null ? 0 : value * 100} />
              </div>
            ))}
            <p className="text-xs text-muted-foreground">
              Averages over {evaluation.evaluated_answers} answered question
              {evaluation.evaluated_answers === 1 ? "" : "s"}. Heuristic scores, not a benchmark.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
