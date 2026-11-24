// Play page: one section at a time. Listen → record → score → retry or next.
// The section number is in the address (?section=2), so a refresh continues the game.
import { useEffect, useReducer, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { getSession, sendAttempt } from '../api.js'
import Recorder from '../components/Recorder.jsx'
import ScoreCard from '../components/ScoreCard.jsx'
import Waveform from '../components/Waveform.jsx'
import { gameReducer, initialState } from './gameReducer.js'

const MAX_RECORDING_SECONDS = 10 // same as the backend's ATTEMPT_MAX_SECONDS

export default function Play() {
  const { sessionId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [state, dispatch] = useReducer(gameReducer, initialState)
  const audioRef = useRef(null)
  // The piece to start on, read from the address once, when the page opens.
  const [startSection] = useState(() => Number(searchParams.get('section')) || 0)

  // Load the session once (and again if the id in the address changes).
  useEffect(() => {
    getSession(sessionId)
      .then((session) => {
        // Keep the number between 0 and the last piece, even if the address was edited by hand.
        const sectionIndex = Math.min(Math.max(startSection, 0), session.sections.length - 1)
        dispatch({ type: 'loaded', session, sectionIndex })
      })
      .catch((error) => dispatch({ type: 'load_failed', error: error.message }))
  }, [sessionId, startSection])

  // The local address of a recording uses memory until we release it.
  useEffect(() => {
    const url = state.attemptUrl
    return () => {
      if (url) {
        URL.revokeObjectURL(url)
      }
    }
  }, [state.attemptUrl])

  if (state.phase === 'loading') {
    return <p className="busy">Loading the game…</p>
  }
  if (state.phase === 'error') {
    return <p className="error">{state.error}</p>
  }

  const sections = state.session.sections
  const section = sections[state.sectionIndex]
  const isLastSection = state.sectionIndex === sections.length - 1
  const sectionSeconds = section.end_s - section.start_s
  const maxSeconds = Math.min(MAX_RECORDING_SECONDS, Math.max(3, sectionSeconds * 3))

  function playOriginal() {
    // Started by a click: browsers block sound that plays on its own.
    audioRef.current.currentTime = 0
    audioRef.current.play()
    dispatch({ type: 'play_started' })
  }

  async function handleRecorded(blob, fileName) {
    dispatch({ type: 'recorded', attemptUrl: URL.createObjectURL(blob) })
    try {
      const attempt = await sendAttempt(sessionId, section.index, blob, fileName)
      dispatch({ type: 'scored', attempt })
    } catch (error) {
      dispatch({ type: 'send_failed', error: error.message })
    }
  }

  function goNext() {
    if (isLastSection) {
      navigate(`/results/${sessionId}`)
      return
    }
    setSearchParams({ section: String(state.sectionIndex + 1) })
    dispatch({ type: 'next' })
  }

  const canRecord = state.phase === 'ready' || state.phase === 'show_score'
  const wasScored = state.attempt && state.attempt.status === 'scored'

  return (
    <div>
      <p className="hint">{state.session.meme_title} · piece {state.sectionIndex + 1} / {sections.length}</p>
      <p className="subtitle">{section.subtitle || '…'}</p>

      <Waveform url={section.audio_url} />
      <audio ref={audioRef} src={section.audio_url} onEnded={() => dispatch({ type: 'play_ended' })} />

      <div className="actions">
        <button disabled={state.phase === 'scoring'} onClick={playOriginal}>
          {state.phase === 'listening' ? '🔊 Playing…' : '▶ Listen'}
        </button>
        <Recorder maxSeconds={maxSeconds} disabled={!canRecord} onRecorded={handleRecorded} />
      </div>
      {state.phase === 'waiting' && <p className="hint">Listen first, then record your imitation.</p>}

      {state.error && <p className="error">{state.error}</p>}
      {state.phase === 'scoring' && <p className="busy">Scoring your imitation…</p>}

      {state.attemptUrl && (
        <div>
          <p className="hint">Your recording:</p>
          <Waveform url={state.attemptUrl} color="#e17055" />
        </div>
      )}

      {state.attempt && <ScoreCard attempt={state.attempt} />}

      {state.phase === 'show_score' && (
        <div className="actions">
          <button className="secondary" onClick={() => dispatch({ type: 'retry' })}>🔁 Retry</button>
          {/* A refused recording keeps you on this piece: only Retry is offered. */}
          {wasScored && (
            <button onClick={goNext}>{isLastSection ? '🏁 See my score' : 'Next ➜'}</button>
          )}
        </div>
      )}
    </div>
  )
}
