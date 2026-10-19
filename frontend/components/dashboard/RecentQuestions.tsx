import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate } from "@/lib/format";
import type { RecentQuestion } from "@/types";

export function RecentQuestions({ questions }: { questions: RecentQuestion[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recent questions</CardTitle>
      </CardHeader>
      <CardContent>
        {questions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No questions yet. Ask one on the Chat page.</p>
        ) : (
          <ul className="divide-y divide-border">
            {questions.map((q) => (
              <li key={q.id} className="py-2 first:pt-0 last:pb-0">
                <Link href={`/chat?c=${q.conversation_id}`} className="line-clamp-2 text-sm hover:text-primary">
                  {q.question}
                </Link>
                <p className="text-xs text-muted-foreground">{formatDate(q.created_at)}</p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
