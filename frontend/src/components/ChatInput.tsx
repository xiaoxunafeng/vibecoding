import { useState, type KeyboardEvent } from 'react';

interface ChatInputProps {
  streaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}

export function ChatInput({ streaming, onSend, onStop }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [composing, setComposing] = useState(false);

  const submit = () => {
    const text = value.trim();
    if (!text || streaming) return;
    onSend(text);
    setValue('');
    const el = document.querySelector<HTMLTextAreaElement>('.input-box textarea');
    if (el) el.style.height = 'auto';
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !composing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <footer className="chat-input">
      <div className="input-box">
        <textarea
          value={value}
          rows={1}
          autoFocus
          placeholder="输入你的问题…（Enter 发送，Shift+Enter 换行）"
          onChange={(e) => {
            setValue(e.target.value);
            e.target.style.height = 'auto';
            e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
          }}
          onKeyDown={handleKeyDown}
          onCompositionStart={() => setComposing(true)}
          onCompositionEnd={() => setComposing(false)}
        />
        {streaming ? (
          <button className="stop-btn" onClick={onStop}>
            停止
          </button>
        ) : (
          <button
            className="send-btn"
            onClick={submit}
            disabled={!value.trim()}
            aria-label="发送"
          >
            ↑
          </button>
        )}
      </div>
      <p className="input-tip">内容由 AI 生成，请注意甄别准确性</p>
    </footer>
  );
}
