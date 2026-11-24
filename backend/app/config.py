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

# Default chosen by measurement: same benchmark success as qwen, 4x faster, no invalid
# tool calls (see eval/results/agent_comparison_2026-11-24.md).
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

# --- The coach agent ---
COACH_MAX_TOURS = 5  # model calls per question, at most (then a polite fallback)
COACH_HISTORY_TURNS = 10  # only the last 10 chat messages are sent (cost, token limits)
LLM_TEMPERATURE = 0.0  # always the same answer for the same question (reproducible)
LLM_RETRIES = 2  # on a 429 "too many requests", retry twice...
LLM_RETRY_WAIT_SECONDS = 2.0  # ...waiting a bit longer each time

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

# --- Attempts (the player's imitations) ---
ATTEMPT_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
ATTEMPT_MAX_SECONDS = 10.0
# "signal" = the real scorer; "mock" = a fixed score, for fast API tests.
SCORER = os.getenv("SCORER", "signal").lower()
MIX_GAP_SECONDS = 0.2  # silence between sections in the final mix

# --- Features (features.py). Same settings for the original and the attempt. ---
HOP_LENGTH = 320  # one analysis frame every 20 ms at 16 000 Hz
N_MFCC = 13
# 0 = keep all 13 coefficients (the plan). 1 = drop c0 (overall loudness).
# Sprint 2 found the timbre score is very sensitive to the voice's pitch: a candidate for
# the Sprint 4 "change one variable" comparison.
MFCC_FIRST_COEFFICIENT = 0
CURVE_POINTS = 50  # pitch and energy curves are resampled to 50 points
TRIM_TOP_DB = 30
PITCH_MIN_HZ = 65
PITCH_MAX_HZ = 1000
MIN_VOICED_RATIO = 0.2  # below this, the sound has no melody to compare

# --- Refusal rules (rules.py) ---
# Starting guesses. Sprint 4 justifies them with measurements.
SILENT_DB = -45.0  # loudest frame quieter than this → silent
MIN_ATTEMPT_SECONDS = 0.3  # after trimming silence
CLIP_LEVEL = 0.99  # a sample this close to the max is distorted
MAX_CLIPPED_SHARE = 0.01  # more than 1% distorted samples → too loud
MIN_DYNAMIC_RANGE_DB = 10.0  # loud parts vs quiet parts; less → too noisy
MAX_LENGTH_FACTOR = 3.0  # attempt longer than 3 × the section + 1 s → too long
MAX_LENGTH_EXTRA_SECONDS = 1.0

# --- Scoring (scoring.py) ---
WEIGHTS = {"timbre": 0.40, "melody": 0.25, "loudness": 0.20, "rhythm": 0.15}
# Timbre calibration: typical DTW cost of a good imitation vs of two unrelated sounds.
# Measured on the catalog memes (see the Sprint 2 notes). Sprint 4 re-measures them
# with real imitations. BAD = median cost between sections of different memes (0.76).
# GOOD = a guess between a slowed-down copy (0.07) and a copy 3 semitones higher (0.49).
TIMBRE_COST_GOOD = 0.30
TIMBRE_COST_BAD = 0.76
MELODY_MAX_DIFF_SEMITONES = 6.0  # 6 semitones apart on average → melody score 0
LOUDNESS_MAX_DIFF = 0.5
T_GREAT = 0.75
T_GOOD = 0.50
