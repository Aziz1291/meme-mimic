"""Turns a session + its attempts into the simple numbers the coach's tools read.

Sections are numbered from 1 here ("piece 1", like on screen), because that's how the
player talks. The API's section_index starts at 0; the conversion happens in ONE place.
"""

from app.schemas import AttemptRecord, SessionResponse


def to_percent(value) -> int | None:
    if value is None:
        return None
    return round(value * 100)


def build_game(session: SessionResponse, attempts: list[AttemptRecord]) -> dict:
    """{"sections": [{"section_number", "subtitle", "tries": [scored attempts, in order]}]}"""
    sections = []
    for section in session.sections:
        tries = []
        for attempt in attempts:
            if attempt.section_index == section.index and attempt.result.status == "scored":
                sub_scores = attempt.result.sub_scores.model_dump()
                tries.append({
                    "percent": to_percent(attempt.result.score),
                    "verdict": attempt.result.verdict.value,
                    "sub_scores_percent": {name: to_percent(value)
                                           for name, value in sub_scores.items()},
                })
        sections.append({"section_number": section.index + 1,
                         "subtitle": section.subtitle, "tries": tries})
    return {"meme_title": session.meme_title, "sections": sections}
