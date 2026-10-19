import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

// Illustrative values for the design preview only. They are NOT benchmark results.
const SAMPLE = [
  { label: "Faithfulness", value: 87 },
  { label: "Answer relevance", value: 91 },
  { label: "Context relevance", value: 89 },
  { label: "Citation coverage", value: 95 },
];

export function EvaluationPreview() {
  return (
    <section id="evaluation" className="mx-auto max-w-3xl scroll-mt-20 px-4 pb-24">
      <h2 className="text-center text-3xl font-bold tracking-tight">Built-in evaluation</h2>
      <p className="mx-auto mt-2 max-w-xl text-center text-muted-foreground">
        Every generated answer is scored, so you can see how well it is supported by your documents.
      </p>
      <Card className="mt-8 bg-card/60">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">RAG evaluation</CardTitle>
          <Badge variant="outline">Sample Evaluation</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          {SAMPLE.map(({ label, value }) => (
            <div key={label}>
              <div className="mb-1 flex justify-between text-sm">
                <span>{label}</span>
                <span className="font-medium">{value}%</span>
              </div>
              <Progress value={value} />
            </div>
          ))}
          <p className="pt-2 text-xs text-muted-foreground">
            Illustrative values for this preview. They are not benchmark results. Your own numbers appear on the
            Evaluation page after you ask questions.
          </p>
        </CardContent>
      </Card>
    </section>
  );
}
