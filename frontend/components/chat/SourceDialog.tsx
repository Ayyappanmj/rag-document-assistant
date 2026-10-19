import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import type { Citation } from "@/types";

interface Props {
  citation: Citation | null;
  onClose: () => void;
}

/** Shows the exact passage that was retrieved for a citation. */
export function SourceDialog({ citation, onClose }: Props) {
  return (
    <Dialog open={citation !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="truncate">{citation?.document}</DialogTitle>
          <DialogDescription>Page {citation?.page}. The passage below was given to the model.</DialogDescription>
        </DialogHeader>
        {citation && (
          <>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">Similarity {citation.score.toFixed(2)}</Badge>
              <Badge variant="outline">Retrieval: {citation.retrieval_type}</Badge>
            </div>
            <p className="whitespace-pre-wrap rounded-lg border border-border bg-muted/30 p-4 text-sm leading-relaxed">
              {citation.text}
            </p>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
