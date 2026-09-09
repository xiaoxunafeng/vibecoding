import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../types';
import { MessageItem } from './MessageItem';

const SUGGESTIONS = [
  '用 Python 写一个快速排序，并解释每一步',
  '帮我写一封请假邮件，语气礼貌得体',
  '什么是 HTTP 状态码 301 和 302 的区别？',
  '给初学者推荐一个三个月的前端学习路线',
];

interface ChatWindowProps {
  messages: ChatMessage[];
  error: string | null;
  onDismissError: () => void;
  onPickSuggestion: (text: string) => void;
}

export function ChatWindow({
  messages,
  error,
  onDismissError,
  onPickSuggestion,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <main className="chat-window">
      <div className="message-list">
        {messages.length === 0 ? (
          <div className="welcome">
            <h1>有什么可以帮你？</h1>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => onPickSuggestion(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <MessageItem key={'id' in m ? m.id : `tmp-${i}`} message={m} />
          ))
        )}
        <div ref={bottomRef} />
      </div>
      {error && (
        <div className="error-bar">
          <span>出错了：{error}</span>
          <button onClick={onDismissError}>知道了</button>
        </div>
      )}
    </main>
  );
}
