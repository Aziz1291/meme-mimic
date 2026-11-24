// Draws a sound as bars (the "sticks and dots"): quiet parts = tiny bars, loud parts = tall bars.
// A static picture only: playback is done by the Play page.
import { useEffect, useRef } from 'react'
import WaveSurfer from 'wavesurfer.js'

export default function Waveform({ url, color = '#6c5ce7' }) {
  // A ref points to the real <div> on the page, so wavesurfer can draw inside it.
  const containerRef = useRef(null)

  useEffect(() => {
    const waveform = WaveSurfer.create({
      container: containerRef.current,
      url: url,
      height: 80,
      barWidth: 3,
      barGap: 2,
      barRadius: 2,
      normalize: true, // the loudest bar always reaches the top
      interact: false, // a picture, not a player: clicks do nothing
      waveColor: color,
      cursorWidth: 0,
    })
    // When the waveform is destroyed while still loading, wavesurfer reports an "abort".
    // That's expected (we asked for it), so we ignore it instead of showing an error.
    waveform.on('error', () => {})

    // The cleanup: runs when the url changes or the component disappears.
    // Without it, React's StrictMode (which runs effects twice in development)
    // would leave two waveforms stacked on top of each other.
    return () => waveform.destroy()
  }, [url, color]) // a new url → remove the old waveform, draw the new one

  return <div className="waveform" ref={containerRef} />
}
