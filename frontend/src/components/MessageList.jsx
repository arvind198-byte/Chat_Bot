import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import styles from './MessageList.module.css'

export default function MessageList({ messages, loading }) {
  const bottomRef = useRef(null)

  // Auto-scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (messages.length === 0 && !loading) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>&#9675;</div>
        <p className={styles.emptyTitle}>Start a conversation</p>
        <p className={styles.emptySub}>Type a message below to begin.</p>
      </div>
    )
  }

  return (
    <div className={styles.list}>
      {messages.map((msg, i) => (
        <Message key={i} role={msg.role} content={msg.content} />
      ))}
      {loading && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  )
}

function Message({ role, content }) {
  const isUser = role === 'user'
  return (
    <div className={`${styles.row} ${isUser ? styles.userRow : styles.assistantRow}`}>
      {!isUser && <div className={styles.avatar}>A</div>}
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
                      customStyle={{ borderRadius: '8px', fontSize: '0.82rem', margin: '0.5rem 0' }}
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
      {isUser && <div className={`${styles.avatar} ${styles.userAvatar}`}>You</div>}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className={`${styles.row} ${styles.assistantRow}`}>
      <div className={styles.avatar}>A</div>
      <div className={`${styles.bubble} ${styles.assistantBubble} ${styles.typing}`}>
        <span /><span /><span />
      </div>
    </div>
  )
}
