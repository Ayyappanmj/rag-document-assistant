import { cn } from "@/lib/utils";
import type { DocumentRecord } from "@/types";

interface Props {
  documents: DocumentRecord[];
  selected: string[];
  onChange: (ids: string[]) => void;
}

const chip = (active: boolean) =>
  cn(
    "shrink-0 rounded-full border px-3 py-1 text-xs transition-colors",
    active
      ? "border-primary bg-primary/10 text-primary"
      : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground",
  );

/** Lets the user limit retrieval to some documents. Nothing selected means all documents. */
export function DocumentScope({ documents, selected, onChange }: Props) {
  if (documents.length === 0) return null;
  const toggle = (id: string) =>
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);

  return (
    <div className="flex gap-2 overflow-x-auto px-3 pb-3" aria-label="Documents to search">
      <button type="button" className={chip(selected.length === 0)} onClick={() => onChange([])}>
        All documents
      </button>
      {documents.map((doc) => (
        <button
          key={doc.id}
          type="button"
          className={chip(selected.includes(doc.id))}
          aria-pressed={selected.includes(doc.id)}
          onClick={() => toggle(doc.id)}
          title={doc.name}
        >
          <span className="inline-block max-w-[180px] truncate align-bottom">{doc.name}</span>
        </button>
      ))}
    </div>
  );
}
