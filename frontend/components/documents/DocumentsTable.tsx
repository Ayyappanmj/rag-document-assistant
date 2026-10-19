import { Eye, MessageSquare, Trash2 } from "lucide-react";
import Link from "next/link";

import { Button, buttonVariants } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatBytes, formatDate, formatNumber } from "@/lib/format";
import type { DocumentRecord } from "@/types";

import { StatusBadge } from "./StatusBadge";

interface Props {
  documents: DocumentRecord[];
  onView: (doc: DocumentRecord) => void;
  onDelete: (doc: DocumentRecord) => void;
}

export function DocumentsTable({ documents, onView, onDelete }: Props) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead className="text-right">Pages</TableHead>
            <TableHead className="text-right">Chunks</TableHead>
            <TableHead>Uploaded</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => {
            const ready = doc.status === "ready";
            return (
              <TableRow key={doc.id}>
                <TableCell>
                  <div className="max-w-[260px] truncate font-medium" title={doc.name}>{doc.name}</div>
                  <div className="text-xs text-muted-foreground">{formatBytes(doc.size_bytes)}</div>
                  {doc.status === "failed" && doc.error_message && (
                    <div className="mt-1 text-xs text-red-400">{doc.error_message}</div>
                  )}
                </TableCell>
                <TableCell className="text-right">{ready ? formatNumber(doc.page_count) : "-"}</TableCell>
                <TableCell className="text-right">{ready ? formatNumber(doc.chunk_count) : "-"}</TableCell>
                <TableCell className="whitespace-nowrap text-muted-foreground">{formatDate(doc.created_at)}</TableCell>
                <TableCell>
                  <StatusBadge status={doc.status} title={doc.error_message ?? undefined} />
                </TableCell>
                <TableCell>
                  <div className="flex justify-end gap-1">
                    <Button variant="ghost" size="icon" aria-label={`View ${doc.name}`} disabled={!ready} onClick={() => onView(doc)}>
                      <Eye className="size-4" />
                    </Button>
                    {ready ? (
                      <Link
                        href={`/chat?doc=${doc.id}`}
                        aria-label={`Chat with ${doc.name}`}
                        className={buttonVariants({ variant: "ghost", size: "icon" })}
                      >
                        <MessageSquare className="size-4" />
                      </Link>
                    ) : (
                      <Button variant="ghost" size="icon" aria-label="Chat unavailable" disabled>
                        <MessageSquare className="size-4" />
                      </Button>
                    )}
                    <Button variant="ghost" size="icon" aria-label={`Delete ${doc.name}`} onClick={() => onDelete(doc)}>
                      <Trash2 className="size-4 text-red-400" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
