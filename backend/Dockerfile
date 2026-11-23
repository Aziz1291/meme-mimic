# Recipe for the backend image: Python 3.12 + ffmpeg + our libraries + our code.
# See docs/plan/docker.md for a line-by-line explanation.

# Start from an official image: Debian Linux + Python 3.12 ("slim" = small)
FROM python:3.12-slim

# No .pyc files, logs appear immediately, numba (used by librosa) can write its cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NUMBA_CACHE_DIR=/tmp/numba_cache

# ffmpeg is a system tool (not a pip package): install it with apt, then clean the apt cache
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements BEFORE code: this layer is cached and only rebuilt when requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The code changes often, so it comes last
COPY . .

EXPOSE 8000

# Production start command. Render sets $PORT; locally it falls back to 8000.
# docker-compose.yml replaces this with a --reload version for development.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
