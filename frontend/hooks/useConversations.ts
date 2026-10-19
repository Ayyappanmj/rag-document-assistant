"use client";

import { useCallback, useEffect, useState } from "react";

import { listConversations } from "@/lib/api";
import type { ConversationSummary } from "@/types";

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setConversations(await listConversations());
    } catch {
      /* the chat itself reports connection errors; an empty history is fine here */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { conversations, loading, refresh };
}
