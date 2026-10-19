import { Progress } from "@/components/ui/progress";
import { formatPercent } from "@/lib/format";

export interface MetricItem {
  label: string;
  value: number | null;
  hint?: string;
}

/** Horizontal bar chart for 0..1 scores. */
export function MetricBars({ items }: { items: MetricItem[] }) {
  return (
    <div className="space-y-4">
      {items.map(({ label, value, hint }) => (
        <div key={label}>
          <div className="mb-1 flex items-baseline justify-between text-sm">
            <span title={hint}>{label}</span>
            <span className="font-medium">{formatPercent(value)}</span>
          </div>
          <Progress value={value === null ? 0 : value * 100} />
        </div>
      ))}
    </div>
  );
}
