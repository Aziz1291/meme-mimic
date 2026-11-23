# Meme Mimic

A web game: listen to a meme section by section, imitate it with your voice, and get a similarity score. A coach (an AI agent) then explains your results.

> Work in progress: end-of-module project, Machine Learning Appliqué (L3 DSI).

## Requirements

- Docker Desktop (Python and ffmpeg live inside the image: nothing else to install)
- Node.js 22+

## Run it

```bash
# 1. Settings (once): copy the example, then edit it if needed
cp backend/.env.example backend/.env

# 2. Backend (terminal 1): first time or after changing requirements, add --build
docker compose up --build

# 3. Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The API docs are at http://localhost:8000/docs.

## Tests

```bash
docker compose run --rm api pytest -q
```

## Modes

- `INFERENCE_MODE=mock` (default): works offline with fixed answers.
- `INFERENCE_MODE=real`: calls Groq. Needs `GROQ_API_KEY` in `backend/.env`.

## Meme audio

The meme mp3 files are not in this repo (copyright). `backend/data/memes/catalog.json` lists them; put the matching files in `backend/data/memes/` (the clips come from myinstants.com). Tests don't need them: they build fake audio.

## Known limits

- The score measures how similar the **sound** is (timbre, melody, loudness, rhythm), not how funny or well acted the imitation is.
- Sessions are files on disk. Writes are atomic (temp file + rename), but two attempts sent at the exact same moment for the same session could still lose one of them. Fine for a single-player game.
