"""Saves and loads game sessions on disk.

Each session is a folder: storage/sessions/<uuid>/ with session.json, original.wav, sections/0.wav...
Used by the session routes. Disk (not a Python dict) so sessions survive server restarts.
"""

import json
import os
import shutil
import uuid
from pathlib import Path

from app import config
from app.schemas import AttemptRecord, SessionResponse


class SessionNotFound(Exception):
    """The session id is invalid or doesn't exist. Routes turn this into a 404."""


def new_session_id() -> str:
    # uuid4 is random: nobody can guess another player's session id.
    return str(uuid.uuid4())


def session_dir(session_id: str) -> Path:
    """Returns the folder of a session, after checking the id is a real uuid."""
    # The id comes from the URL, so the user controls it. Something like "../../etc"
    # would point outside our folder (path traversal). Parsing it as a uuid blocks that.
    try:
        clean_id = str(uuid.UUID(session_id))
    except ValueError:
        raise SessionNotFound(session_id)
    return Path(config.STORAGE_DIR) / clean_id


def create_session_dir(session_id: str) -> Path:
    folder = session_dir(session_id)
    (folder / "sections").mkdir(parents=True, exist_ok=True)
    return folder


def delete_session(session_id: str) -> None:
    """Removes a half-created session (for example when an upload is refused)."""
    folder = session_dir(session_id)
    shutil.rmtree(folder, ignore_errors=True)


def write_atomically(path: Path, text: str) -> None:
    """Writes to a temporary file, then renames it. A rename is instant, so a reader never
    sees a half-written file, even if two requests arrive at the same time."""
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(text, encoding="utf-8")
    os.replace(temporary_path, path)


def save_session(session: SessionResponse) -> None:
    folder = session_dir(session.session_id)
    write_atomically(folder / "session.json", session.model_dump_json(indent=2))


def load_session(session_id: str) -> SessionResponse:
    path = session_dir(session_id) / "session.json"
    if not path.exists():
        raise SessionNotFound(session_id)
    json_text = path.read_text(encoding="utf-8")
    return SessionResponse.model_validate_json(json_text)


def section_audio_path(session_id: str, section_index: int) -> Path:
    return session_dir(session_id) / "sections" / f"{section_index}.wav"


# --- Attempts: attempts/<section>_<number>.wav + one attempts.json list per session ---

def attempts_dir(session_id: str) -> Path:
    folder = session_dir(session_id) / "attempts"
    folder.mkdir(exist_ok=True)
    return folder


def load_attempts(session_id: str) -> list[AttemptRecord]:
    path = session_dir(session_id) / "attempts.json"
    if not path.exists():
        return []
    attempts = []
    for raw_attempt in json.loads(path.read_text(encoding="utf-8")):
        attempts.append(AttemptRecord.model_validate(raw_attempt))
    return attempts


def save_attempts(session_id: str, attempts: list[AttemptRecord]) -> None:
    raw_attempts = []
    for attempt in attempts:
        raw_attempts.append(attempt.model_dump(mode="json"))
    path = session_dir(session_id) / "attempts.json"
    write_atomically(path, json.dumps(raw_attempts, indent=2))
