"""The /api/health route: a quick "is everything OK?" check.

Used by the frontend (to show "Backend: ok") and by you when debugging.
"""

import shutil

from fastapi import APIRouter

from app.config import INFERENCE_MODE

# prefix="/api": every route in this file starts with /api (the Vite proxy relies on it)
router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    # shutil.which looks for the program on the system, like typing "which ffmpeg".
    # It returns its path, or None if ffmpeg is not installed.
    ffmpeg_found = shutil.which("ffmpeg") is not None

    # We say WHICH mode we're in, but never anything secret (no key, no paths).
    return {"status": "ok", "mode": INFERENCE_MODE, "ffmpeg": ffmpeg_found}
