import { Clock, FileText, Layers, MessagesSquare, ShieldCheck, BookOpen } from "lucide-react";

import { formatMs, formatNumber } from "@/lib/format";
import type { DashboardStats } from "@/types";

import { StatCard } from "./StatCard";

export function StatsGrid({ stats }: { stats: DashboardStats }) {
  const answered = stats.grounded_answers + stats.ungrounded_answers;
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <StatCard label="Total documents" value={formatNumber(stats.total_documents)} icon={FileText} />
      <StatCard label="Total pages" value={formatNumber(stats.total_pages)} icon={BookOpen} />
      <StatCard label="Total chunks" value={formatNumber(stats.total_chunks)} icon={Layers} />
      <StatCard label="Questions asked" value={formatNumber(stats.questions_asked)} icon={MessagesSquare} />
      <StatCard label="Avg response time" value={formatMs(stats.avg_response_time_ms)} icon={Clock} />
      <StatCard
        label="Grounded answers"
        value={formatNumber(stats.grounded_answers)}
        hint={answered > 0 ? `${stats.ungrounded_answers} flagged as potentially unsupported` : "No answers checked yet"}
        icon={ShieldCheck}
      />
    </div>
  );
}
