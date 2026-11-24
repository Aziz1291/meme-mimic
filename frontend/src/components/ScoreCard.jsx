// Shows the backend's answer to one recording: the score and its 4 parts, or the refusal.
const VERDICT_LABELS = {
  great: '🔥 Great!',
  good: '👍 Good',
  try_again: '🔁 Try again',
}

const SUB_SCORE_LABELS = {
  timbre: 'Sound',
  melody: 'Melody',
  loudness: 'Loud / quiet',
  rhythm: 'Length',
}

function SubScoreBar({ label, value }) {
  // melody can be null: this sound has no melody to compare (not the same as 0).
  if (value === null) {
    return (
      <div className="sub-score">
        <span>{label}</span>
        <span className="hint">no melody here</span>
      </div>
    )
  }
  const percent = Math.round(value * 100)
  return (
    <div className="sub-score">
      <span>{label}</span>
      <div className="bar"><div className="bar-fill" style={{ width: `${percent}%` }} /></div>
      <span>{percent}%</span>
    </div>
  )
}

export default function ScoreCard({ attempt }) {
  if (attempt.status === 'refused') {
    return (
      <div className="card score refused">
        <h2>Not scored</h2>
        <p>{attempt.message}</p>
      </div>
    )
  }
  return (
    <div className={`card score ${attempt.verdict}`}>
      <h2>{VERDICT_LABELS[attempt.verdict]} {Math.round(attempt.score * 100)}%</h2>
      <p>{attempt.message}</p>
      {Object.keys(SUB_SCORE_LABELS).map((name) => (
        <SubScoreBar key={name} label={SUB_SCORE_LABELS[name]} value={attempt.sub_scores[name]} />
      ))}
    </div>
  )
}
