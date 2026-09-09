export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  reasoning_content?: string;
  created_at: string;
}

/** 本地流式渲染中的临时消息（尚无数据库 id） */
export interface StreamingMessage {
  role: 'assistant';
  content: string;
  reasoning_content?: string;
  streaming: true;
}

export type ChatMessage = Message | StreamingMessage;

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export function isStreamingMessage(m: ChatMessage): m is StreamingMessage {
  return 'streaming' in m;
}
