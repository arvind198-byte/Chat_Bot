import styles from './Sidebar.module.css'

export default function Sidebar({ chats, activeChatId, onNew, onSelect, onDelete }) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <span className={styles.brandName}>Placement Cell</span>
        <span className={styles.brandSub}>Virtual Assistant</span>
      </div>

      <button className={styles.newBtn} onClick={onNew}>
        New Inquiry
      </button>

      <div className={styles.listLabel}>
        {chats.length > 0 ? `${chats.length} conversation${chats.length !== 1 ? 's' : ''}` : 'No conversations'}
      </div>

      <nav className={styles.list}>
        {chats.map(chat => (
          <ChatItem
            key={chat.id}
            chat={chat}
            active={chat.id === activeChatId}
            onSelect={onSelect}
            onDelete={onDelete}
          />
        ))}
      </nav>
    </aside>
  )
}

function ChatItem({ chat, active, onSelect, onDelete }) {
  function handleDelete(e) {
    e.stopPropagation()
    if (window.confirm(`Delete "${chat.title}"?\n\nThis will permanently remove the conversation record.`)) {
      onDelete(chat.id)
    }
  }

  return (
    <div
      className={`${styles.item} ${active ? styles.active : ''}`}
      onClick={() => !active && onSelect(chat.id)}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && !active && onSelect(chat.id)}
    >
      <span className={styles.itemTitle}>{chat.title || 'Untitled'}</span>
      <button
        className={styles.deleteBtn}
        onClick={handleDelete}
        title="Delete inquiry"
        aria-label="Delete inquiry"
      >
        &#x2715;
      </button>
    </div>
  )
}
