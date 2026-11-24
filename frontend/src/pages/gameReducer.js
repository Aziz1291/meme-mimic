// The Play page as a "state machine": the page is always in exactly ONE phase.
// The reducer is a plain function: (current state, event) → new state.
// Events that make no sense in the current phase are ignored, so impossible
// situations (like recording while a score is being computed) can't happen.
//
//  waiting ──(Play)──► listening ──(audio ended)──► ready ──(recorded)──► scoring
//     ▲                                               ▲                     │
//     │                                            (Retry)              (response)
//  (Next)                                             │                     ▼
//     └───────────────────────────────────────── show_score ◄───────────────┘

export const initialState = {
  phase: 'loading', // loading | error | waiting | listening | ready | scoring | show_score
  session: null,
  sectionIndex: 0,
  attempt: null, // the backend's answer for the last recording
  attemptUrl: null, // a local address for the last recording, to draw its waveform
  error: '',
}

export function gameReducer(state, action) {
  switch (action.type) {
    case 'loaded':
      return { ...state, phase: 'waiting', session: action.session, sectionIndex: action.sectionIndex }

    case 'load_failed':
      return { ...state, phase: 'error', error: action.error }

    case 'play_started':
      // You can listen again at any time, except while recording is being scored.
      if (state.phase === 'scoring') {
        return state
      }
      return { ...state, phase: 'listening', error: '' }

    case 'play_ended':
      if (state.phase !== 'listening') {
        return state
      }
      // After a score, stay on the score card; otherwise the player can now record.
      return { ...state, phase: state.attempt ? 'show_score' : 'ready' }

    case 'recorded':
      if (state.phase !== 'ready' && state.phase !== 'show_score') {
        return state
      }
      return { ...state, phase: 'scoring', attempt: null, attemptUrl: action.attemptUrl, error: '' }

    case 'scored':
      return { ...state, phase: 'show_score', attempt: action.attempt }

    case 'send_failed':
      return { ...state, phase: 'ready', attemptUrl: null, error: action.error }

    case 'retry':
      return { ...state, phase: 'ready', attempt: null, attemptUrl: null }

    case 'next':
      return { ...state, phase: 'waiting', sectionIndex: state.sectionIndex + 1,
               attempt: null, attemptUrl: null, error: '' }

    default:
      return state
  }
}
