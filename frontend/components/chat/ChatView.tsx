"use client";

import { Eraser, History, Plus } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useChat } from "@/hooks/useChat";
import { useConversations } from "@/hooks/useConversations";
import { useDocuments } from "@/hooks/useDocuments";
import { deleteConversation } from "@/lib/api";
import type { Citation } from "@/types";

import { ChatInput } from "./ChatInput";
import { ConversationList } from "./ConversationList";
import { DocumentScope } from "./DocumentScope";
import { EmptyChat } from "./EmptyChat";
import { MessageList } from "./MessageList";
import { SourceDialog } from "./SourceDialog";

export function ChatView() {
  const params = useSearchParams();
  const conversationParam = params.get("c");
  const docParam = params.get("doc");

  const { documents, loading: docsLoading } = useDocuments();
  const readyDocs = useMemo(() => documents.filter((d) => d.status === "ready"), [documents]);
  const [selected, setSelected] = useState<string[]>(() => (docParam ? [docParam] : []));

  useEffect(() => {
    if (docParam) {
      setSelected([docParam]);
    }
  }, [docParam]);

  const activeDocIds = useMemo(
    () => selected.filter((id) => readyDocs.some((d) => d.id === id)),
    [selected, readyDocs],
  );

  const { conversations, loading: convLoading, refresh } = useConversations();
  const chat = useChat(activeDocIds, () => void refresh());
  const { loadConversation } = chat;

  const [source, setSource] = useState<Citation | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    if (conversationParam) void loadConversation(conversationParam);
  }, [conversationParam, loadConversation]);

  async function removeConversation(id: string) {
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await deleteConversation(id);
      if (id === chat.conversationId) chat.newChat();
      await refresh();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not delete the conversation");
    }
  }

  const history = (
    <ConversationList
      conversations={conversations}
      activeId={chat.conversationId}
      loading={convLoading}
      onSelect={(id) => {
        void chat.loadConversation(id);
        setShowHistory(false);
      }}
      onDelete={(id) => void removeConversation(id)}
      onNew={() => {
        chat.newChat();
        setShowHistory(false);
      }}
    />
  );

  return (
    <div className="flex h-[calc(100dvh-6rem)] gap-4 md:h-[calc(100dvh-4rem)]">
      <aside className="hidden w-64 shrink-0 lg:block">{history}</aside>

      <section className="flex min-w-0 flex-1 flex-col rounded-xl border border-border">
        <header className="flex items-center justify-between gap-2 border-b border-border p-3">
          <h1 className="text-base font-semibold">Chat</h1>
          <div className="flex gap-1">
            <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setShowHistory((v) => !v)}>
              <History className="size-4" /> History
            </Button>
            <Button variant="ghost" size="sm" onClick={chat.newChat}>
              <Plus className="size-4" /> New
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={chat.messages.length === 0 || chat.sending}
              onClick={() => void chat.clear()}
            >
              <Eraser className="size-4" /> Clear chat
            </Button>
          </div>
        </header>

        {showHistory && <div className="max-h-56 border-b border-border p-3 lg:hidden">{history}</div>}

        <div className="pt-3">
          <DocumentScope documents={readyDocs} selected={activeDocIds} onChange={setSelected} />
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          {chat.loading ? (
            <Skeleton className="h-32 w-full rounded-xl" />
          ) : chat.messages.length === 0 && !chat.sending ? (
            docsLoading ? (
              <Skeleton className="h-32 w-full rounded-xl" />
            ) : (
              <EmptyChat hasReadyDocuments={readyDocs.length > 0} onPick={chat.send} />
            )
          ) : (
            <MessageList
              messages={chat.messages}
              sending={chat.sending}
              onRegenerate={chat.regenerate}
              onRetry={chat.retry}
              onOpenSource={setSource}
            />
          )}
        </div>

        <ChatInput disabled={chat.sending || readyDocs.length === 0} onSend={chat.send} />
      </section>

      <SourceDialog citation={source} onClose={() => setSource(null)} />
    </div>
  );
}
