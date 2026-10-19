import { ArrowDown } from "lucide-react";

const STEPS = [
  { title: "PDF upload", text: "Validate, store, extract text per page" },
  { title: "Chunking", text: "Recursive splitting with page and section metadata" },
];

const BRANCHES = [
  { title: "Embeddings + FAISS", text: "all-MiniLM-L6-v2 vectors, semantic search" },
  { title: "BM25", text: "Keyword search for exact names, codes and numbers" },
];

const AFTER = [
  { title: "Hybrid retriever", text: "Normalise scores, weighted fusion, top-K" },
  { title: "Context builder + LLM", text: "Context-only prompt, local Ollama by default" },
  { title: "Citations + grounding check", text: "Validated sources, faithfulness and number checks" },
];

function Box({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border border-border bg-card/60 px-4 py-3 text-left">
      <p className="text-sm font-semibold">{title}</p>
      <p className="text-xs text-muted-foreground">{text}</p>
    </div>
  );
}

const Arrow = () => <ArrowDown className="mx-auto my-2 size-4 text-muted-foreground" aria-hidden />;

export function Architecture() {
  return (
    <section id="architecture" className="mx-auto max-w-3xl scroll-mt-20 px-4 pb-20">
      <h2 className="text-center text-3xl font-bold tracking-tight">Architecture overview</h2>
      <p className="mx-auto mt-2 max-w-xl text-center text-muted-foreground">
        A Next.js frontend talks to a FastAPI backend that runs the whole RAG pipeline.
      </p>
      <div className="mt-8">
        {STEPS.map((s) => (
          <div key={s.title}>
            <Box {...s} />
            <Arrow />
          </div>
        ))}
        <div className="grid gap-3 sm:grid-cols-2">
          {BRANCHES.map((b) => (
            <Box key={b.title} {...b} />
          ))}
        </div>
        {AFTER.map((s) => (
          <div key={s.title}>
            <Arrow />
            <Box {...s} />
          </div>
        ))}
      </div>
    </section>
  );
}
