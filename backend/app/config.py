"""All the app's settings, in one place.

Values come from environment variables (the .env file), with safe defaults.
Every other file imports its settings from here instead of reading .env itself.
"""

import os

from dotenv import load_dotenv

# Reads backend/.env if it exists. In Docker, compose already passes the same values.
load_dotenv()

# "mock" works offline with fixed answers; "real" calls Groq.
# .lower() so that "Mock" or "MOCK" also work.
INFERENCE_MODE = os.getenv("INFERENCE_MODE", "mock").lower()

# Secret: never print it, never return it in a response.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")
