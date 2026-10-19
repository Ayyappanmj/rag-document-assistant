"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";

import { deleteConversation, getConversation, sendChat, sendChatStream } from "@/lib/api";
import { errorMessage, fromRecord, fromResponse, userMessage } from "@/lib/chatMapping";
import type { ChatMessage, Citation } from "@/types";

/** Chat state and actions. `documentIds` limits retrieval to those documents (empty = all). */
export function useChat(documentIds: string[], onChanged: () => void) {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);

  const ask = useCallback(
    async (question: string, regenerate = false) => {
      setSending(true);
      const assistantId = "streaming-" + Date.now();
      let streamedAnswer = "";

      // Add a streaming placeholder message
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          citations: [],
          grounded: null,
          confidence: null,
          unsupportedClaims: [],
          citationCoverage: null,
          invalidCitations: [],
          totalMs: null,
          retrievalMs: null,
          generationMs: null,
          streaming: true,
        },
      ]);

      try {
        const res = await sendChatStream(
          {
            question,
            conversation_id: conversationId,
            document_ids: documentIds.length > 0 ? documentIds : null,
            regenerate,
          },
          (token) => {
            streamedAnswer += token;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId ? { ...msg, content: streamedAnswer } : msg
              )
            );
          },
          (sources) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId ? { ...msg, citations: sources } : msg
              )
            );
          }
        );
        setConversationId(res.conversation_id);
        setMessages((prev) =>
          prev.map((msg) => (msg.id === assistantId ? fromResponse(res) : msg))
        );
        onChanged();
      } catch {
        // Fallback to non-streaming if stream reader fails
        try {
          const res = await sendChat({
            question,
            conversation_id: conversationId,
            document_ids: documentIds.length > 0 ? documentIds : null,
            regenerate,
          });
          setConversationId(res.conversation_id);
          setMessages((prev) =>
            prev.map((msg) => (msg.id === assistantId ? fromResponse(res) : msg))
          );
          onChanged();
        } catch (e2) {
          const message = e2 instanceof Error ? e2.message : "Something went wrong";
          setMessages((prev) => [
            ...prev.filter((m) => m.id !== assistantId),
            errorMessage(message, question),
          ]);
        }
      } finally {
        setSending(false);
      }
    },
    [conversationId, documentIds, onChanged],
  );

  const send = useCallback(
    (text: string) => {
      const question = text.trim();
      if (!question || sending) return;
      setMessages((prev) => [...prev, userMessage(question)]);
      void ask(question);
    },
    [ask, sending],
  );

  /** Ask the same question again and replace the last answer. */
  const regenerate = useCallback(() => {
    if (sending) return;
    const lastUser = messages.map((m) => m.role).lastIndexOf("user");
    if (lastUser === -1) return;
    const question = messages[lastUser].content;
    setMessages(messages.slice(0, lastUser + 1)); // drop the old answer
    void ask(question, true);
  }, [ask, messages, sending]);

  /** After a failed request nothing was saved on the server, so just ask again. */
  const retry = useCallback(() => {
    if (sending) return;
    const last = messages[messages.length - 1];
    if (!last?.error || !last.question) return;
    const question = last.question;
    setMessages(messages.slice(0, -2)); // remove the error bubble and the question that failed
    send(question);
  }, [messages, send, sending]);

  const newChat = useCallback(() => {
    setConversationId(null);
    setMessages([]);
  }, []);

  const loadConversation = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const detail = await getConversation(id);
      setConversationId(detail.id);
      setMessages(detail.messages.map(fromRecord));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not load the conversation");
    } finally {
      setLoading(false);
    }
  }, []);

  /** Delete the current conversation from the server and start fresh. */
  const clear = useCallback(async () => {
    if (conversationId) {
      try {
        await deleteConversation(conversationId);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Could not clear the chat");
        return;
      }
      onChanged();
    }
    newChat();
  }, [conversationId, newChat, onChanged]);

  return { conversationId, messages, sending, loading, send, regenerate, retry, newChat, loadConversation, clear };
}
