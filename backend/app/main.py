"""Creates the FastAPI app and plugs in every group of routes.

uvicorn starts the server with: uvicorn app.main:app
("in the file app/main.py, use the variable called app").
"""

import logging

from fastapi import FastAPI

from app.api import health, memes, sessions

# Show our own log messages (ffmpeg problems, broken memes) in the docker logs.
logging.basicConfig(level=logging.INFO)

# Check catalog.json right now: a typo stops the server at startup with a clear error,
# instead of breaking in the middle of a game.
memes.load_catalog()

app = FastAPI(title="Meme Mimic", version="0.1.0")

# Each file in app/api/ has its own router; we add them here one by one.
app.include_router(health.router)
app.include_router(memes.router)
app.include_router(sessions.router)
