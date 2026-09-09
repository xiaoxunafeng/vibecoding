import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type StreamEvent } from '../api/client';
import type { ChatMessage, Conversation } from '../types';

export function useChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thinking, setThinking] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await api.listConversations());
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  const loadConversation = useCallback(async (id: string) => {
    try {
      const detail = await api.getConversation(id);
      setMessages(detail.messages);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const selectConversation = useCallback(
    (id: string) => {
      if (streaming || id === activeId) return;
      setActiveId(id);
      void loadConversation(id);
    },
    [streaming, activeId, loadConversation],
  );

  const newConversation = useCallback(async () => {
    if (streaming) return;
    try {
      const conv = await api.createConversation();
      setConversations((prev) => [conv, ...prev]);
      setActiveId(conv.id);
      setMessages([]);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [streaming]);

  const removeConversation = useCallback(
    async (id: string) => {
      try {
        await api.deleteConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (activeId === id) {
          setActiveId(null);
          setMessages([]);
        }
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [activeId],
  );

  const renameConversation = useCallback(async (id: string, title: string) => {
    try {
      const updated = await api.renameConversation(id, title);
      setConversations((prev) => prev.map((c) => (c.id === id ? updated : c)));
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const toggleThinking = useCallback(() => {
    if (streaming) return;
    setThinking((prev) => !prev);
  }, [streaming]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || streaming) return;

      setError(null);
      setMessages((prev) => [
        ...prev,
        { id: -Date.now(), role: 'user', content, created_at: '' },
        { role: 'assistant', content: '', reasoning_content: '', streaming: true },
      ]);
      setStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      const patchLast = (patch: (m: ChatMessage) => ChatMessage | null) => {
        setMessages((prev) => {
          if (prev.length === 0) return prev;
          const next = [...prev];
          const patched = patch(next[next.length - 1]);
          if (patched === null) next.pop();
          else next[next.length - 1] = patched;
          return next;
        });
      };

      const handleEvent = (event: StreamEvent) => {
        switch (event.type) {
          case 'meta':
            setActiveId((current) => current ?? event.conversation_id);
            break;
          case 'delta':
            patchLast((m) =>
              'streaming' in m ? { ...m, content: m.content + event.content } : m,
            );
            break;
          case 'reasoning_delta':
            patchLast((m) =>
              'streaming' in m
                ? { ...m, reasoning_content: (m.reasoning_content ?? '') + event.content }
                : m,
            );
            break;
          case 'error':
            setError(event.message);
            break;
          case 'done':
            break;
        }
      };

      try {
        await api.streamChat(
          { conversation_id: activeId, message: content, thinking },
          handleEvent,
          controller.signal,
        );
      } catch (e) {
        if ((e as Error).name !== 'AbortError') {
          setError((e as Error).message);
        }
      } finally {
        patchLast((m) => {
          if (!('streaming' in m)) return m;
          if (!m.content && !m.reasoning_content) return null;
          return {
            id: -Date.now(),
            role: 'assistant',
            content: m.content,
            reasoning_content: m.reasoning_content ?? '',
            created_at: '',
          };
        });
        setStreaming(false);
        abortRef.current = null;
        void refreshConversations();
      }
    },
    [activeId, thinking, streaming, refreshConversations],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    conversations,
    activeId,
    messages,
    streaming,
    thinking,
    toggleThinking,
    error,
    send,
    stop,
    newConversation,
    selectConversation,
    removeConversation,
    renameConversation,
    clearError,
  };
}

export type ChatController = ReturnType<typeof useChat>;
