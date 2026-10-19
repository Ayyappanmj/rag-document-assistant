import { FileUp, Sparkles } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/EmptyState";
import { buttonVariants } from "@/components/ui/button";
import { SAMPLE_QUESTIONS } from "@/lib/constants";

interface Props {
  hasReadyDocuments: boolean;
  onPick: (question: string) => void;
}

export function EmptyChat({ hasReadyDocuments, onPick }: Props) {
  if (!hasReadyDocuments) {
    return (
      <div className="mx-auto max-w-lg py-6">
        <EmptyState
          icon={FileUp}
          title="Upload a PDF to start asking questions."
          description="Once a document is ready you can ask about it here."
        >
          <Link href="/documents" className={buttonVariants()}>Upload Documents</Link>
        </EmptyState>
        <p className="mt-6 text-center text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Sample questions to try afterwards
        </p>
        <ul className="mt-2 space-y-1 text-center text-sm text-muted-foreground">
          {SAMPLE_QUESTIONS.map((q) => (
            <li key={q}>{q}</li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl py-8 text-center">
      <div className="mx-auto mb-4 flex size-10 items-center justify-center rounded-full bg-primary/10">
        <Sparkles className="size-5 text-primary" />
      </div>
      <h2 className="text-lg font-semibold">Ask anything about your documents</h2>
      <p className="mt-1 text-sm text-muted-foreground">Pick a sample question or type your own.</p>
      <div className="mt-6 grid gap-2">
        {SAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="rounded-lg border border-border px-4 py-2.5 text-left text-sm transition-colors hover:border-primary/50 hover:bg-muted/40"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
