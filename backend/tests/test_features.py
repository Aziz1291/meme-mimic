"""Tests for audio/features.py with fake signals."""

import numpy as np

from app.audio import features
from tests.conftest import make_chirp, make_noise, make_silence, make_tone

SAMPLE_RATE = 16000


def test_trim_removes_silence_around_the_sound():
    samples = np.concatenate([make_silence(1.0), make_tone(1.0), make_silence(1.0)])
    trimmed = features.trim(samples)
    assert abs(len(trimmed) / SAMPLE_RATE - 1.0) < 0.15


def test_rising_chirp_gives_a_rising_pitch_curve():
    curve = features.pitch_semitones(make_chirp(1.5, 200, 400), SAMPLE_RATE)
    assert len(curve) == 50
    # 200 Hz → 400 Hz is one octave = 12 semitones.
    assert curve[-1] - curve[0] > 9


def test_noise_has_no_melody():
    assert features.pitch_semitones(make_noise(1.5), SAMPLE_RATE) is None


def test_energy_curve_has_50_points_between_0_and_1():
    curve = features.energy_envelope(make_tone(1.0))
    assert len(curve) == 50
    assert curve.min() >= 0 and curve.max() <= 1


def test_mfcc_is_normalized():
    matrix = features.mfcc(make_chirp(1.0, 200, 400), SAMPLE_RATE)
    assert matrix.shape[0] == 13
    assert np.allclose(matrix.mean(axis=1), 0, atol=1e-6)


def test_features_cache_round_trip(tmp_path):
    original = features.extract(make_tone(1.0), SAMPLE_RATE)
    features.save_features(tmp_path / "f.npz", original)
    loaded = features.load_features(tmp_path / "f.npz")
    assert np.allclose(loaded["mfcc"], original["mfcc"])
    assert loaded["duration"] == original["duration"]


def test_cache_keeps_no_melody_as_none(tmp_path):
    noise = features.extract(make_noise(1.0), SAMPLE_RATE)
    features.save_features(tmp_path / "n.npz", noise)
    assert features.load_features(tmp_path / "n.npz")["pitch"] is None
