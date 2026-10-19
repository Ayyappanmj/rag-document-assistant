"use client";

import { FileUp } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { DashboardSkeleton } from "@/components/dashboard/DashboardSkeleton";
import { EvaluationSummaryCard } from "@/components/dashboard/EvaluationSummaryCard";
import { RecentDocuments } from "@/components/dashboard/RecentDocuments";
import { RecentQuestions } from "@/components/dashboard/RecentQuestions";
import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { buttonVariants } from "@/components/ui/button";
import { useApi } from "@/hooks/useApi";
import { getDashboardStats } from "@/lib/api";

export default function DashboardPage() {
  const { data, error, loading, reload } = useApi(getDashboardStats);

  return (
    <>
      <PageHeader title="Dashboard" description="An overview of your documents, questions and answer quality." />
      {loading && <DashboardSkeleton />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.total_documents === 0 && (
        <EmptyState
          icon={FileUp}
          title="Upload a PDF to start asking questions."
          description="Your statistics will appear here once you add a document."
        >
          <Link href="/documents" className={buttonVariants()}>Upload Documents</Link>
        </EmptyState>
      )}
      {data && data.total_documents > 0 && (
        <div className="space-y-6">
          <StatsGrid stats={data} />
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <RecentDocuments documents={data.recent_documents} />
            </div>
            <EvaluationSummaryCard evaluation={data.evaluation} />
          </div>
          <RecentQuestions questions={data.recent_questions} />
        </div>
      )}
    </>
  );
}
