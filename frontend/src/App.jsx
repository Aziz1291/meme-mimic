// The app's pages and their addresses (routes).
// The session id is in the address, so refreshing the page doesn't lose the game:
// the page reloads the session from the backend.
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Home from './pages/Home.jsx'
import Play from './pages/Play.jsx'
import Results from './pages/Results.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <header className="top-bar">
        <Link to="/" className="logo">🎤 Meme Mimic</Link>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/play/:sessionId" element={<Play />} />
          <Route path="/results/:sessionId" element={<Results />} />
          <Route path="*" element={<p>Page not found. <Link to="/">Go home</Link></p>} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
