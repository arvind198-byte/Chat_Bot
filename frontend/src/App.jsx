import { useState, useEffect, useCallback } from 'react'
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

  // ── Load status & chat list on mount ──────────────────────────────────
  useEffect(() => {
    api.status()
      .then(setApiStatus)
      .catch(() => setError('Could not connect to the chatbot backend.'))
    loadChats()
  }, [])

  async function loadChats() {
    try {
      const data = await api.getChats()
      setChats(data)
    } catch (e) {
      setError('Could not load conversations.')
    }
  }

  // ── Select a chat ──────────────────────────────────────────────────────
  async function handleSelect(chatId) {
    setActiveChatId(chatId)
    setError(null)
    try {
      const msgs = await api.getMessages(chatId)
      setMessages(msgs.map(m => ({ role: m.role, content: m.content })))
    } catch {
      setError('Could not load messages.')
    }
  }

  // ── Create a new chat ──────────────────────────────────────────────────
  async function handleNew() {
    setError(null)
    try {
      const chat = await api.createChat()
      setMessages([])
      setActiveChatId(chat.id)
      await loadChats()
    } catch {
      setError('Could not create a new chat.')
    }
  }

  // ── Delete a chat ──────────────────────────────────────────────────────
  async function handleDelete(chatId) {
    try {
      await api.deleteChat(chatId)
      if (chatId === activeChatId) {
        setActiveChatId(null)
        setMessages([])
      }
      await loadChats()
    } catch {
      setError('Could not delete the chat.')
    }
  }

  // ── Send a message ─────────────────────────────────────────────────────
  async function handleSend(content) {
    if (!activeChatId || loading) return
    setError(null)

    // Optimistically show user message
    const userMsg = { role: 'user', content }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const response = await api.sendMessage(activeChatId, content)
      setMessages(prev => [...prev, { role: 'assistant', content: response.content }])
      // Refresh sidebar so the auto-generated title appears
      await loadChats()
      return true
    } catch (e) {
      setError(e.message || 'Something went wrong. Please try again.')
      // Remove the optimistic user message so they can retry
      setMessages(prev => prev.slice(0, -1))
      return false
    } finally {
      setLoading(false)
    }
  }

  // ── Active chat title for the header ──────────────────────────────────
  const activeChat = chats.find(c => c.id === activeChatId)
  const chatTitle = activeChat?.title || 'New Chat'

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
          {activeChatId ? (
            <span className={styles.chatTitle}>{chatTitle}</span>
          ) : (
            <span className={styles.chatTitle}>Son of Anton</span>
          )}
          {apiStatus && !apiStatus.api_configured && (
            <span className={styles.apiWarning}>
              API key missing — add GEMINI_API_KEY to .env
            </span>
          )}
        </header>

        {error && (
          <div className={styles.error} role="alert">
            {error}
            <button onClick={() => setError(null)} className={styles.errorClose} aria-label="Dismiss error">
              &#x2715;
            </button>
          </div>
        )}

        {/* No chat selected */}
        {!activeChatId ? (
          <div className={styles.welcome}>
            <div className={styles.welcomeInner}>
              <h1>Son of Anton</h1>
              <p>Conversational AI powered by Google Gemini.</p>
              <button className={styles.welcomeBtn} onClick={handleNew}>
                Start a new conversation
              </button>
            </div>
          </div>
        ) : (
          <>
            <MessageList messages={messages} loading={loading} />
            <ChatInput onSend={handleSend} disabled={loading} />
          </>
        )}
      </div>
    </div>
  )
}
