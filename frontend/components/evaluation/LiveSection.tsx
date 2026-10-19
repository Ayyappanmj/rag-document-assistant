import { Activity } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/EmptyState";
import { StatCard } from "@/components/dashboard/StatCard";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMs, formatNumber } from "@/lib/format";
import type { LiveMetrics } from "@/types";

import { DonutChart } from "./DonutChart";
import { MetricBars } from "./MetricBars";

export function LiveSection({ live }: { live: LiveMetrics }) {
  if (live.evaluated_answers === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="No live data yet"
        description="Every answer you generate on the Chat page is scored automatically and shows up here."
      >
        <Link href="/chat" className={buttonVariants()}>Go to Chat</Link>
      </EmptyState>
    );
  }
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Questions asked" value={formatNumber(live.questions_asked)} icon={Activity} />
        <StatCard label="Evaluated answers" value={formatNumber(live.evaluated_answers)} icon={Activity} />
        <StatCard label="Avg response time" value={formatMs(live.avg_response_time_ms)} icon={Activity} />
        <StatCard
          label="Avg retrieval score"
          value={live.avg_retrieval_score === null ? "-" : live.avg_retrieval_score.toFixed(2)}
          hint="Cosine similarity of cited passages"
          icon={Activity}
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="text-base">Answer quality (average)</CardTitle></CardHeader>
          <CardContent>
            <MetricBars
              items={[
                { label: "Faithfulness / groundedness", value: live.faithfulness },
                { label: "Answer relevance", value: live.answer_relevance },
                { label: "Context relevance", value: live.context_relevance },
                { label: "Citation coverage", value: live.citation_coverage },
              ]}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Grounding check</CardTitle></CardHeader>
          <CardContent>
            <DonutChart
              centerLabel="Grounded versus potentially hallucinated answers"
              segments={[
                { label: "Grounded", value: live.grounded_answers, className: "stroke-emerald-500" },
                { label: "Potentially hallucinated", value: live.potentially_hallucinated_answers, className: "stroke-amber-500" },
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
