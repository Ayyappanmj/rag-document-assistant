import { TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

interface Props {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: Props) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center rounded-xl border border-destructive/40 bg-destructive/10 px-6 py-8 text-center"
    >
      <TriangleAlert className="mb-3 size-6 text-destructive" />
      <p className="text-sm font-medium">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
