import { FileSearch, Gauge, Layers, Quote, ShieldCheck } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

const PILLARS = [
  { icon: FileSearch, title: "PDF understanding", text: "Page-aware text extraction that keeps page numbers and section titles." },
  { icon: Layers, title: "Hybrid retrieval", text: "FAISS semantic search and BM25 keyword search, fused with configurable weights." },
  { icon: ShieldCheck, title: "Grounded generation", text: "The LLM answers only from retrieved context and refuses when evidence is missing." },
  { icon: Quote, title: "Source citations", text: "Every answer points to the document and page it came from." },
  { icon: Gauge, title: "Hallucination evaluation", text: "Each answer is checked against its context for faithfulness and invented numbers." },
];

export function Pillars() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-20">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {PILLARS.map(({ icon: Icon, title, text }) => (
          <Card key={title} className="bg-card/60">
            <CardContent className="pt-6">
              <Icon className="mb-3 size-5 text-violet-400" />
              <h3 className="text-sm font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{text}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
