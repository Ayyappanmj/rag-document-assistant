import { LoaderCircle, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { EvaluationStatus } from "@/types";

interface Props {
  status: EvaluationStatus;
  running: boolean;
  onStart: () => void;
}

export function RunPanel({ status, running, onStart }: Props) {
  return (
    <div className="flex flex-col items-end gap-2">
      <Button onClick={onStart} disabled={running}>
        {running ? <LoaderCircle className="size-4 animate-spin" /> : <Play className="size-4" />}
        {running ? "Running..." : "Run sample evaluation"}
      </Button>
      {running && (
        <div className="w-56">
          <Progress value={status.total > 0 ? (status.completed / status.total) * 100 : 0} />
          <p className="mt-1 text-right text-xs text-muted-foreground">
            {status.completed} of {status.total} questions
          </p>
        </div>
      )}
      {status.state === "failed" && status.error && <p className="max-w-xs text-right text-xs text-red-400">{status.error}</p>}
    </div>
  );
}
