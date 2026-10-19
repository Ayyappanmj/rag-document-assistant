export interface DonutSegment {
  label: string;
  value: number;
  className: string; // tailwind stroke class, e.g. "stroke-emerald-500"
}

const RADIUS = 40;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Small SVG donut chart (no chart library needed). */
export function DonutChart({ segments, centerLabel }: { segments: DonutSegment[]; centerLabel: string }) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  let offset = 0;
  return (
    <div className="flex items-center gap-6">
      <svg viewBox="0 0 100 100" className="size-28 -rotate-90" role="img" aria-label={centerLabel}>
        <circle cx="50" cy="50" r={RADIUS} fill="none" strokeWidth="12" className="stroke-muted" />
        {total > 0 &&
          segments.map((s) => {
            const length = (s.value / total) * CIRCUMFERENCE;
            const circle = (
              <circle
                key={s.label}
                cx="50"
                cy="50"
                r={RADIUS}
                fill="none"
                strokeWidth="12"
                strokeDasharray={`${length} ${CIRCUMFERENCE - length}`}
                strokeDashoffset={-offset}
                className={s.className}
              />
            );
            offset += length;
            return circle;
          })}
      </svg>
      <ul className="space-y-1 text-sm">
        {segments.map((s) => (
          <li key={s.label} className="flex items-center gap-2">
            <span className={`inline-block size-2.5 rounded-full ${s.className.replace("stroke-", "bg-")}`} />
            {s.label}: <span className="font-medium">{s.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
