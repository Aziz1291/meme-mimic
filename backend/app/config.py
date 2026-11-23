"""All the app's settings, in one place.

Values come from environment variables (the .env file), with safe defaults.
Every other file imports its settings from here instead of reading .env itself.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Reads backend/.env if it exists. In Docker, compose already passes the same values.
load_dotenv()

# "mock" works offline with fixed answers; "real" calls Groq.
# .lower() so that "Mock" or "MOCK" also work.
INFERENCE_MODE = os.getenv("INFERENCE_MODE", "mock").lower()

# Secret: never print it, never return it in a response.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")

# --- Folders ---
# backend/ is two levels above this file (backend/app/config.py).
BACKEND_DIR = Path(__file__).resolve().parent.parent
MEMES_DIR = BACKEND_DIR / "data" / "memes"
CATALOG_PATH = MEMES_DIR / "catalog.json"
# One sub-folder per game session. Tests point this to a temporary folder.
STORAGE_DIR = BACKEND_DIR / "storage" / "sessions"

# --- Upload limits ---
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_UPLOAD_SECONDS = 1.0
MAX_UPLOAD_SECONDS = 20.0
READ_CHUNK_BYTES = 1024 * 1024  # read uploads 1 MB at a time
FFMPEG_TIMEOUT_SECONDS = 30

# --- Audio format used everywhere after conversion ---
SAMPLE_RATE = 16000  # 16 000 samples per second, mono

# --- Automatic cutting of uploads (segment.py) ---
SILENCE_TOP_DB = 30  # quieter than (loudest - 30 dB) counts as silence
SILENCE_PEAK = 0.01  # if the loudest sample is below this, the file is silent
MERGE_GAP_SECONDS = 0.25  # a pause shorter than this is a breath, not a cut
MIN_SECTION_SECONDS = 0.5
MAX_SECTION_SECONDS = 2.0
TARGET_SECTION_SECONDS = 1.5
MAX_SECTIONS = 10
