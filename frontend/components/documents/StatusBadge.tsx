import { CircleCheck, LoaderCircle, CircleX } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { DocumentStatus } from "@/types";

const LABELS: Record<DocumentStatus, string> = {
  uploading: "Uploading",
  processing: "Processing",
  embedding: "Embedding",
  indexed: "Indexed",
  ready: "Ready",
  failed: "Failed",
};

export function StatusBadge({ status, title }: { status: DocumentStatus; title?: string }) {
  const tone =
    status === "ready"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
      : status === "failed"
        ? "border-red-500/30 bg-red-500/10 text-red-400"
        : "border-amber-500/30 bg-amber-500/10 text-amber-400";
  return (
    <Badge variant="outline" title={title} className={cn("gap-1", tone)}>
      {status === "ready" && <CircleCheck className="size-3" />}
      {status === "failed" && <CircleX className="size-3" />}
      {status !== "ready" && status !== "failed" && <LoaderCircle className="size-3 animate-spin" />}
      {LABELS[status]}
    </Badge>
  );
}
