// Every call to the backend lives in this file. Pages never call fetch() directly.
// Each function returns the JSON from the backend, or throws an Error whose message
// can be shown to the player as is.

// Messages for each HTTP error code. 422 uses the backend's own message when it has one.
const ERROR_MESSAGES = {
  404: "This game doesn't exist anymore.",
  413: 'This file is too big.',
  415: "This isn't an audio or video file we can read.",
  422: 'Invalid request.',
  503: 'The service is busy, try again in a moment.',
}

// The one place that calls fetch(). "/api/..." has no host: the Vite proxy forwards it.
async function request(path, options = {}) {
  let response
  try {
    response = await fetch(path, options)
  } catch {
    // fetch() itself fails when the server is unreachable (backend stopped, no network).
    throw new Error("Can't reach the server.")
  }
  if (response.ok) {
    return response.json()
  }
  throw await errorFromResponse(response)
}

async function errorFromResponse(response) {
  let detail = null
  try {
    const body = await response.json()
    // FastAPI sends { detail: "text" }, or { detail: [ ... ] } for validation errors.
    if (typeof body.detail === 'string') {
      detail = body.detail
    }
  } catch {
    // Not JSON (for example the proxy's "502 Bad Gateway" page): keep detail = null.
  }
  const error = new Error(messageFor(response.status, detail))
  error.status = response.status // so a page can react to a code (e.g. 409 → go back)
  return error
}

function messageFor(status, detail) {
  if (status === 422 && detail) {
    return detail // our backend's 422 messages are written for players ("too short"...)
  }
  if (status === 409 && detail) {
    return detail
  }
  if (ERROR_MESSAGES[status]) {
    return ERROR_MESSAGES[status]
  }
  if (status === 502 || status === 504) {
    return "Can't reach the server." // the Vite proxy answers 502 when the backend is off
  }
  return 'Something went wrong. Try again.'
}

// Sends a file as multipart form data, field name "file" (what FastAPI expects).
function postFile(path, file, fileName) {
  const form = new FormData()
  form.append('file', file, fileName)
  // No "Content-Type" header on purpose: the browser adds it, with the right "boundary".
  return request(path, { method: 'POST', body: form })
}

export function getHealth() {
  return request('/api/health')
}

export function listMemes() {
  return request('/api/memes')
}

export function startSession(memeId) {
  return request('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ meme_id: memeId }),
  })
}

export function uploadMeme(file) {
  return postFile('/api/sessions/upload', file, file.name)
}

export function getSession(sessionId) {
  return request(`/api/sessions/${sessionId}`)
}

export function sendAttempt(sessionId, sectionIndex, blob, fileName) {
  return postFile(`/api/sessions/${sessionId}/sections/${sectionIndex}/attempts`, blob, fileName)
}

export function getResult(sessionId) {
  return request(`/api/sessions/${sessionId}/result`)
}

// Not a fetch: the <audio> tag downloads the mix itself from this address.
export function mixUrl(sessionId) {
  return `/api/sessions/${sessionId}/mix`
}

// history = the earlier messages, [{ role: 'user' | 'assistant', content: '...' }].
export function askCoach(sessionId, message, history) {
  return request(`/api/sessions/${sessionId}/coach`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  })
}
