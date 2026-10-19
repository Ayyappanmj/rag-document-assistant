import Link from "next/link";

import { StatusBadge } from "@/components/documents/StatusBadge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import type { DocumentRecord } from "@/types";

export function RecentDocuments({ documents }: { documents: DocumentRecord[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Recent documents</CardTitle>
        <Link href="/documents" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          View all
        </Link>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead className="text-right">Pages</TableHead>
              <TableHead>Uploaded</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.map((doc) => (
              <TableRow key={doc.id}>
                <TableCell className="max-w-[200px] truncate font-medium" title={doc.name}>{doc.name}</TableCell>
                <TableCell className="text-right">{doc.status === "ready" ? doc.page_count : "-"}</TableCell>
                <TableCell className="whitespace-nowrap text-muted-foreground">{formatDate(doc.created_at)}</TableCell>
                <TableCell><StatusBadge status={doc.status} /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
