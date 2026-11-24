"""Playing the game: send an imitation, get the final result, download the mix of your attempts.

Order for an attempt: checks (404/413/415/422) → refusal rules → scorer. The rules always win.
"""

import logging
import time

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app import config, storage
from app.audio import rules
from app.audio.io import AudioError, load_wav, validate_and_convert
from app.audio.mixing import mix
from app.providers.scorers import get_scorer
from app.schemas import AttemptRecord, AttemptResponse, SectionResult, SessionResult, Verdict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["attempts"])

NOT_FINISHED = "The game isn't finished: every section needs a scored attempt."
VERDICT_MESSAGES = {
    Verdict.great: "Great! {percent}% similar.",
    Verdict.good: "Good! {percent}% similar. You can do even better.",
    Verdict.try_again: "{percent}% similar. Listen again and try once more.",
}


def find_section(session_id: str, section_index: int):
    """Returns the session and the section, or raises a 404."""
    try:
        session = storage.load_session(session_id)
    except storage.SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session or section not found.")
    if section_index < 0 or section_index >= len(session.sections):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session or section not found.")
    return session, session.sections[section_index]


def best_attempts(section_count: int, attempts: list[AttemptRecord]):
    """For each section: (best scored attempt, number of attempts). None if a section has
    no scored attempt yet (the game isn't finished)."""
    best = []
    for index in range(section_count):
        section_attempts = [a for a in attempts if a.section_index == index]
        scored = [a for a in section_attempts if a.result.status == "scored"]
        if not scored:
            return None
        best_one = max(scored, key=lambda attempt: attempt.result.score)
        best.append((best_one, len(section_attempts)))
    return best


def build_response(samples, sample_rate, section, section_path, started) -> AttemptResponse:
    """Rules first; the scorer only runs if the recording is usable."""
    scorer = get_scorer(config.SCORER)
    reason = rules.check(samples, sample_rate, section.end_s - section.start_s)
    if reason is not None:
        latency_ms = (time.perf_counter() - started) * 1000
        return AttemptResponse(status="refused", refusal_reason=reason,
                               message=rules.MESSAGES[reason], scorer=scorer.name,
                               latency_ms=latency_ms)
    try:
        score, sub_scores, verdict = scorer.score(section_path, samples, sample_rate)
    except ValueError as error:
        logger.error("scoring failed: %s", error)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Scoring failed. Try again.")
    latency_ms = (time.perf_counter() - started) * 1000
    # Round once, and use that same number everywhere, so the % in the message and the
    # % the page computes from "score" can never disagree (0.9349 vs 0.935).
    score = round(score, 3)
    message = VERDICT_MESSAGES[verdict].format(percent=round(score * 100))
    return AttemptResponse(status="scored", score=score, verdict=verdict,
                           message=message, sub_scores=sub_scores, scorer=scorer.name,
                           latency_ms=latency_ms)


@router.post("/sessions/{session_id}/sections/{section_index}/attempts",
             response_model=AttemptResponse)
def send_attempt(session_id: str, section_index: int, file: UploadFile):
    started = time.perf_counter()  # for the latency measurement (Sprint 4 bonus)
    session, section = find_section(session_id, section_index)
    attempts = storage.load_attempts(session_id)
    # The number comes from the saved attempts, not from a counter in memory.
    previous = [a for a in attempts if a.section_index == section_index]
    attempt_number = len(previous) + 1
    file_name = f"{section_index}_{attempt_number}.wav"
    attempt_path = storage.attempts_dir(session_id) / file_name
    try:
        validate_and_convert(file.file, attempt_path, for_attempt=True)
    except AudioError as error:
        attempt_path.unlink(missing_ok=True)
        raise HTTPException(error.status_code, error.message)

    samples, sample_rate = load_wav(attempt_path)
    section_path = storage.section_audio_path(session_id, section_index)
    result = build_response(samples, sample_rate, section, section_path, started)
    attempts.append(AttemptRecord(section_index=section_index, attempt_number=attempt_number,
                                  file_name=file_name, result=result))
    storage.save_attempts(session_id, attempts)
    return result


def finished_game(session_id: str):
    """Returns (session, best attempts), or raises 404 / 409."""
    try:
        session = storage.load_session(session_id)
    except storage.SessionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    best = best_attempts(len(session.sections), storage.load_attempts(session_id))
    if best is None:
        # 409 Conflict: the request is fine, but the game is not in the right state yet.
        raise HTTPException(status.HTTP_409_CONFLICT, NOT_FINISHED)
    return session, best


@router.get("/sessions/{session_id}/result", response_model=SessionResult)
def get_result(session_id: str):
    session, best = finished_game(session_id)
    sections = []
    total = 0.0
    for index, (attempt, attempt_count) in enumerate(best):
        sections.append(SectionResult(index=index, best_score=attempt.result.score,
                                      verdict=attempt.result.verdict, attempt_count=attempt_count))
        total += attempt.result.score
    total_percent = round(total / len(best) * 100)
    return SessionResult(session_id=session.session_id, total_percent=total_percent,
                         sections=sections)


@router.get("/sessions/{session_id}/mix")
def get_mix(session_id: str):
    session, best = finished_game(session_id)
    folder = storage.attempts_dir(session.session_id)
    wav_paths = []
    for attempt, _ in best:
        wav_paths.append(folder / attempt.file_name)
    output_path = storage.session_dir(session.session_id) / "mix.wav"
    mix(wav_paths, output_path)
    return FileResponse(output_path, media_type="audio/wav", filename="my-imitation.wav")
