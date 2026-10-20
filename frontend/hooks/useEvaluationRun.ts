"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { getEvaluationStatus, startEvaluation } from "@/lib/api";
import type { EvaluationStatus } from "@/types";

const IDLE: EvaluationStatus = { state: "idle", completed: 0, total: 0, error: null, started_at: null };

/** Starts a sample evaluation and polls its progress. Calls onFinished when it completes. */
export function useEvaluationRun(onFinished: () => void) {
  const [status, setStatus] = useState<EvaluationStatus>(IDLE);

  // pick up a run that is already in progress (e.g. after a page refresh)
  useEffect(() => {
    getEvaluationStatus().then(setStatus).catch(() => undefined);
  }, []);

  const running = status.state === "running";
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(async () => {
      try {
        const next = await getEvaluationStatus();
        setStatus(next);
        if (next.state === "completed") {
          toast.success("Sample evaluation finished");
          onFinished();
        } else if (next.state === "failed") {
          toast.error(next.error ?? "The evaluation failed");
        }
      } catch {
        /* keep polling; a temporary network error should not stop the run display */
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [running, onFinished]);

  const start = useCallback(async (limit?: number) => {
    try {
      await startEvaluation(limit);
      const next = await getEvaluationStatus();
      setStatus(next);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not start the evaluation");
    }
  }, []);

  return { status, running, start };
}
