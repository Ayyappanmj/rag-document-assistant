import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatMs, formatPercent } from "@/lib/format";
import type { SampleRun } from "@/types";

import { DonutChart } from "./DonutChart";
import { MetricBars } from "./MetricBars";

export function SampleSection({ run }: { run: SampleRun }) {
  const s = run.summary;
  const config = run.config;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">{run.label}</Badge>
        <span className="text-xs text-muted-foreground">
          Last run {formatDate(run.generated_at)} · {s.total_questions} questions · {String(config.llm_model)} ·
          top-K {String(config.top_k)}
        </span>
      </div>
      <p className="text-sm text-muted-foreground">{run.note}</p>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="text-base">Quality and retrieval</CardTitle></CardHeader>
          <CardContent>
            <MetricBars
              items={[
                { label: "Faithfulness / groundedness", value: s.faithfulness },
                { label: "Answer relevance", value: s.answer_relevance },
                { label: "Context relevance", value: s.context_relevance },
                { label: "Citation coverage", value: s.citation_coverage },
                { label: "Retrieval precision", value: s.retrieval_precision, hint: "Share of retrieved chunks from an expected document" },
                { label: "Retrieval recall", value: s.retrieval_recall, hint: "Share of expected documents that were retrieved" },
                { label: "Answer match", value: s.answer_match, hint: "Expected key words and numbers found in the answer" },
                { label: "Correct refusals", value: s.refusal_accuracy, hint: "Unanswerable questions that were declined" },
              ]}
            />
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Grounding check</CardTitle></CardHeader>
            <CardContent>
              <DonutChart
                centerLabel="Grounded versus potentially hallucinated answers"
                segments={[
                  { label: "Grounded", value: s.grounded_answers, className: "stroke-emerald-500" },
                  { label: "Potentially hallucinated", value: s.potentially_hallucinated_answers, className: "stroke-amber-500" },
                ]}
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="space-y-1 pt-6 text-sm">
              <p><span className="text-muted-foreground">Average latency:</span> {formatMs(s.avg_latency_ms)}</p>
              <p><span className="text-muted-foreground">Average retrieval score:</span> {s.avg_retrieval_score === null ? "-" : s.avg_retrieval_score.toFixed(2)}</p>
              <p><span className="text-muted-foreground">Wrongly declined (answerable):</span> {formatPercent(s.false_refusal_rate)}</p>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">By question type</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Questions</TableHead>
                <TableHead className="text-right">Answer match</TableHead>
                <TableHead className="text-right">Faithfulness</TableHead>
                <TableHead className="text-right">Avg latency</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(s.by_type).map(([type, t]) => (
                <TableRow key={type}>
                  <TableCell className="font-medium">{type.replace("_", "-")}</TableCell>
                  <TableCell className="text-right">{t.count}</TableCell>
                  <TableCell className="text-right">{formatPercent(t.answer_match)}</TableCell>
                  <TableCell className="text-right">{formatPercent(t.faithfulness)}</TableCell>
                  <TableCell className="text-right">{formatMs(t.avg_latency_ms)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
