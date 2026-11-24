# Meme Mimic 🎤

A web game: pick a meme, listen to it **piece by piece**, imitate each piece with your voice, and get a **similarity score**. At the end you hear all your imitations stitched together, and a **coach** (an AI agent with tools) explains your results.

Two "models" work together:
- **The scorer** (signal processing with librosa): compares your voice to the original on 4 things: timbre, melody, loudness, rhythm.
- **The coach** (an LLM on Groq, or an offline mock): reads your scores through 5 tools and gives advice. It can **propose** a retry, but only your click confirms it.

> End-of-module project, Machine Learning Appliqué, L3 DSI (ISET Nabeul).

---

## Requirements

- **Docker Desktop** (Python 3.12 and ffmpeg live inside the image: nothing else to install for the backend)
- **Node.js 22+** (for the frontend)
- Optional: a free **Groq API key** (console.groq.com), only for the real coach. Everything works offline without it.

## Install

```powershell
git clone https://github.com/Aziz1291/meme-mimic.git
cd meme-mimic

# 1. Settings: copy the example file (Linux/macOS: cp backend/.env.example backend/.env)
Copy-Item backend/.env.example backend/.env

# 2. Backend: build the image (first time, or after changing requirements.txt)
docker compose build

# 3. Frontend
cd frontend
npm install
cd ..
```

### Meme audio

The meme clips are **not in the repo** (copyright). `backend/data/memes/catalog.json` lists them. Download the 3 files from myinstants.com into `backend/data/memes/`:

```powershell
cd backend/data/memes
curl.exe -L -o emotional_damage.mp3 https://www.myinstants.com/media/sounds/emotional-damage-steven-he.mp3
curl.exe -L -o why_are_you_running.mp3 https://www.myinstants.com/media/sounds/why-are.mp3
curl.exe -L -o phone_ringing.mp3 https://www.myinstants.com/media/sounds/yo-phone-is-ringing-your-phone-was-ringing.mp3
cd ../../..
```

Without them the game still runs: you can **upload your own clip** on the home page. The tests don't need them either: they build fake audio.

## Run

```powershell
# Terminal 1: backend (API on http://localhost:8000, docs on http://localhost:8000/docs)
docker compose up

# Terminal 2: frontend
cd frontend
npm run dev
```

Open **http://localhost:5173**. Use Chrome or Firefox, allow the microphone, and wear headphones.

## Modes

In `backend/.env`:

| Setting | Values |
|---|---|
| `INFERENCE_MODE` | `mock` (default): the coach is a scripted offline mock · `real`: the coach calls Groq |
| `GROQ_API_KEY` | your key, only for `real`. **Never commit it** (`.env` is gitignored). |
| `LLM_MODEL` | `openai/gpt-oss-20b` (default, chosen by measurement) or `qwen/qwen3.8-27b` |
| `SCORER` | `signal` (default, the real scorer) · `mock` (always 80%, to test the game quickly) |

`real` without a key falls back to the mock and **says so** (the response has `"degraded": true` and the chat shows a "mock" badge). After editing `.env`, run `docker compose up -d` to reload it.

## Tests

```powershell
docker compose run --rm api pytest -q
```

124 tests, about 17 s, all **offline**: the tests force mock mode even if your `.env` says `real`.

## Measurements

All scripts run inside Docker and save their output (`.txt` + `.json`) in `backend/eval/results/`. The protocol (`backend/eval/PROTOCOL.md`) was committed before any result.

| What | Command |
|---|---|
| Coach benchmark (20 tasks, frozen game) | `docker compose exec api python -m eval.evaluate_agent openai/gpt-oss-20b` |
| Attempt latency (first call + 20) | `docker compose exec api python -m eval.latency` |
| Scoring vs human labels: export game attempts | `docker compose run --rm api python -m eval.export_attempts` |
| … then, after labeling `eval/labels.csv` blind | `docker compose run --rm api python -m eval.split`, then `… -m eval.calibrate` (dev set) |
| … final evaluation on the test set | `docker compose run --rm api python -m eval.evaluate_scoring signal-v1` (and `signal-no-melody`) |
| … which stage failed | `docker compose run --rm api python -m eval.diagnose signal-v1` |

## Results (so far)

| Measurement | Result |
|---|---|
| **Coach, 2 models × 2 runs** | `gpt-oss-20b`: 20/20 and 20/20 · `qwen3.8-27b`: 20/20 and 20/20. **0 unrequested actions.** No measurable difference on success (the benchmark is saturated), but gpt-oss is about 4× faster (median ≈ 640 ms vs ≈ 2 700 ms), and qwen sometimes writes invalid tool names. Details: `eval/results/agent_comparison_2026-11-24.md`. |
| **Attempt latency** (i7-13620H, Docker) | first call 1.4 s (feature cache + warm-up), then min 213 · median 226 · max 273 ms |
| **Scoring vs humans** (macro-F1, refusals, `signal-v1` vs `signal-no-melody`) | *Pending: the recordings and blind labels are being collected.* |

## Architecture

```
 BROWSER (React + Vite, port 5173)
   Home: pick / upload → Play: listen, bars, record → Results: %, mix, coach chat
        │  fetch("/api/...")  (the Vite proxy forwards to port 8000)
        ▼
 BACKEND (FastAPI in Docker, port 8000)
   1. Pydantic checks every request ................ 422
   2. audio/io.py: size, real content, ffmpeg ...... 413 / 415 / 422
   3. audio/segment.py: cut uploads at the pauses
   4. audio/rules.py: refuse silent / short / loud / noisy / long recordings ← the app decides
   5. audio/features.py + scoring.py: MFCC + DTW, relative pitch, energy, duration
   6. agent/: coach loop, 5 tools, max_tours = 5, retry = proposal only
        │                     │                        │
   storage/ (disk)        ffmpeg (in the image)    LLM: MockLLM (offline) | GroqLLM (key in .env)
```

```
backend/app/   main.py · config.py (every limit and threshold) · schemas.py (the contract) · storage.py
               api/ (health, memes, sessions, attempts, coach) · audio/ · providers/ · agent/
backend/eval/  PROTOCOL.md · metrics.py · scripts above · fixtures/ · results/ (deliverables)
frontend/src/  api.js (every fetch) · pages/ (Home, Play + gameReducer, Results) · components/
```

## Limitations

- **Signal similarity ≠ human judgment.** The score compares the sound (timbre, melody, loudness, rhythm), not how funny or well acted an imitation is.
- **Timbre is sensitive to the voice's pitch:** in a test, a section shifted 5 semitones lower scored as badly as an unrelated meme. Melody uses relative pitch, but timbre doesn't. Being measured on real voices.
- **Few speakers:** the scoring evaluation uses the voices we could collect; results only hold for voices like those.
- **The noise rule** refuses recordings with no quiet moment at all (continuous sound): watch for false "too noisy" refusals.
- **Single-player storage:** sessions are files on disk. Writes are atomic, but two attempts sent at the exact same moment for one session could lose one.
- **The coach benchmark is saturated** (both models 20/20): it proves correct behavior, but it can't rank the models on quality.
- The mic only works on `localhost` or `https`.

## Credits

- Meme clips: [myinstants.com](https://www.myinstants.com) (not redistributed).
- Libraries: FastAPI, Pydantic, librosa, NumPy, SoundFile, ffmpeg, Groq SDK, pytest, React, React Router, Vite, wavesurfer.js.
