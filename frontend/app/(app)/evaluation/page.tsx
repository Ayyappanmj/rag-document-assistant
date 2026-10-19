"use client";

import { Database, FlaskConical } from "lucide-react";
import { useCallback } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { PageHeader } from "@/components/common/PageHeader";
import { LiveSection } from "@/components/evaluation/LiveSection";
import { ResultsList } from "@/components/evaluation/ResultsList";
import { RunPanel } from "@/components/evaluation/RunPanel";
import { SampleSection } from "@/components/evaluation/SampleSection";
import { VectorStoreComparison } from "@/components/evaluation/VectorStoreComparison";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/useApi";
import { useEvaluationRun } from "@/hooks/useEvaluationRun";
import { getEvaluationMetrics, getEvaluationResults, getVectorStoreComparison } from "@/lib/api";

export default function EvaluationPage() {
  const metrics = useApi(getEvaluationMetrics);
  const results = useApi(getEvaluationResults);
  const vectorStores = useApi(getVectorStoreComparison);

  const reloadMetrics = metrics.reload;
  const reloadResults = results.reload;
  const onFinished = useCallback(() => {
    void reloadMetrics();
    void reloadResults();
  }, [reloadMetrics, reloadResults]);
  const run = useEvaluationRun(onFinished);

  return (
    <>
      <PageHeader
        title="Evaluation"
        description="How well are answers supported by your documents? Scores are heuristics, not a benchmark."
        actions={<RunPanel status={run.status} running={run.running} onStart={() => void run.start()} />}
      />

      {metrics.loading && <Skeleton className="h-64 w-full rounded-xl" />}
      {metrics.error && <ErrorState message={metrics.error} onRetry={metrics.reload} />}

      {metrics.data && (
        <div className="space-y-10">
          <section>
            <h2 className="mb-1 text-lg font-semibold">Live usage</h2>
            <p className="mb-4 text-sm text-muted-foreground">Scores from the questions you asked on the Chat page.</p>
            <LiveSection live={metrics.data.live} />
          </section>

          <section>
            <h2 className="mb-1 text-lg font-semibold">Sample evaluation</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              A fixed set of questions about fictional sample documents, useful for comparing settings and models.
            </p>
            {metrics.data.sample ? (
              <div className="space-y-6">
                <SampleSection run={metrics.data.sample} />
                {results.data && (
                  <div>
                    <h3 className="mb-3 text-base font-semibold">Question by question</h3>
                    <ResultsList rows={results.data.results} />
                  </div>
                )}
              </div>
            ) : (
              <EmptyState
                icon={FlaskConical}
                title="No sample evaluation has been run yet"
                description="Create the sample PDFs with python evaluation/make_sample_pdfs.py, upload the three files from evaluation/sample_docs on the Documents page, then press Run sample evaluation."
              />
            )}
          </section>

          <section>
            <h2 className="mb-1 text-lg font-semibold">Vector databases: FAISS vs Chroma</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              The same vectors stored in both databases, measured on this machine.
            </p>
            {vectorStores.data ? (
              <VectorStoreComparison data={vectorStores.data} />
            ) : (
              <EmptyState
                icon={Database}
                title="No comparison has been run yet"
                description="Install Chroma with pip install -r backend/requirements-chroma.txt, then run python evaluation/compare_vector_stores.py from the project root and refresh this page."
              />
            )}
          </section>
        </div>
      )}
    </>
  );
}
