"""Creates the FastAPI app and plugs in every group of routes.

uvicorn starts the server with: uvicorn app.main:app
("in the file app/main.py, use the variable called app").
"""

from fastapi import FastAPI

from app.api import health

app = FastAPI(title="Meme Mimic", version="0.1.0")

# Each file in app/api/ has its own router; we add them here one by one.
app.include_router(health.router)
