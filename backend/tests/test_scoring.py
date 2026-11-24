"""Tests for audio/scoring.py with fake signals (tones, chirps, noise)."""

import math

import numpy as np
import pytest

from app.audio import features, scoring
from app.schemas import SubScores, Verdict
from tests.conftest import make_chirp, make_noise, make_tone

SAMPLE_RATE = 16000


def compare(original_samples, attempt_samples):
    original = features.extract(original_samples, SAMPLE_RATE)
    attempt = features.extract(attempt_samples, SAMPLE_RATE)
    return scoring.score(original, attempt)


def assert_valid(score, sub_scores):
    """Every score must be a real number between 0 and 1."""
    values = [score, sub_scores.timbre, sub_scores.loudness, sub_scores.rhythm]
    if sub_scores.melody is not None:
        values.append(sub_scores.melody)
    for value in values:
        assert math.isfinite(value) and 0 <= value <= 1


def test_sound_against_itself_is_great():
    chirp = make_chirp(1.5, 200, 350)
    score, sub_scores, verdict = compare(chirp, chirp)
    assert score >= 0.95
    assert verdict == Verdict.great
    assert_valid(score, sub_scores)


def test_rising_vs_falling_melody_is_low():
    score, sub_scores, _ = compare(make_chirp(1.5, 200, 400), make_chirp(1.5, 400, 200))
    assert sub_scores.melody < 0.4
    assert_valid(score, sub_scores)


def test_tone_vs_noise_has_low_timbre():
    score, sub_scores, _ = compare(make_chirp(1.5, 200, 350), make_noise(1.5))
    assert sub_scores.timbre < 0.5
    assert_valid(score, sub_scores)


def test_one_second_vs_two_seconds_rhythm_is_half():
    _, sub_scores, _ = compare(make_tone(1.0), make_tone(2.0))
    assert sub_scores.rhythm == pytest.approx(0.5, abs=0.05)


def test_noise_has_no_melody_but_still_a_valid_score():
    score, sub_scores, _ = compare(make_noise(1.5), make_noise(1.5) * 0.8)
    assert sub_scores.melody is None
    assert_valid(score, sub_scores)


def test_missing_melody_shares_its_weight():
    # With melody None, the 3 other scores all at 1.0 must still give exactly 1.0.
    sub_scores = SubScores(timbre=1.0, melody=None, loudness=1.0, rhythm=1.0)
    assert scoring.weighted_score(sub_scores) == pytest.approx(1.0)


def test_verdict_matches_the_rounded_score(monkeypatch):
    # A raw 0.4996 is shown as 50%: it must also be judged "good", not "try again".
    monkeypatch.setattr(scoring, "weighted_score", lambda sub_scores, use_melody=True: 0.4996)
    original = features.extract(make_chirp(1.0, 200, 300), SAMPLE_RATE)
    score, _, verdict = scoring.score(original, original)
    assert score == 0.5 and verdict == Verdict.good


def test_verdict_thresholds():
    assert scoring.verdict_for(0.9) == Verdict.great
    assert scoring.verdict_for(0.6) == Verdict.good
    assert scoring.verdict_for(0.2) == Verdict.try_again


def test_timbre_cost_maps_to_0_1():
    assert scoring.timbre_score(0.0) == 1.0
    assert scoring.timbre_score(5.0) == 0.0
    assert 0 < scoring.timbre_score(0.5) < 1


def test_nan_never_reaches_the_player():
    original = features.extract(make_tone(1.0), SAMPLE_RATE)
    broken = dict(original)
    broken["energy"] = np.full(50, np.nan)
    with pytest.raises(ValueError):
        scoring.score(original, broken)
