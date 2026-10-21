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
  const [viewAll, setViewAll] = useState(false);
  const [chunks, setChunks] = useState<ChunkRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const docId = document?.id;

  useEffect(() => {
    setPage(1);
    setViewAll(false);
  }, [docId]);

  useEffect(() => {
    if (!docId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const targetPage = viewAll ? undefined : page;
    getChunks(docId, targetPage, viewAll ? 200 : 50)
      .then((data) => !cancelled && setChunks(data))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Could not load chunks"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [docId, page, viewAll]);

  const totalPages = document?.page_count ?? 1;

  return (
    <Dialog open={document !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="truncate">{document?.name}</DialogTitle>
          <DialogDescription>
            {viewAll
              ? `Showing all chunks (${chunks.length}) across ${totalPages} page${totalPages === 1 ? "" : "s"}.`
              : `Extracted text chunks for page ${page} of ${totalPages}.`}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between gap-2 border-b border-border pb-3">
          {!viewAll ? (
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft className="size-4" /> Previous
              </Button>
              <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Next <ChevronRight className="size-4" />
              </Button>
            </div>
          ) : (
            <span className="text-sm font-medium">All Document Chunks</span>
          )}
          <Button variant="ghost" size="sm" onClick={() => setViewAll((v) => !v)}>
            {viewAll ? "View by Page" : "View All"}
          </Button>
        </div>

        {loading && <Skeleton className="h-32 w-full" />}
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!loading && !error && chunks.length === 0 && (
          <div className="py-6 text-center text-sm text-muted-foreground">
            <p>No text chunks found {viewAll ? "in this document" : `on page ${page}`}.</p>
            {!viewAll && (
              <Button variant="link" size="sm" className="mt-2" onClick={() => setViewAll(true)}>
                View all document chunks
              </Button>
            )}
          </div>
        )}
        {!loading &&
          chunks.map((chunk) => (
            <div key={chunk.id} className="rounded-lg border border-border p-3">
              <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex items-center gap-2">
                  <span>Chunk {chunk.chunk_index}</span>
                  {chunk.section && <Badge variant="secondary">{chunk.section}</Badge>}
                </div>
                <span>Page {chunk.page_number}</span>
              </div>
              <p className="whitespace-pre-wrap text-sm">{chunk.text}</p>
            </div>
          ))}
      </DialogContent>
    </Dialog>
  );
}
