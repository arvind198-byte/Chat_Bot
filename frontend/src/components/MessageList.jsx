import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import styles from './MessageList.module.css'

function parseDate(raw) {
  if (!raw) return null
  let iso = String(raw).trim()
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(iso)) {
    iso = iso.replace(' ', 'T') + 'Z'
  } else if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(iso)) {
    iso = iso + 'Z'
  }
  const d = new Date(iso)
  return isNaN(d.getTime()) ? null : d
}

function formatTimestamp(raw) {
  const d = parseDate(raw)
  if (!d) return ''
  const now = new Date()
  const isToday =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  if (isToday) return timeStr
  const dateStr = d.toLocaleDateString([], { month: 'short', day: 'numeric' })
  return `${dateStr}, ${timeStr}`
}

function formatFullDateTime(raw) {
  const d = parseDate(raw)
  if (!d) return ''
  return d.toLocaleString([], {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatDuration(ms) {
  if (!ms || ms <= 0) return ''
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export default function MessageList({ messages, loading, onFeedback }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (messages.length === 0 && !loading) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>T&P</div>
        <p className={styles.emptyTitle}>Placement Cell Inquiry Desk</p>
        <p className={styles.emptySub}>Ask about eligibility thresholds, company tiers, drive procedures, or preparation rules.</p>
      </div>
    )
  }

  return (
    <div className={styles.list}>
      {messages.map((msg, i) => {
        let promptLatency = msg.latency_ms || 0
        if (msg.role === 'user' && !promptLatency && messages[i + 1]?.role === 'assistant') {
          promptLatency = messages[i + 1].latency_ms || 0
        }
        const isLatestPending = msg.role === 'user' && i === messages.length - 1 && loading

        return (
          <Message
            key={msg.id || i}
            message={msg}
            promptLatency={promptLatency}
            isLatestPending={isLatestPending}
            onFeedback={onFeedback}
          />
        )
      })}
      {loading && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  )
}

function Message({ message, promptLatency, isLatestPending, onFeedback }) {
  const { role, content, latency_ms, tokens_used, id, created_at } = message
  const isUser = role === 'user'
  const [feedbackStatus, setFeedbackStatus] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const formattedTime = formatTimestamp(created_at)
  const formattedFull = formatFullDateTime(created_at)

  async function handleRating(rating) {
    if (!id || submitting || feedbackStatus !== null) return
    setSubmitting(true)
    try {
      if (onFeedback) {
        await onFeedback(id, rating)
      }
      setFeedbackStatus(rating === 1 ? 'positive' : 'negative')
    } catch {
      // Ignored
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={`${styles.row} ${isUser ? styles.userRow : styles.assistantRow}`}>
      {!isUser && <div className={styles.avatar}>T&P</div>}
      <div className={`${styles.bubbleWrapper} ${isUser ? styles.userWrapper : ''}`}>
        <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.assistantBubble}`}>
          {isUser ? (
            <p className={styles.userText}>{content}</p>
          ) : (
            <div className={styles.mdContent}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '')
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={oneLight}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ borderRadius: '6px', fontSize: '0.82rem', margin: '0.5rem 0' }}
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={styles.inlineCode} {...props}>{children}</code>
                    )
                  },
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* User prompt metadata: timestamp & response duration */}
        {isUser && (formattedTime || isLatestPending || promptLatency > 0) && (
          <div className={styles.userMetaRow}>
            {formattedTime && (
              <span className={styles.timestamp} title={formattedFull || undefined}>
                {formattedTime}
              </span>
            )}
            {promptLatency > 0 && (
              <>
                <span className={styles.separator}>·</span>
                <span className={styles.promptDuration} title={`Prompt response latency: ${promptLatency} ms`}>
                  Took {formatDuration(promptLatency)}
                </span>
              </>
            )}
            {isLatestPending && (
              <>
                <span className={styles.separator}>·</span>
                <span className={styles.promptPending}>Processing...</span>
              </>
            )}
          </div>
        )}

        {/* Assistant response metadata: timestamp, latency, tokens & feedback */}
        {!isUser && (
          <div className={styles.metaRow}>
            <div className={styles.metaLeft}>
              {formattedTime && (
                <span className={styles.timestamp} title={formattedFull || undefined}>
                  {formattedTime}
                </span>
              )}
              {latency_ms > 0 && (
                <>
                  {formattedTime && <span className={styles.separator}>·</span>}
                  <span className={styles.metrics} title={`Round-trip response latency: ${latency_ms} ms`}>
                    Took {formatDuration(latency_ms)} ({latency_ms} ms)
                  </span>
                </>
              )}
              {tokens_used > 0 && (
                <>
                  <span className={styles.separator}>·</span>
                  <span className={styles.metrics} title={`Total tokens consumed: ${tokens_used}`}>
                    {tokens_used} tokens
                  </span>
                </>
              )}
            </div>

            {id && (
              <div className={styles.feedbackControls}>
                {feedbackStatus === null ? (
                  <>
                    <button
                      className={styles.feedbackBtn}
                      onClick={() => handleRating(1)}
                      disabled={submitting}
                      title="Helpful response"
                      aria-label="Helpful"
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                      </svg>
                    </button>
                    <button
                      className={styles.feedbackBtn}
                      onClick={() => handleRating(-1)}
                      disabled={submitting}
                      title="Unhelpful response"
                      aria-label="Unhelpful"
                    >
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path>
                      </svg>
                    </button>
                  </>
                ) : (
                  <span className={styles.feedbackConfirmed}>
                    {feedbackStatus === 'positive' ? 'Feedback recorded (+1)' : 'Feedback recorded (-1)'}
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
      {isUser && <div className={`${styles.avatar} ${styles.userAvatar}`}>You</div>}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className={`${styles.row} ${styles.assistantRow}`}>
      <div className={styles.avatar}>T&P</div>
      <div className={`${styles.bubble} ${styles.assistantBubble} ${styles.typing}`}>
        <span /><span /><span />
      </div>
    </div>
  )
}
