import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar.jsx'
import MessageList from './components/MessageList.jsx'
import ChatInput from './components/ChatInput.jsx'
import { api } from './api.js'
import styles from './App.module.css'

export default function App() {
  const [chats, setChats] = useState([])
  const [activeChatId, setActiveChatId] = useState(null)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [apiStatus, setApiStatus] = useState(null)

  // Load status & chat list on mount
  useEffect(() => {
    api.status()
      .then(setApiStatus)
      .catch(() => setError('Could not connect to the backend service.'))
    loadChats()
  }, [])

  async function loadChats() {
    try {
      const data = await api.getChats()
      setChats(data)
    } catch {
      setError('Could not load conversations.')
    }
  }

  // Select a chat
  async function handleSelect(chatId) {
    setActiveChatId(chatId)
    setError(null)
    try {
      const msgs = await api.getMessages(chatId)
      setMessages(msgs)
    } catch {
      setError('Could not load messages.')
    }
  }

  // Create a new chat
  async function handleNew() {
    setError(null)
    try {
      const chat = await api.createChat('New Inquiry')
      setMessages([])
      setActiveChatId(chat.id)
      await loadChats()
    } catch {
      setError('Could not create a new inquiry session.')
    }
  }

  // Delete a chat
  async function handleDelete(chatId) {
    try {
      await api.deleteChat(chatId)
      if (chatId === activeChatId) {
        setActiveChatId(null)
        setMessages([])
      }
      await loadChats()
    } catch {
      setError('Could not delete the inquiry.')
    }
  }

  // Send a message
  async function handleSend(content) {
    if (!activeChatId || loading) return
    setError(null)

    // Optimistically show user message with current client timestamp
    const clientTimestamp = new Date().toISOString()
    const tempUserMsg = {
      role: 'user',
      content,
      created_at: clientTimestamp,
    }
    setMessages(prev => [...prev, tempUserMsg])
    setLoading(true)

    try {
      const response = await api.sendMessage(activeChatId, content)
      setMessages(prev => {
        const updated = [...prev]
        const lastIdx = updated.length - 1
        if (lastIdx >= 0 && updated[lastIdx].role === 'user') {
          updated[lastIdx] = {
            ...updated[lastIdx],
            id: response.user_message_id || updated[lastIdx].id,
            created_at: response.user_created_at || updated[lastIdx].created_at || clientTimestamp,
            latency_ms: response.latency_ms,
          }
        }
        return [
          ...updated,
          {
            id: response.id,
            role: 'assistant',
            content: response.content,
            latency_ms: response.latency_ms,
            tokens_used: response.tokens_used,
            created_at: response.created_at || new Date().toISOString(),
          },
        ]
      })
      await loadChats()
      return true
    } catch (e) {
      setError(e.message || 'Inquiry processing failed. Please try again.')
      setMessages(prev => prev.slice(0, -1))
      return false
    } finally {
      setLoading(false)
    }
  }

  // Submit feedback
  async function handleFeedback(messageId, rating) {
    try {
      await api.submitFeedback(messageId, rating)
    } catch (e) {
      console.error('Feedback submission failed:', e)
      throw e
    }
  }

  const activeChat = chats.find(c => c.id === activeChatId)
  const chatTitle = activeChat?.title || 'Placement Inquiry'

  return (
    <div className={styles.layout}>
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onNew={handleNew}
        onSelect={handleSelect}
        onDelete={handleDelete}
      />

      <div className={styles.main}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.brandTitle}>Placement Cell Virtual Assistant</span>
            {activeChatId && <span className={styles.headerSeparator}>/</span>}
            {activeChatId && <span className={styles.chatTitle}>{chatTitle}</span>}
          </div>
          {apiStatus && !apiStatus.api_configured && (
            <span className={styles.apiWarning}>
              API key missing in environment
            </span>
          )}
        </header>

        {error && (
          <div className={styles.error} role="alert">
            <span>{error}</span>
            <button onClick={() => setError(null)} className={styles.errorClose} aria-label="Dismiss">
              &#x2715;
            </button>
          </div>
        )}

        {/* No chat selected */}
        {!activeChatId ? (
          <div className={styles.welcome}>
            <div className={styles.welcomeInner}>
              <div className={styles.welcomeBadge}>Official Placement Desk</div>
              <h1>Placement Cell Virtual Assistant</h1>
              <p className={styles.welcomeBanner}>
                Inquire about recruitment drives, company eligibility criteria, interview preparation, and placement policies.
              </p>
              <button className={styles.welcomeBtn} onClick={handleNew}>
                Start New Inquiry
              </button>
            </div>
          </div>
        ) : (
          <>
            <MessageList
              messages={messages}
              loading={loading}
              onFeedback={handleFeedback}
            />
            <ChatInput onSend={handleSend} disabled={loading} />
          </>
        )}
      </div>
    </div>
  )
}
