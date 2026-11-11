
import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import {
  BrainCircuit,
  Plus,
  MessageSquare,
  Send,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  User,
  Trash2,
  AlertCircle,
  LoaderCircle,
  Network,
  ShieldCheck,
  Users,
  Workflow,
  TrendingUp,
} from 'lucide-react'
import './App.css'

const API_URL = '/api/assistant/chat'

const suggestions = [
  {
    icon: Network,
    title: 'Organizational intelligence',
    prompt: 'Audit the organizational hierarchy and identify employees with missing manager assignments.',
  },
  {
    icon: ShieldCheck,
    title: 'Approval routing',
    prompt: 'Analyze pending leave requests and identify approval routing problems.',
  },
  {
    icon: Users,
    title: 'Workforce analysis',
    prompt: 'Analyze active projects, staffing shortages and employee workload allocation.',
  },
  {
    icon: TrendingUp,
    title: 'Predictive intelligence',
    prompt: 'Run a predictive workforce risk assessment and recommend preventive actions.',
  },
]

// Render inline Markdown formatting.
function renderInline(text, keyPrefix = '') {
  const pattern = /(\*\*.*?\*\*|__.*?__|(?<!\*)\*[^*]+\*|(?<!_)_[^_]+_|`[^`]+`)/g

  return text.split(pattern).map((part, index) => {
    const key = `${keyPrefix}-${index}`

    if (
      (part.startsWith('**') && part.endsWith('**')) ||
      (part.startsWith('__') && part.endsWith('__'))
    ) {
      return <strong key={key}>{part.slice(2, -2)}</strong>
    }

    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={key}>{part.slice(1, -1)}</code>
    }

    if (
      (part.startsWith('*') && part.endsWith('*')) ||
      (part.startsWith('_') && part.endsWith('_'))
    ) {
      return <em key={key}>{part.slice(1, -1)}</em>
    }

    return part
  })
}

function isTableSeparator(line) {
  return /^\|?[\s:|-]+\|?$/.test(line.trim()) && line.includes('-')
}

function parseTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

// Render Markdown blocks.
function formatAnswer(content) {
  if (!content) return null

  const lines = content.split('\n')
  const elements = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    const trimmed = line.trim()

    if (!trimmed) {
      index++
      continue
    }

    // Fenced code blocks.
    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim()
      const codeLines = []
      index++

      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        codeLines.push(lines[index])
        index++
      }

      if (index < lines.length) index++

      elements.push(
        <pre key={`code-${index}`} className="markdown-code-block">
          {language && (
            <span className="markdown-code-language">{language}</span>
          )}
          <code>{codeLines.join('\n')}</code>
        </pre>
      )
      continue
    }

    // Markdown tables.
    if (
      trimmed.includes('|') &&
      index + 1 < lines.length &&
      isTableSeparator(lines[index + 1])
    ) {
      const headers = parseTableRow(line)
      index += 2

      const rows = []

      while (index < lines.length && lines[index].trim().includes('|')) {
        rows.push(parseTableRow(lines[index]))
        index++
      }

      elements.push(
        <div className="markdown-table-wrapper" key={`table-${index}`}>
          <table className="markdown-table">
            <thead>
              <tr>
                {headers.map((header, headerIndex) => (
                  <th key={headerIndex}>
                    {renderInline(header, `th-${headerIndex}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {headers.map((_, cellIndex) => (
                    <td key={cellIndex}>
                      {renderInline(row[cellIndex] || '', `td-${rowIndex}-${cellIndex}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      continue
    }

    // Headings.
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/)

    if (headingMatch) {
      const level = headingMatch[1].length
      const Heading = `h${level}`

      elements.push(
        <Heading key={`heading-${index}`} className={`markdown-heading heading-${level}`}>
          {renderInline(headingMatch[2], `heading-${index}`)}
        </Heading>
      )
      index++
      continue
    }

    // Horizontal divider.
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      elements.push(<hr key={`hr-${index}`} className="markdown-divider" />)
      index++
      continue
    }

    // Blockquotes.
    if (trimmed.startsWith('>')) {
      const quoteLines = []

      while (index < lines.length && lines[index].trim().startsWith('>')) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ''))
        index++
      }

      elements.push(
        <blockquote key={`quote-${index}`} className="markdown-blockquote">
          {quoteLines.map((quote, quoteIndex) => (
            <p key={quoteIndex}>{renderInline(quote, `quote-${quoteIndex}`)}</p>
          ))}
        </blockquote>
      )
      continue
    }

    // Unordered lists.
    if (/^[-*+]\s+/.test(trimmed)) {
      const items = []

      while (
        index < lines.length &&
        /^[-*+]\s+/.test(lines[index].trim())
      ) {
        items.push(lines[index].trim().replace(/^[-*+]\s+/, ''))
        index++
      }

      elements.push(
        <ul key={`ul-${index}`} className="markdown-list">
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>
              {renderInline(item, `ul-${itemIndex}`)}
            </li>
          ))}
        </ul>
      )
      continue
    }

    // Ordered lists.
    if (/^\d+[.)]\s+/.test(trimmed)) {
      const items = []

      while (
        index < lines.length &&
        /^\d+[.)]\s+/.test(lines[index].trim())
      ) {
        items.push(lines[index].trim().replace(/^\d+[.)]\s+/, ''))
        index++
      }

      elements.push(
        <ol key={`ol-${index}`} className="markdown-list">
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>
              {renderInline(item, `ol-${itemIndex}`)}
            </li>
          ))}
        </ol>
      )
      continue
    }

    // Regular paragraphs.
    const paragraphLines = [trimmed]
    index++

    while (index < lines.length) {
      const next = lines[index].trim()

      if (
        !next ||
        /^(#{1,6})\s/.test(next) ||
        /^[-*+]\s+/.test(next) ||
        /^\d+[.)]\s+/.test(next) ||
        next.startsWith('>') ||
        next.startsWith('```') ||
        /^(-{3,}|\*{3,}|_{3,})$/.test(next) ||
        (next.includes('|') &&
          index + 1 < lines.length &&
          isTableSeparator(lines[index + 1]))
      ) {
        break
      }

      paragraphLines.push(next)
      index++
    }

    elements.push(
      <p key={`paragraph-${index}`} className="markdown-paragraph">
        {paragraphLines.map((paragraphLine, lineIndex) => (
          <span key={lineIndex}>
            {lineIndex > 0 && ' '}
            {renderInline(paragraphLine, `paragraph-${index}-${lineIndex}`)}
          </span>
        ))}
      </p>
    )
  }

  return elements
}

function App() {
  const [conversations, setConversations] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [error, setError] = useState('')

  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeId
  )

  const messages = activeConversation?.messages || []

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const createConversation = () => {
    const id = crypto.randomUUID()

    setConversations((previous) => [
      {
        id,
        title: 'New conversation',
        messages: [],
      },
      ...previous,
    ])

    setActiveId(id)
    setInput('')
    setError('')
  }

  const selectConversation = (id) => {
    setActiveId(id)
    setError('')
  }

  const deleteConversation = (id) => {
    const updated = conversations.filter(
      (conversation) => conversation.id !== id
    )

    setConversations(updated)

    if (activeId === id) {
      setActiveId(updated[0]?.id || null)
    }
  }

  const sendMessage = async (text = input) => {
    const question = text.trim()

    if (!question || loading) return

    let conversationId = activeId

    if (!conversationId) {
      conversationId = crypto.randomUUID()

      setConversations((previous) => [
        {
          id: conversationId,
          title: question.slice(0, 45),
          messages: [],
        },
        ...previous,
      ])

      setActiveId(conversationId)
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
    }

    setConversations((previous) =>
      previous.map((conversation) =>
        conversation.id === conversationId
          ? {
              ...conversation,
              title:
                conversation.messages.length === 0
                  ? question.slice(0, 45)
                  : conversation.title,
              messages: [...conversation.messages, userMessage],
            }
          : conversation
      )
    )

    setInput('')
    setError('')
    setLoading(true)

    try {
      const response = await axios.post(API_URL, {
        question,
      })

      const assistantMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.data.answer,
        orchestration: response.data.orchestration,
        model: response.data.model,
      }

      setConversations((previous) =>
        previous.map((conversation) =>
          conversation.id === conversationId
            ? {
                ...conversation,
                messages: [
                  ...conversation.messages,
                  assistantMessage,
                ],
              }
            : conversation
        )
      )
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        'Unable to connect to Nexora. Please check that the backend is running and try again.'

      setError(message)
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="nexora-app">

      <aside className={`sidebar ${sidebarOpen ? '' : 'sidebar-closed'}`}>
        <div className="sidebar-top">
          <div className="brand">
            <div className="brand-icon">
              <BrainCircuit size={23} />
            </div>

            {sidebarOpen && (
              <div className="brand-text">
                <span>NEXORA</span>
                <small>WORKFORCE INTELLIGENCE</small>
              </div>
            )}
          </div>

          <button
            className="icon-button sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title="Toggle sidebar"
          >
            {sidebarOpen ? (
              <PanelLeftClose size={19} />
            ) : (
              <PanelLeftOpen size={19} />
            )}
          </button>
        </div>

        <button className="new-chat-button" onClick={createConversation}>
          <Plus size={18} />
          {sidebarOpen && <span>New conversation</span>}
        </button>

        {sidebarOpen && (
          <>
            <div className="sidebar-section">
              <span className="section-label">WORKSPACE</span>

              <div className="nav-item active">
                <MessageSquare size={17} />
                <span>AI Assistant</span>
              </div>
            </div>

            <div className="sidebar-section">
              <span className="section-label">INTELLIGENCE</span>

              <div className="nav-item">
                <Network size={17} />
                <span>Organizational</span>
              </div>

              <div className="nav-item">
                <ShieldCheck size={17} />
                <span>Approval Routing</span>
              </div>

              <div className="nav-item">
                <Users size={17} />
                <span>Workforce</span>
              </div>

              <div className="nav-item">
                <Workflow size={17} />
                <span>HR Workflow</span>
              </div>

              <div className="nav-item">
                <TrendingUp size={17} />
                <span>Predictive</span>
              </div>
            </div>

            <div className="sidebar-section conversation-section">
              <span className="section-label">RECENT CONVERSATIONS</span>

              {conversations.length === 0 ? (
                <div className="empty-history">
                  Your conversations will appear here.
                </div>
              ) : (
                conversations.map((conversation) => (
                  <div
                    key={conversation.id}
                    className={`history-item ${
                      activeId === conversation.id ? 'selected' : ''
                    }`}
                  >
                    <button
                      className="history-title"
                      onClick={() => selectConversation(conversation.id)}
                    >
                      <MessageSquare size={15} />
                      <span>{conversation.title}</span>
                    </button>

                    <button
                      className="delete-chat"
                      onClick={() => deleteConversation(conversation.id)}
                      title="Delete conversation"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        <div className="sidebar-footer">
          <div className="system-status">
            <span className="status-dot" />
            {sidebarOpen && <span>AI Engine ready</span>}
          </div>

          {sidebarOpen && (
            <div className="version-label">NEXORA v2.0</div>
          )}
        </div>
      </aside>

      <main className="main-content">

        <header className="topbar">
          <div className="topbar-left">
            {!sidebarOpen && (
              <button
                className="icon-button"
                onClick={() => setSidebarOpen(true)}
              >
                <PanelLeftOpen size={20} />
              </button>
            )}

            <div className="page-title">
              <span>AI Assistant</span>
              <small>Workforce intelligence, powered by AI</small>
            </div>
          </div>

          <div className="topbar-right">
            <div className="connection-status">
              <span className="status-dot" />
              <span>System online</span>
            </div>
            <div className="avatar">N</div>
          </div>
        </header>

        <section className="chat-area">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-icon">
                <Sparkles size={29} />
              </div>

              <h1>How can I help your workforce today?</h1>

              <p className="welcome-description">
                Ask Nexora about employees, organizational structures,
                approvals, workforce allocation and predictive risks.
                Nexora automatically selects the relevant HR tools.
              </p>

              <div className="suggestion-grid">
                {suggestions.map((suggestion) => {
                  const Icon = suggestion.icon

                  return (
                    <button
                      key={suggestion.title}
                      className="suggestion-card"
                      onClick={() => sendMessage(suggestion.prompt)}
                      disabled={loading}
                    >
                      <Icon size={20} />
                      <div>
                        <strong>{suggestion.title}</strong>
                        <span>{suggestion.prompt}</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ) : (
            <div className="messages-container">
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={`message-row ${message.role}`}
                >
                  <div className={`message-avatar ${message.role}`}>
                    {message.role === 'assistant' ? (
                      <BrainCircuit size={19} />
                    ) : (
                      <User size={19} />
                    )}
                  </div>

                  <div className="message-content">
                    <div className="message-author">
                      {message.role === 'assistant' ? 'Nexora' : 'You'}
                    </div>

                    <div className="message-text">
                      {message.role === 'assistant'
                        ? formatAnswer(message.content)
                        : message.content}
                    </div>

                    {message.role === 'assistant' && (
                      <div className="message-meta">
                        <span>{message.model || 'Groq'}</span>
                        <span className="meta-separator">·</span>
                        <span>{message.orchestration || 'AI Assistant'}</span>
                      </div>
                    )}
                  </div>
                </article>
              ))}

              {loading && (
                <div className="message-row assistant">
                  <div className="message-avatar assistant">
                    <BrainCircuit size={19} />
                  </div>

                  <div className="message-content">
                    <div className="message-author">Nexora</div>
                    <div className="loading-indicator">
                      <LoaderCircle size={17} className="spin" />
                      <span>
                        Analyzing your request and consulting HR tools...
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}

          {error && (
            <div className="error-message">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}
        </section>

        <footer className="chat-footer">
          <div className="prompt-container">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message Nexora about your workforce..."
              rows={1}
              disabled={loading}
            />

            <button
              className="send-button"
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              title="Send message"
            >
              {loading ? (
                <LoaderCircle size={19} className="spin" />
              ) : (
                <Send size={19} />
              )}
            </button>
          </div>

          <div className="input-hint">
            <span>
              <Sparkles size={13} />
              Powered by Groq and LangGraph
            </span>
            <span>Enter to send · Shift + Enter for a new line</span>
          </div>

          <div className="disclaimer">
            Nexora provides decision support. HR authorization is required
            for employee and approval decisions.
          </div>
        </footer>

      </main>
    </div>
  )
}

export default App
