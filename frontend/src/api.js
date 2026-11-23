// Every call to the backend lives in this file. Pages never call fetch() directly.
// Later sprints add more functions here (startSession, sendAttempt, askCoach, ...).

// Asks the backend if it's alive. Returns the JSON, e.g. { status: "ok", mode: "mock", ffmpeg: true }.
// Throws an Error with a player-friendly message if something goes wrong.
export async function getHealth() {
  let response
  try {
    // "/api/..." without a host: the Vite proxy forwards it to the backend.
    response = await fetch('/api/health')
  } catch {
    // fetch() itself fails when the network or the server is unreachable.
    throw new Error("Can't reach the server.")
  }
  if (!response.ok) {
    // The server answered, but with an error code (e.g. 500, or 502 from the proxy).
    throw new Error("Can't reach the server.")
  }
  return response.json()
}
