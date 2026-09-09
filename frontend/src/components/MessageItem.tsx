import { useState, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import type { ChatMessage } from '../types';
import { isStreamingMessage } from '../types';
import 'highlight.js/styles/github-dark.css';

function CopyButton({ getText }: { getText: () => string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="copy-btn"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(getText());
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1500);
        } catch {
          /* 剪贴板不可用时忽略 */
        }
      }}
    >
      {copied ? '已复制' : '复制'}
    </button>
  );
}

function ThinkingBlock({
  reasoning,
  streaming,
}: {
  reasoning: string;
  streaming: boolean;
}) {
  const [open, setOpen] = useState(true);
  const preview = reasoning.match(/\S/) ? reasoning.trim().slice(0, 80) : '';
  return (
    <div className={`thinking-block ${open ? 'open' : ''}`}>
      <button className="thinking-toggle" onClick={() => setOpen((v) => !v)}>
        <span className="thinking-label">{open ? '已展开思考过程' : '思考过程'}</span>
        {streaming && <span className="thinking-dot" aria-hidden />}
        {!open && preview ? <span className="thinking-preview"> — {preview}…</span> : null}
        <span className="thinking-chevron">{open ? '▴' : '▾'}</span>
      </button>
      {open && (
        <div className="thinking-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
            {reasoning}
          </ReactMarkdown>
          {streaming && <span className="cursor" aria-hidden />}
        </div>
      )}
    </div>
  );
}

function renderMarkdown(
  content: string,
  streaming: boolean,
  formatter: (children: ReactNode) => ReactNode,
) {
  return (
    <>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          pre: ({ children }) => formatter(children),
        }}
      >
        {content}
      </ReactMarkdown>
      {streaming && <span className="cursor" aria-hidden />}
    </>
  );
}

export function MessageItem({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  const streaming = isStreamingMessage(message);
  const reasoning = message.reasoning_content ?? '';
  const hasReasoning = Boolean(reasoning);

  const codeBlock = (children: ReactNode) => {
    const textForCopy = () => {
      if (typeof children === 'string') return children;
      return String(children).replace(/<[^>]+>/g, '');
    };
    return (
      <div className="code-block">
        <div className="code-toolbar">
          <CopyButton getText={textForCopy} />
        </div>
        <pre>{children}</pre>
      </div>
    );
  };

  if (isUser) {
    return (
      <div className="message-row user">
        <div className="avatar">我</div>
        <div className="bubble">
          <p className="user-text">{message.content}</p>
        </div>
      </div>
    );
  }

  const isReasoningPhase = streaming && hasReasoning && !message.content;

  return (
    <div className="message-row assistant">
      <div className="avatar">AI</div>
      <div className="bubble">
        {hasReasoning && (
          <ThinkingBlock reasoning={reasoning} streaming={isReasoningPhase} />
        )}
        {message.content ? (
          renderMarkdown(message.content, streaming && !isReasoningPhase, codeBlock)
        ) : isReasoningPhase ? null : streaming ? (
          <span className="cursor" aria-hidden />
        ) : null}
      </div>
    </div>
  );
}
