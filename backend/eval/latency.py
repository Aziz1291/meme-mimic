"""Measures how long the attempt endpoint takes: first call, then min / median / max of 20.

Why not the average? One slow call pulls the average up and hides that most calls are fast.
The median shows the typical case, the max the worst case. The first call is reported
apart: it computes and caches the original's features (and librosa warms up).

Usage (inside Docker, with the server running):  python -m eval.latency
Saves eval/results/latency_<date>.txt and .json.
"""

import io
import os
import platform
import statistics
import time
from datetime import date

import httpx
import numpy as np
import soundfile

from app import storage
from eval.common import save_result

SERVER = "http://localhost:8000"
MEME_ID = "emotional_damage"
REPEATS = 20


def machine_description() -> str:
    memory = "unknown"
    cpu = platform.machine()
    try:
        with open("/proc/cpuinfo") as file:
            for line in file:
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()  # e.g. "AMD Ryzen 7 5800H ..."
                    break
        with open("/proc/meminfo") as file:
            first_line = file.readline()  # "MemTotal:  16303000 kB"
        memory = f"{int(first_line.split()[1]) / 1024 / 1024:.1f} GB"
    except OSError:
        pass
    return (f"{cpu}, {os.cpu_count()} CPUs, {memory} RAM, "
            f"Python {platform.python_version()} (inside Docker: the numbers include it)")


def attempt_file(client: httpx.Client, audio_url: str) -> bytes:
    """The section's own audio with silence around it: a valid, always-scored attempt."""
    samples, sample_rate = soundfile.read(io.BytesIO(client.get(audio_url).content))
    pad = np.zeros(int(0.3 * sample_rate))
    buffer = io.BytesIO()
    soundfile.write(buffer, np.concatenate([pad, samples, pad]), sample_rate, format="WAV")
    return buffer.getvalue()


def timed_call(client: httpx.Client, url: str, file_bytes: bytes) -> float:
    started = time.perf_counter()
    response = client.post(url, files={"file": ("attempt.wav", file_bytes)})
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    return elapsed_ms


def measure():
    with httpx.Client(base_url=SERVER, timeout=60) as client:
        session = client.post("/api/sessions", json={"meme_id": MEME_ID}).json()
        section = session["sections"][0]
        file_bytes = attempt_file(client, section["audio_url"])
        url = f"/api/sessions/{session['session_id']}/sections/0/attempts"
        first_ms = timed_call(client, url, file_bytes)
        timings = [timed_call(client, url, file_bytes) for _ in range(REPEATS)]
    # This was a fake game: delete it, so export_attempts never mistakes it for real data.
    storage.delete_session(session["session_id"])

    lines = [f"=== Latency of POST .../attempts ({date.today()}) ===",
             f"machine : {machine_description()}",
             f"meme    : {MEME_ID}, section 0 ({section['end_s'] - section['start_s']:.2f} s), "
             f"scorer from config",
             "",
             f"first call (cache + warm-up): {first_ms:.0f} ms",
             f"next {REPEATS} calls: min {min(timings):.0f} ms · median {statistics.median(timings):.0f} ms"
             f" · max {max(timings):.0f} ms"]
    numbers = {"first_ms": first_ms, "timings_ms": timings, "min_ms": min(timings),
               "median_ms": statistics.median(timings), "max_ms": max(timings),
               "machine": machine_description()}
    text = "\n".join(lines)
    save_result(f"latency_{date.today()}", text, numbers)
    return text


if __name__ == "__main__":
    print(measure())
