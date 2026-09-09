import { ChatInput } from './components/ChatInput';
import { ChatWindow } from './components/ChatWindow';
import { Sidebar } from './components/Sidebar';
import { useChat } from './hooks/useChat';

export default function App() {
  const chat = useChat();
  const activeConversation = chat.conversations.find((c) => c.id === chat.activeId);

  return (
    <div className="app">
      <Sidebar
        conversations={chat.conversations}
        activeId={chat.activeId}
        disabled={chat.streaming}
        onSelect={chat.selectConversation}
        onNew={() => void chat.newConversation()}
        onDelete={(id) => void chat.removeConversation(id)}
        onRename={chat.renameConversation}
      />
      <div className="chat-main">
        <header className="chat-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{activeConversation?.title ?? 'AI 对话助手'}</span>
          <button
            className={`thinking-switch ${chat.thinking ? 'on' : 'off'}`}
            onClick={chat.toggleThinking}
            disabled={chat.streaming}
            title={chat.thinking ? '当前：思考模式（将先输出思维链）' : '当前：普通模式'}
          >
            <span className="thinking-switch-dot" />
            {chat.thinking ? '思考模式' : '普通模式'}
          </button>
        </header>
        <ChatWindow
          messages={chat.messages}
          error={chat.error}
          onDismissError={chat.clearError}
          onPickSuggestion={chat.send}
        />
        <ChatInput streaming={chat.streaming} onSend={chat.send} onStop={chat.stop} />
      </div>
    </div>
  );
}
