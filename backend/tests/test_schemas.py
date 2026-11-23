"""Tests for the contract in schemas.py."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    AttemptResponse,
    CatalogMeme,
    CatalogSection,
    StartSessionRequest,
    SubScores,
)


def test_empty_meme_id_is_refused():
    with pytest.raises(ValidationError):
        StartSessionRequest(meme_id="")


def test_section_must_end_after_it_starts():
    with pytest.raises(ValidationError):
        CatalogSection(start_s=2.0, end_s=1.0)


def test_catalog_file_name_cannot_leave_the_folder():
    with pytest.raises(ValidationError):
        CatalogMeme(
            id="bad",
            title="Bad",
            file="../../secret.wav",
            sections=[{"start_s": 0, "end_s": 1}],
        )


def test_valid_catalog_meme():
    meme = CatalogMeme(
        id="meme_01",
        title="Test",
        file="meme_01.wav",
        sections=[{"start_s": 0, "end_s": 1.2, "subtitle": "hello"}],
    )
    assert meme.sections[0].subtitle == "hello"


def test_score_above_one_is_refused():
    with pytest.raises(ValidationError):
        SubScores(timbre=1.3, melody=None, loudness=0.5, rhythm=0.5)


def test_unknown_refusal_reason_is_refused():
    with pytest.raises(ValidationError):
        AttemptResponse(
            status="refused", refusal_reason="i_dont_like_it", message="x", scorer="mock", latency_ms=1
        )
