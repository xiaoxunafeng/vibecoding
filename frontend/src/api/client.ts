import type { Conversation, ConversationDetail } from '../types';

const BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* 非 JSON 响应时保留 statusText */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  listConversations: () => request<Conversation[]>('/conversations'),

  createConversation: () =>
    request<Conversation>('/conversations', { method: 'POST' }),

  getConversation: (id: string) =>
    request<ConversationDetail>(`/conversations/${id}`),

  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    }),

  deleteConversation: (id: string) =>
    request<{ ok: boolean }>(`/conversations/${id}`, { method: 'DELETE' }),

  /**
   * 发起流式对话请求。
   * @param onEvent 收到每个 SSE 事件时回调
   * @param signal 用于停止生成
   */
  streamChat: async (
    body: { conversation_id: string | null; message: string; thinking: boolean },
    onEvent: (event: StreamEvent) => void,
    signal: AbortSignal,
  ): Promise<void> => {
    const res = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok || !res.body) {
      throw new Error(`请求失败: ${res.status} ${res.statusText}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE 事件以空行分隔
      let sep: number;
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        for (const line of raw.split('\n')) {
          if (!line.startsWith('data:')) continue;
          const text = line.slice(5).trim();
          if (!text) continue;
          try {
            onEvent(JSON.parse(text) as StreamEvent);
          } catch {
            /* 跳过无法解析的行 */
          }
        }
      }
    }
  },
};

export type StreamEvent =
  | { type: 'meta'; conversation_id: string; thinking?: boolean }
  | { type: 'delta'; content: string }
  | { type: 'reasoning_delta'; content: string }
  | { type: 'done' }
  | { type: 'error'; message: string };
