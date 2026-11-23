"""Tests for audio/segment.py, with fake audio built from beeps and silence."""

import numpy as np
import pytest

from app.audio.io import AudioError
from app.audio.segment import cut_audio, split_into_sections
from tests.conftest import make_silence, make_tone

SAMPLE_RATE = 16000


def test_two_words_with_a_pause_give_two_sections():
    samples = np.concatenate([make_tone(0.8), make_silence(0.5), make_tone(1.2)])
    sections = split_into_sections(samples, SAMPLE_RATE)
    assert len(sections) == 2
    first_start, first_end = sections[0]
    second_start, second_end = sections[1]
    assert abs(first_end - 0.8) < 0.15
    assert abs(second_start - 1.3) < 0.15


def test_five_seconds_of_sound_give_about_three_sections():
    sections = split_into_sections(make_tone(5.0), SAMPLE_RATE)
    assert len(sections) == 3
    for start, end in sections:
        assert end - start <= 2.0


def test_silence_only_is_refused():
    with pytest.raises(AudioError) as error:
        split_into_sections(make_silence(3.0), SAMPLE_RATE)
    assert error.value.status_code == 422


def test_short_pause_is_not_a_cut():
    # 0.1 s is a breath, not the end of a word.
    samples = np.concatenate([make_tone(0.7), make_silence(0.1), make_tone(0.7)])
    assert len(split_into_sections(samples, SAMPLE_RATE)) == 1


def test_cut_audio_returns_the_right_length():
    piece = cut_audio(make_tone(3.0), SAMPLE_RATE, 1.0, 2.5)
    assert len(piece) == int(1.5 * SAMPLE_RATE)


def test_cut_audio_past_the_end_is_an_error():
    with pytest.raises(ValueError):
        cut_audio(make_tone(1.0), SAMPLE_RATE, 0.5, 3.0)
