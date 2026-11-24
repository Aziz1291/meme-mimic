// Home page: pick a meme from the catalog, or upload your own clip.
// Both start a game on the backend, then go to /play/<session id>.
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listMemes, startSession, uploadMeme } from '../api.js'

// Same limit as the backend (config.MAX_UPLOAD_BYTES). Checked here for instant feedback,
// but the backend checks again: never trust the browser.
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

export default function Home() {
  const navigate = useNavigate()
  const [memes, setMemes] = useState([])
  const [busyMessage, setBusyMessage] = useState('') // not empty = a request is running
  const [error, setError] = useState('')

  useEffect(() => {
    listMemes()
      .then(setMemes)
      .catch((loadError) => setError(loadError.message))
  }, [])

  // One function for both ways to start: it shows the loading message,
  // waits for the session, then opens the Play page.
  async function start(createSession, message) {
    setError('')
    setBusyMessage(message)
    try {
      const session = await createSession()
      navigate(`/play/${session.session_id}`)
    } catch (startError) {
      setError(startError.message)
      setBusyMessage('')
    }
  }

  function handleFileChosen(event) {
    const file = event.target.files[0]
    event.target.value = '' // so choosing the same file again still triggers onChange
    if (!file) {
      return
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setError('This file is too big (max 10 MB).')
      return
    }
    start(() => uploadMeme(file), 'Cutting your meme…')
  }

  const isBusy = busyMessage !== ''

  return (
    <div>
      <h1>Pick a meme</h1>
      <p className="hint">Listen to each piece, then imitate it. 🎧 Headphones recommended.</p>

      {error && <p className="error">{error}</p>}
      {isBusy && <p className="busy">{busyMessage}</p>}

      <div className="meme-list">
        {memes.map((meme) => (
          <div className="card" key={meme.meme_id}>
            <h2>{meme.title}</h2>
            <p className="hint">{meme.section_count} pieces</p>
            {/* Disabled while busy: an impatient double-click would create two games. */}
            <button
              disabled={isBusy}
              onClick={() => start(() => startSession(meme.meme_id), 'Preparing the game…')}
            >
              Play
            </button>
          </div>
        ))}
      </div>

      <div className="card upload">
        <h2>Or use your own clip</h2>
        <p className="hint">Audio or video, 1 to 20 seconds, max 10 MB.</p>
        <input type="file" accept="audio/*,video/*" disabled={isBusy} onChange={handleFileChosen} />
      </div>
    </div>
  )
}
