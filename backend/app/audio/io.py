"""The gatekeeper for every audio file that comes in: size, real content, duration, conversion.

Used by the session routes (uploads now, attempts in Sprint 2).
No FastAPI code here: errors are AudioError, and the routes turn them into HTTP responses.
"""

import json
import logging
import subprocess
import tempfile
from http import HTTPStatus
from pathlib import Path

import soundfile

from app import config

logger = logging.getLogger(__name__)


class AudioError(Exception):
    """A problem with an audio file, with the HTTP code and a message safe to show the player."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def save_in_chunks(source_file, target_path: Path, max_bytes: int) -> int:
    """Copies the upload to disk 1 MB at a time, and stops as soon as it's too big."""
    total_bytes = 0
    with open(target_path, "wb") as target:
        while True:
            chunk = source_file.read(config.READ_CHUNK_BYTES)
            if not chunk:
                break
            total_bytes += len(chunk)
            # Checking while reading means a huge file is refused before it fills the disk.
            if total_bytes > max_bytes:
                raise AudioError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "This file is too big.")
            target.write(chunk)
    return total_bytes


def run_tool(arguments: list[str]) -> subprocess.CompletedProcess:
    """Runs ffmpeg or ffprobe safely: a list of arguments, never a shell, always a timeout."""
    try:
        # A list (no shell=True) means a strange file name can't inject a command.
        return subprocess.run(
            arguments, capture_output=True, text=True, timeout=config.FFMPEG_TIMEOUT_SECONDS
        )
    except FileNotFoundError:
        logger.error("%s is not installed", arguments[0])
        raise AudioError(HTTPStatus.SERVICE_UNAVAILABLE, "Audio processing is not available.")
    except subprocess.TimeoutExpired:
        logger.warning("%s took too long", arguments[0])
        raise AudioError(HTTPStatus.UNPROCESSABLE_ENTITY, "This file took too long to process.")


def check_has_audio(path: Path) -> None:
    """Asks ffprobe what's really inside the file. The extension and the header can lie."""
    result = run_tool([
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type",
        "-of", "json", str(path),
    ])
    stream_types = []
    if result.returncode == 0:
        streams = json.loads(result.stdout).get("streams", [])
        for stream in streams:
            stream_types.append(stream.get("codec_type"))
    if "audio" not in stream_types:
        # The technical reason goes to the log, never to the player.
        logger.info("refused upload, ffprobe said: %s", result.stderr.strip()[:200])
        raise AudioError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "This file is not an audio or video file.")


def convert_to_wav(input_path: Path, output_path: Path, max_seconds: float | None = None) -> None:
    """Converts any audio/video to WAV, mono, 16 000 Hz, 16-bit: one format for the whole app."""
    if max_seconds is None:
        max_seconds = config.MAX_UPLOAD_SECONDS
    result = run_tool([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(input_path),
        "-vn",                              # drop the video
        "-ac", "1",                         # mono
        "-ar", str(config.SAMPLE_RATE),     # 16 000 samples per second
        "-sample_fmt", "s16",               # 16-bit
        # Keep only a bit more than the limit: enough to know the file is too long.
        "-t", str(max_seconds + 1),
        str(output_path),
    ])
    if result.returncode != 0:
        logger.warning("ffmpeg failed: %s", result.stderr.strip()[:200])
        raise AudioError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "This audio file could not be read.")


def check_duration(path: Path, min_seconds: float, max_seconds: float) -> float:
    duration = soundfile.info(str(path)).duration
    if duration < min_seconds:
        message = f"This clip is too short (minimum {min_seconds:g} second)."
        raise AudioError(HTTPStatus.UNPROCESSABLE_ENTITY, message)
    if duration > max_seconds:
        message = f"This clip is too long (maximum {max_seconds:g} seconds)."
        raise AudioError(HTTPStatus.UNPROCESSABLE_ENTITY, message)
    return duration


def validate_and_convert(source_file, output_path: Path, for_attempt=False) -> Path:
    """The full check: size (413) → real content (415) → convert → duration (422).

    Uploads (a whole meme) and attempts (one imitation) have different limits.
    """
    # Read config here (not at import), so tests can change the limits.
    if for_attempt:
        max_bytes = config.ATTEMPT_MAX_BYTES
        min_seconds = 0.0  # a too-short attempt is a refusal (rules.py), not an error
        max_seconds = config.ATTEMPT_MAX_SECONDS
    else:
        max_bytes = config.MAX_UPLOAD_BYTES
        min_seconds = config.MIN_UPLOAD_SECONDS
        max_seconds = config.MAX_UPLOAD_SECONDS
    # The temporary folder and everything in it is deleted when the "with" block ends,
    # even if an error is raised inside it.
    with tempfile.TemporaryDirectory() as temp_folder:
        raw_path = Path(temp_folder) / "upload"
        save_in_chunks(source_file, raw_path, max_bytes)
        check_has_audio(raw_path)
        convert_to_wav(raw_path, output_path, max_seconds)
    check_duration(output_path, min_seconds, max_seconds)
    return output_path


def load_wav(path: Path):
    """Returns (samples as a numpy array, sample rate)."""
    samples, sample_rate = soundfile.read(str(path), dtype="float32")
    return samples, sample_rate


def write_wav(path: Path, samples, sample_rate: int) -> None:
    soundfile.write(str(path), samples, sample_rate, subtype="PCM_16")
