import { useState, type KeyboardEvent } from 'react';
import type { Conversation } from '../types';

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  disabled: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
}

export function Sidebar({
  conversations,
  activeId,
  disabled,
  onSelect,
  onNew,
  onDelete,
  onRename,
}: SidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState('');

  const commitRename = (id: string) => {
    setEditingId(null);
    const title = draftTitle.trim();
    if (!title) return;
    onRename(id, title);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="logo">AI 对话助手</span>
      </div>
      <button className="new-chat-btn" onClick={onNew} disabled={disabled}>
        + 新建对话
      </button>
      <nav className="conversation-list">
        {conversations.length === 0 && (
          <p className="empty-hint">暂无对话，点击上方按钮开始</p>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`conversation-item ${c.id === activeId ? 'active' : ''}`}
            onClick={() => !disabled && onSelect(c.id)}
          >
            {editingId === c.id ? (
              <input
                className="rename-input"
                autoFocus
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                onBlur={() => commitRename(c.id)}
                onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === 'Enter') commitRename(c.id);
                  if (e.key === 'Escape') setEditingId(null);
                }}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <>
                <span className="conv-title" title={c.title}>
                  {c.title}
                </span>
                <span className="conv-actions">
                  <button
                    className="icon-btn"
                    title="重命名"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDraftTitle(c.title);
                      setEditingId(c.id);
                    }}
                  >
                    ✎
                  </button>
                  <button
                    className="icon-btn"
                    title="删除"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(c.id);
                    }}
                  >
                    ✕
                  </button>
                </span>
              </>
            )}
          </div>
        ))}
      </nav>
    </aside>
  );
}
