// Results page: total %, best score per piece, and the mix of your attempts.
// If the game isn't finished (409), go back to the Play page.
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getResult, getSession, mixUrl } from '../api.js'

const VERDICT_EMOJIS = { great: '🔥', good: '👍', try_again: '🔁' }

export default function Results() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [session, setSession] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    // Both requests at the same time; continue when both have answered.
    Promise.all([getSession(sessionId), getResult(sessionId)])
      .then(([loadedSession, loadedResult]) => {
        setSession(loadedSession)
        setResult(loadedResult)
      })
      .catch((loadError) => {
        if (loadError.status === 409) {
          navigate(`/play/${sessionId}`) // not finished: back to the game
          return
        }
        setError(loadError.message)
      })
  }, [sessionId, navigate])

  if (error) {
    return <p className="error">{error}</p>
  }
  if (!result) {
    return <p className="busy">Counting your points…</p>
  }

  return (
    <div>
      <p className="hint">{session.meme_title}</p>
      <h1 className="total">{result.total_percent}%</h1>

      <div className="card">
        <h2>Hear yourself</h2>
        <audio controls src={mixUrl(sessionId)} />
      </div>

      <div className="card">
        {result.sections.map((sectionResult) => (
          <div className="result-row" key={sectionResult.index}>
            <span>{session.sections[sectionResult.index].subtitle || `Piece ${sectionResult.index + 1}`}</span>
            <span>
              {VERDICT_EMOJIS[sectionResult.verdict]} {Math.round(sectionResult.best_score * 100)}%
              <span className="hint"> · {sectionResult.attempt_count} tries</span>
            </span>
          </div>
        ))}
      </div>

      {/* Sprint 5: the coach chat goes here. */}

      <div className="actions">
        <Link to="/" className="button">Play again</Link>
      </div>
    </div>
  )
}
