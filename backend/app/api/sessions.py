"""Game session routes: start a game (catalog or upload), read it, play a section's audio.

Each route is a plain "def": the work is disk + ffmpeg, so FastAPI runs it in a thread
and the server stays responsive for other players.
"""

import logging

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app import config, storage
from app.api.memes import find_meme
from app.audio.io import AudioError, convert_to_wav, load_wav, validate_and_convert, write_wav
from app.audio.segment import cut_audio, split_into_sections
from app.schemas import Section, SessionResponse, StartSessionRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["sessions"])

NOT_FOUND = "Session or section not found."


def build_session(session_id, source, title, times, subtitles) -> SessionResponse:
    """Cuts original.wav into section files, then saves session.json."""
    folder = storage.session_dir(session_id)
    samples, sample_rate = load_wav(folder / "original.wav")
    sections = []
    for index, (start_s, end_s) in enumerate(times):
        piece = cut_audio(samples, sample_rate, start_s, end_s)
        write_wav(storage.section_audio_path(session_id, index), piece, sample_rate)
        sections.append(Section(
            index=index,
            start_s=start_s,
            end_s=end_s,
            subtitle=subtitles[index],
            audio_url=f"/api/sessions/{session_id}/sections/{index}/audio",
        ))
    session = SessionResponse(
        session_id=session_id, source=source, meme_title=title, sections=sections
    )
    storage.save_session(session)
    return session


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def start_catalog_session(request: StartSessionRequest):
    meme = find_meme(request.meme_id)
    if meme is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown meme.")

    session_id = storage.new_session_id()
    folder = storage.create_session_dir(session_id)
    times = []
    subtitles = []
    for section in meme.sections:
        times.append((section.start_s, section.end_s))
        subtitles.append(section.subtitle)
    try:
        # Catalog files go through ffmpeg too, so every session has the same format.
        convert_to_wav(config.MEMES_DIR / meme.file, folder / "original.wav")
        return build_session(session_id, "catalog", meme.title, times, subtitles)
    except (AudioError, ValueError) as error:
        # This is our catalog's fault, not the player's: log it, send a generic 500.
        logger.error("meme %s is broken: %s", meme.id, error)
        storage.delete_session(session_id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "This meme can't be played.")


@router.post("/sessions/upload", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def start_upload_session(file: UploadFile):
    session_id = storage.new_session_id()
    folder = storage.create_session_dir(session_id)
    try:
        validate_and_convert(file.file, folder / "original.wav")
        samples, sample_rate = load_wav(folder / "original.wav")
        times = split_into_sections(samples, sample_rate)
        subtitles = [None] * len(times)  # no subtitles for uploads (yet)
        return build_session(session_id, "upload", "Your upload", times, subtitles)
    except AudioError as error:
        storage.delete_session(session_id)
        raise HTTPException(error.status_code, error.message)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    try:
        return storage.load_session(session_id)
    except storage.SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)


@router.get("/sessions/{session_id}/sections/{section_index}/audio")
def get_section_audio(session_id: str, section_index: int):
    try:
        session = storage.load_session(session_id)
    except storage.SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    if section_index < 0 or section_index >= len(session.sections):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    path = storage.section_audio_path(session_id, section_index)
    return FileResponse(path, media_type="audio/wav")
