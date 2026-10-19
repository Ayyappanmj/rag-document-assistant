"use client";

import { CircleCheck, CircleX } from "lucide-react";
import type { ReactNode } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { PageHeader } from "@/components/common/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/useApi";
import { API_URL, getConfig, getHealth } from "@/lib/api";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{children}</span>
    </div>
  );
}

export default function SettingsPage() {
  const health = useApi(getHealth);
  const config = useApi(getConfig);

  return (
    <>
      <PageHeader
        title="Settings"
        description="Read-only view of the backend configuration. Change values in backend/.env and restart the server."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Backend connection</CardTitle></CardHeader>
          <CardContent>
            <Row label="API URL">{API_URL}</Row>
            <Row label="Status">
              {health.loading ? (
                <Skeleton className="h-5 w-16" />
              ) : health.data ? (
                <Badge variant="outline" className="gap-1 border-emerald-500/30 text-emerald-400">
                  <CircleCheck className="size-3" /> Connected
                </Badge>
              ) : (
                <Badge variant="outline" className="gap-1 border-red-500/30 text-red-400">
                  <CircleX className="size-3" /> Unreachable
                </Badge>
              )}
            </Row>
            {health.data && <Row label="Environment">{health.data.environment}</Row>}
            {health.error && <p className="pt-2 text-xs text-red-400">{health.error}</p>}
          </CardContent>
        </Card>

        {config.error && <ErrorState message={config.error} onRetry={config.reload} />}
        {config.loading && <Skeleton className="h-64 rounded-xl" />}
        {config.data && (
          <>
            <Card>
              <CardHeader><CardTitle className="text-base">Models</CardTitle></CardHeader>
              <CardContent>
                <Row label="LLM provider">{config.data.llm_provider}</Row>
                <Row label="LLM model">{config.data.llm_model}</Row>
                <Row label="Embedding model">{config.data.embedding_model}</Row>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Retrieval</CardTitle></CardHeader>
              <CardContent>
                <Row label="Vector database">{config.data.vector_store}</Row>
                <Row label="Top K">{config.data.top_k}</Row>
                <Row label="Dense weight">{config.data.dense_weight}</Row>
                <Row label="BM25 weight">{config.data.bm25_weight}</Row>
                <Row label="Retrieval threshold">{config.data.retrieval_threshold}</Row>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Documents and safety</CardTitle></CardHeader>
              <CardContent>
                <Row label="Chunk size">{config.data.chunk_size}</Row>
                <Row label="Chunk overlap">{config.data.chunk_overlap}</Row>
                <Row label="Max upload size">{config.data.max_upload_mb} MB</Row>
                <Row label="Block ungrounded answers">{config.data.block_ungrounded ? "On" : "Off"}</Row>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </>
  );
}
