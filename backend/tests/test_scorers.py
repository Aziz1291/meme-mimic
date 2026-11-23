"""Tests for providers/scorers.py."""

import pytest

from app.audio.io import write_wav
from app.providers.scorers import MockScorer, SignalScorer, get_scorer
from app.schemas import Verdict
from tests.conftest import make_chirp

SAMPLE_RATE = 16000


def test_get_scorer_by_name():
    assert get_scorer("signal").name == "signal-v1"
    assert get_scorer("signal-no-melody").name == "signal-no-melody"
    assert get_scorer("mock").name == "mock"
    with pytest.raises(ValueError):
        get_scorer("magic")


def test_mock_scorer_is_fixed():
    score, _, verdict = MockScorer().score(None, None, SAMPLE_RATE)
    assert score == 0.8 and verdict == Verdict.great


def test_signal_scorer_caches_the_original(tmp_path):
    section_path = tmp_path / "0.wav"
    chirp = make_chirp(1.5, 200, 350)
    write_wav(section_path, chirp, SAMPLE_RATE)
    score, _, _ = SignalScorer().score(section_path, chirp, SAMPLE_RATE)
    assert (tmp_path / "0.npz").exists()
    assert score > 0.9
