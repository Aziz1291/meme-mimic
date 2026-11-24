// Records the microphone with the browser's MediaRecorder (no library needed).
// Flow: click → 3-2-1 countdown → recording (auto-stops) → gives the parent a Blob.
import { useEffect, useRef, useState } from 'react'

// Fixed for the whole project: changing them would change our measurements.
// autoGainControl changes your volume on its own (bad for the loudness score);
// noiseSuppression can delete sounds that are part of a meme (screams, whistles).
const MIC_SETTINGS = { echoCancellation: true, noiseSuppression: false, autoGainControl: false }

// Chrome records WebM, Safari records MP4. The backend converts both with ffmpeg.
const FORMATS = [
  { mimeType: 'audio/webm;codecs=opus', extension: 'webm' },
  { mimeType: 'audio/webm', extension: 'webm' },
  { mimeType: 'audio/mp4', extension: 'mp4' },
]

function pickFormat() {
  for (const format of FORMATS) {
    if (MediaRecorder.isTypeSupported(format.mimeType)) {
      return format
    }
  }
  return null
}

function micErrorMessage(error) {
  if (error.name === 'NotAllowedError') {
    return 'Microphone blocked. Allow it in the browser (icon in the address bar), then retry.'
  }
  if (error.name === 'NotFoundError') {
    return 'No microphone found. Plug one in, then retry.'
  }
  return "Can't use the microphone."
}

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds))

// maxSeconds: auto-stop after this long. onRecorded(blob, fileName) is called at the end.
export default function Recorder({ maxSeconds, disabled, onRecorded }) {
  const [phase, setPhase] = useState('idle') // idle | countdown | recording
  const [countdown, setCountdown] = useState(3)
  const [error, setError] = useState('')
  const recorderRef = useRef(null) // the MediaRecorder, kept between renders
  const timerRef = useRef(null)
  const isGoneRef = useRef(false) // true once the component has left the page

  // If the component disappears mid-recording (player leaves the page), release the mic.
  useEffect(() => {
    isGoneRef.current = false
    return () => {
      isGoneRef.current = true
      clearTimeout(timerRef.current)
      if (recorderRef.current && recorderRef.current.state === 'recording') {
        recorderRef.current.stop()
      }
    }
  }, [])

  async function startRecording() {
    setError('')
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      // getUserMedia only exists on localhost or https pages.
      setError('Recording needs a secure page (https or localhost).')
      return
    }
    const format = pickFormat()
    if (!format) {
      setError("This browser can't record audio.")
      return
    }
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: MIC_SETTINGS })
    } catch (micError) {
      setError(micErrorMessage(micError))
      return
    }
    // The countdown gives time to breathe and avoids cutting the first syllable.
    setPhase('countdown')
    for (let second = 3; second >= 1; second -= 1) {
      setCountdown(second)
      await wait(1000)
    }
    if (isGoneRef.current) {
      // The player left during the countdown: turn the mic off and do nothing.
      stream.getTracks().forEach((track) => track.stop())
      return
    }
    record(stream, format)
  }

  function record(stream, format) {
    const chunks = []
    const recorder = new MediaRecorder(stream, { mimeType: format.mimeType })
    recorder.ondataavailable = (event) => chunks.push(event.data)
    recorder.onstop = () => {
      // Turn the mic off, or the browser's "mic in use" indicator stays on.
      stream.getTracks().forEach((track) => track.stop())
      clearTimeout(timerRef.current)
      if (isGoneRef.current) {
        return // the player left the page: don't send anything
      }
      setPhase('idle')
      const blob = new Blob(chunks, { type: format.mimeType })
      onRecorded(blob, `attempt.${format.extension}`)
    }
    recorderRef.current = recorder
    recorder.start()
    setPhase('recording')
    timerRef.current = setTimeout(() => recorder.stop(), maxSeconds * 1000)
  }

  function stopRecording() {
    recorderRef.current.stop() // onstop (above) does the rest
  }

  return (
    <div className="recorder">
      {phase === 'idle' && (
        <button className="record" disabled={disabled} onClick={startRecording}>
          🎙️ Record
        </button>
      )}
      {phase === 'countdown' && <p className="countdown">{countdown}</p>}
      {phase === 'recording' && (
        <button className="record recording" onClick={stopRecording}>
          ⏹ Stop
        </button>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
