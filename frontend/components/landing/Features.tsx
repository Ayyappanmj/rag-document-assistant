import { Cpu, FileUp, FolderOpen, MessageSquareText, Plug, Server } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  { icon: FileUp, title: "Drag-and-drop upload", text: "PDF validation, size limits and live upload progress." },
  { icon: FolderOpen, title: "Multi-document Q&A", text: "Ask across several PDFs and get citations from each." },
  { icon: MessageSquareText, title: "Clickable source cards", text: "See the document, page, snippet and retrieval score behind every answer." },
  { icon: Cpu, title: "Free local LLM", text: "Works out of the box with Ollama. No paid API required." },
  { icon: Plug, title: "Pluggable provider", text: "Switch to any OpenAI-compatible API with environment variables." },
  { icon: Server, title: "REST API + Swagger", text: "A documented FastAPI backend with tests and Docker support." },
];

export function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-4 pb-20">
      <h2 className="text-center text-3xl font-bold tracking-tight">Features</h2>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, text }) => (
          <Card key={title} className="bg-card/60">
            <CardHeader>
              <Icon className="mb-2 size-5 text-cyan-300" />
              <CardTitle className="text-base">{title}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{text}</CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
