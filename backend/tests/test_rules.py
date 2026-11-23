"""Tests for audio/rules.py: each rule has a signal that triggers it."""

import numpy as np

from app.audio.rules import check
from app.schemas import RefusalReason
from tests.conftest import make_noise, make_silence, make_tone

SAMPLE_RATE = 16000


def with_pauses(sound):
    """Real recordings have a bit of silence before and after the voice."""
    return np.concatenate([make_silence(0.3), sound, make_silence(0.3)])


def test_good_recording_is_accepted():
    assert check(with_pauses(make_tone(1.0)), SAMPLE_RATE, section_seconds=1.0) is None


def test_all_zeros_is_silent():
    assert check(make_silence(1.0), SAMPLE_RATE, 1.0) == RefusalReason.silent


def test_empty_recording_is_silent():
    assert check(np.array([]), SAMPLE_RATE, 1.0) == RefusalReason.silent


def test_very_quiet_recording_is_silent():
    assert check(with_pauses(0.001 * make_tone(1.0)), SAMPLE_RATE, 1.0) == RefusalReason.silent


def test_tenth_of_a_second_is_too_short():
    assert check(with_pauses(make_tone(0.1)), SAMPLE_RATE, 1.0) == RefusalReason.too_short


def test_full_volume_square_wave_is_too_loud():
    square = np.sign(make_tone(1.0))  # only -1 and +1: every sample is at the maximum
    assert check(with_pauses(square), SAMPLE_RATE, 1.0) == RefusalReason.too_loud


def test_noise_everywhere_is_too_noisy():
    # A voice drowned in constant noise: no quiet frames at all.
    noisy = make_tone(1.5) * 0.5 + make_noise(1.5)
    assert check(noisy, SAMPLE_RATE, 1.5) == RefusalReason.too_noisy


def test_five_seconds_for_a_one_second_section_is_too_long():
    # Pauses between "words": 5 s of non-stop sound would look like noise (see too_noisy).
    word = np.concatenate([make_tone(1.0), make_silence(0.3)])
    samples = with_pauses(np.concatenate([word, word, word, word, word]))
    assert check(samples, SAMPLE_RATE, 1.0) == RefusalReason.too_long
