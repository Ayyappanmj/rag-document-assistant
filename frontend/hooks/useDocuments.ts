"use client";

import { useCallback, useEffect, useState } from "react";

import { listDocuments } from "@/lib/api";
import type { DocumentRecord, DocumentStatus } from "@/types";

const IN_PROGRESS: ReadonlySet<DocumentStatus> = new Set(["uploading", "processing", "embedding", "indexed"]);

/** Loads documents and keeps polling every 2s while any of them is still being processed. */
export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      setDocuments(await listDocuments());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const hasActive = documents.some((d) => IN_PROGRESS.has(d.status));
  useEffect(() => {
    if (!hasActive) return;
    const timer = setInterval(() => void refresh(true), 2000);
    return () => clearInterval(timer);
  }, [hasActive, refresh]);

  return { documents, loading, error, refresh };
}
