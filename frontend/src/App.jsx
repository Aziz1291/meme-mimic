// The whole app for now: one page that shows whether the backend is alive.
// Sprint 3 replaces this with real pages (Home, Play, Results).
import { useEffect, useState } from 'react'
import { getHealth } from './api.js'

export default function App() {
  // What we show: "Checking…", then the backend status or an error message.
  const [message, setMessage] = useState('Checking the backend…')

  // useEffect runs after the page is drawn: the right moment to call the backend.
  // The [] at the end means "only once, when the page opens".
  useEffect(() => {
    getHealth()
      .then((health) => setMessage(`Backend: ${health.status} (${health.mode} mode)`))
      .catch((error) => setMessage(error.message))
  }, [])

  return (
    <main>
      <h1>Meme Mimic</h1>
      <p>{message}</p>
    </main>
  )
}
