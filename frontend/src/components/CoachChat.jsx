// The coach chat on the Results page. The coach can PROPOSE a retry; only the player's
// click on the button actually opens that piece again. The model proposes, the player decides.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { askCoach } from '../api.js'

const MAX_MESSAGE_LENGTH = 500 // same limit as the backend (CoachRequest)
const MAX_HISTORY = 20 // same limit as the backend

export default function CoachChat({ sessionId }) {
  const navigate = useNavigate()
  const [messages, setMessages] = useState([]) // [{ role, content }]
  const [draft, setDraft] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [error, setError] = useState('')
  const [pendingAction, setPendingAction] = useState(null)
  const [provider, setProvider] = useState('')

  async function send(event) {
    event.preventDefault() // a form submit would reload the page
    const text = draft.trim()
    if (!text || isThinking) {
      return
    }
    const history = messages.slice(-MAX_HISTORY)
    setMessages([...messages, { role: 'user', content: text }])
    setDraft('')
    setError('')
    setPendingAction(null)
    setIsThinking(true)
    try {
      const answer = await askCoach(sessionId, text, history)
      setMessages((current) => [...current, { role: 'assistant', content: answer.reply }])
      setPendingAction(answer.pending_action)
      setProvider(answer.degraded ? 'mock (no key)' : answer.provider)
    } catch (askError) {
      setError(askError.message)
    }
    setIsThinking(false)
  }

  function confirmRetry() {
    // ?retry=1: after this piece, the Play page brings the player back here.
    navigate(`/play/${sessionId}?section=${pendingAction.section_index}&retry=1`)
  }

  return (
    <div className="card coach">
      <h2>
        🧑‍🏫 Coach
        {/* Honest demo: always show when it's the offline mock answering. */}
        {provider.startsWith('mock') && <span className="badge">{provider} mode</span>}
      </h2>
      <div className="chat">
        {messages.length === 0 && (
          <p className="hint">Ask me: "Which piece was my worst?" or "Any tip for my melody?"</p>
        )}
        {messages.map((message, position) => (
          <p key={position} className={`bubble ${message.role}`}>{message.content}</p>
        ))}
        {isThinking && <p className="busy">Thinking…</p>}
      </div>

      {pendingAction && (
        <button className="record" onClick={confirmRetry}>
          🔁 Retry piece {pendingAction.section_index + 1}?
        </button>
      )}
      {error && <p className="error">{error}</p>}

      <form className="chat-input" onSubmit={send}>
        <input
          value={draft}
          maxLength={MAX_MESSAGE_LENGTH}
          placeholder="Ask the coach…"
          onChange={(event) => setDraft(event.target.value)}
        />
        <button disabled={isThinking || !draft.trim()}>Send</button>
      </form>
    </div>
  )
}
