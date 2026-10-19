import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { StoreBenchmark, StoreBenchmarkError, VectorBenchmark } from "@/types";

type Entry = StoreBenchmark | StoreBenchmarkError;
const isOk = (s: Entry): s is StoreBenchmark => !("error" in s);

interface Row {
  label: string;
  value: (s: StoreBenchmark) => number;
  format: (n: number) => string;
  better: "lower" | "higher";
  hint?: string;
}

const fixed = (digits: number, unit = "") => (n: number) => `${n.toFixed(digits)}${unit}`;

const ROWS: Row[] = [
  { label: "Build time", value: (s) => s.build_seconds, format: fixed(2, " s"), better: "lower", hint: "Adding every vector, including saving to disk" },
  { label: "Disk size", value: (s) => s.disk_mb, format: fixed(1, " MB"), better: "lower" },
  { label: "Reopen time", value: (s) => s.open_seconds, format: fixed(2, " s"), better: "lower", hint: "Loading the saved index after a restart" },
  { label: "Query, median", value: (s) => s.query_ms.p50, format: fixed(2, " ms"), better: "lower" },
  { label: "Query, 95th percentile", value: (s) => s.query_ms.p95, format: fixed(2, " ms"), better: "lower" },
  { label: "Filtered query, median", value: (s) => s.filtered_query_ms.p50, format: fixed(2, " ms"), better: "lower", hint: "Search limited to a few documents" },
  { label: "Recall at k vs exact", value: (s) => s.recall_at_k, format: (n) => formatPercent(n), better: "higher", hint: "How many of the true nearest neighbours were returned" },
  { label: "Filtered recall at k", value: (s) => s.filtered_recall_at_k, format: (n) => formatPercent(n), better: "higher" },
  { label: "Delete one document", value: (s) => s.delete_document_ms, format: fixed(1, " ms"), better: "lower" },
];

const title = (name: string) => (name === "faiss" ? "FAISS" : name === "chroma" ? "Chroma" : name);

/** Side-by-side table. The better value in each row is highlighted, only when the two differ. */
export function VectorStoreComparison({ data }: { data: VectorBenchmark }) {
  const entries = Object.entries(data.stores);
  const ok = entries.filter((e): e is [string, StoreBenchmark] => isOk(e[1]));
  const failed = entries.filter((e): e is [string, StoreBenchmarkError] => !isOk(e[1]));
  const p = data.parameters;

  function best(row: Row): number | null {
    if (ok.length < 2) return null;
    const values = ok.map(([, s]) => row.value(s));
    if (new Set(values).size === 1) return null;
    return row.better === "lower" ? Math.min(...values) : Math.max(...values);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline">{data.label}</Badge>
        <span className="text-xs text-muted-foreground">
          Run {formatDate(data.generated_at)} · {String(p.vectors)} vectors · {String(p.dimension)} dimensions ·{" "}
          {String(p.queries)} queries · top-{String(p.top_k)}
        </span>
      </div>
      <p className="text-sm text-muted-foreground">{data.note}</p>

      {failed.map(([name, entry]) => (
        <p key={name} className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-400">
          {title(name)} was skipped: {entry.error}. Install it with pip install -r backend/requirements-chroma.txt and run
          the comparison again.
        </p>
      ))}

      {ok.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base">FAISS and Chroma, same vectors, same machine</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Measure</TableHead>
                  {ok.map(([name]) => (
                    <TableHead key={name} className="text-right">{title(name)}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="text-muted-foreground">Index type</TableCell>
                  {ok.map(([name, s]) => (
                    <TableCell key={name} className="text-right text-xs">{s.index_type}</TableCell>
                  ))}
                </TableRow>
                {ROWS.map((row) => {
                  const winner = best(row);
                  return (
                    <TableRow key={row.label}>
                      <TableCell title={row.hint}>
                        {row.label}
                        <span className="ml-1 text-[11px] text-muted-foreground">({row.better} is better)</span>
                      </TableCell>
                      {ok.map(([name, s]) => {
                        const value = row.value(s);
                        return (
                          <TableCell
                            key={name}
                            className={cn("text-right font-medium", winner !== null && value === winner && "text-emerald-400")}
                          >
                            {row.format(value)}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {data.real_documents && (
        <Card>
          <CardHeader><CardTitle className="text-base">On your indexed documents</CardTitle></CardHeader>
          <CardContent className="space-y-3 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Store</TableHead>
                  <TableHead className="text-right">Retrieval precision</TableHead>
                  <TableHead className="text-right">Retrieval recall</TableHead>
                  <TableHead className="text-right">Avg query</TableHead>
                  <TableHead className="text-right">Vectors</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(data.real_documents.stores).map(([name, s]) => (
                  <TableRow key={name}>
                    <TableCell className="font-medium">{title(name)}</TableCell>
                    <TableCell className="text-right">{formatPercent(s.retrieval_precision)}</TableCell>
                    <TableCell className="text-right">{formatPercent(s.retrieval_recall)}</TableCell>
                    <TableCell className="text-right">{s.avg_query_ms === null ? "-" : `${s.avg_query_ms.toFixed(2)} ms`}</TableCell>
                    <TableCell className="text-right">{s.vectors}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="text-xs text-muted-foreground">
              {data.real_documents.questions} evaluation questions, top-{data.real_documents.top_k}.
              {data.real_documents.top_k_overlap_jaccard !== null &&
                ` Both stores returned the same passages for ${formatPercent(data.real_documents.top_k_overlap_jaccard)} of the results (Jaccard overlap).`}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
