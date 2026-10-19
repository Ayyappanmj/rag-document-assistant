import { MessageSquare, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { ConversationSummary } from "@/types";

interface Props {
  conversations: ConversationSummary[];
  activeId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
}

export function ConversationList({ conversations, activeId, loading, onSelect, onDelete, onNew }: Props) {
  return (
    <div className="flex h-full flex-col">
      <Button variant="outline" size="sm" className="mb-3 w-full" onClick={onNew}>
        <Plus className="size-4" /> New conversation
      </Button>
      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto">
        {loading && <Skeleton className="h-9 w-full" />}
        {!loading && conversations.length === 0 && (
          <p className="px-2 text-xs text-muted-foreground">Your conversations will appear here.</p>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={cn(
              "group flex items-center gap-1 rounded-lg pr-1 text-sm",
              c.id === activeId ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted",
            )}
          >
            <button
              type="button"
              onClick={() => onSelect(c.id)}
              className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left"
              title={c.title}
            >
              <MessageSquare className="size-3.5 shrink-0" />
              <span className="truncate">{c.title}</span>
            </button>
            <Button
              variant="ghost"
              size="icon"
              className="size-7 opacity-60 hover:opacity-100"
              aria-label={`Delete conversation ${c.title}`}
              onClick={() => onDelete(c.id)}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
