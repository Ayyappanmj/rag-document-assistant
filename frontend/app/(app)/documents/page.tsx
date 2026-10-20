"use client";

import { FileText } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { PageHeader } from "@/components/common/PageHeader";
import { DocumentViewer } from "@/components/documents/DocumentViewer";
import { DocumentsTable } from "@/components/documents/DocumentsTable";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/useApi";
import { useDocuments } from "@/hooks/useDocuments";
import { deleteDocument, getConfig, retryDocument } from "@/lib/api";
import type { DocumentRecord } from "@/types";

const DEFAULT_MAX_MB = 25;

export default function DocumentsPage() {
  const { documents, loading, error, refresh } = useDocuments();
  const { data: config } = useApi(getConfig);
  const [viewing, setViewing] = useState<DocumentRecord | null>(null);

  async function handleDelete(doc: DocumentRecord) {
    if (!window.confirm(`Delete "${doc.name}"? This also removes its search index entries.`)) return;
    try {
      await deleteDocument(doc.id);
      toast.success(`${doc.name} deleted`);
      await refresh(true);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not delete the document");
    }
  }

  async function handleRetry(doc: DocumentRecord) {
    try {
      await retryDocument(doc.id);
      toast.success(`Retrying indexing for "${doc.name}"...`);
      await refresh(true);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not retry indexing");
    }
  }

  return (
    <>
      <PageHeader
        title="Documents"
        description="Upload PDFs and manage what the assistant can answer questions about."
      />
      <div className="space-y-6">
        <UploadDropzone maxMb={config?.max_upload_mb ?? DEFAULT_MAX_MB} onUploaded={() => void refresh(true)} />

        {loading && <Skeleton className="h-40 w-full rounded-xl" />}
        {error && <ErrorState message={error} onRetry={() => void refresh()} />}
        {!loading && !error && documents.length === 0 && (
          <EmptyState
            icon={FileText}
            title="No documents yet"
            description="Upload a PDF to start asking questions."
          />
        )}
        {documents.length > 0 && (
          <DocumentsTable
            documents={documents}
            onView={setViewing}
            onDelete={handleDelete}
            onRetry={handleRetry}
          />
        )}
      </div>
      <DocumentViewer document={viewing} onClose={() => setViewing(null)} />
    </>
  );
}
