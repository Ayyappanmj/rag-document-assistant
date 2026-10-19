"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { getChunks } from "@/lib/api";
import type { ChunkRecord, DocumentRecord } from "@/types";

interface Props {
  document: DocumentRecord | null;
  onClose: () => void;
}

/** Shows the text chunks the system extracted from one page of a document. */
export function DocumentViewer({ document, onClose }: Props) {
  const [page, setPage] = useState(1);
  const [chunks, setChunks] = useState<ChunkRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const docId = document?.id;

  useEffect(() => {
    setPage(1);
  }, [docId]);

  useEffect(() => {
    if (!docId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getChunks(docId, page)
      .then((data) => !cancelled && setChunks(data))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Could not load chunks"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [docId, page]);

  const totalPages = document?.page_count ?? 1;

  return (
    <Dialog open={document !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="truncate">{document?.name}</DialogTitle>
          <DialogDescription>
            Extracted text chunks for page {page} of {totalPages}.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            <ChevronLeft className="size-4" /> Previous
          </Button>
          <span className="text-sm text-muted-foreground">Page {page}</span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next <ChevronRight className="size-4" />
          </Button>
        </div>

        {loading && <Skeleton className="h-32 w-full" />}
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!loading && !error && chunks.length === 0 && (
          <p className="text-sm text-muted-foreground">No text was extracted from this page.</p>
        )}
        {!loading &&
          chunks.map((chunk) => (
            <div key={chunk.id} className="rounded-lg border border-border p-3">
              <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                <span>Chunk {chunk.chunk_index}</span>
                {chunk.section && <Badge variant="secondary">{chunk.section}</Badge>}
              </div>
              <p className="whitespace-pre-wrap text-sm">{chunk.text}</p>
            </div>
          ))}
      </DialogContent>
    </Dialog>
  );
}
