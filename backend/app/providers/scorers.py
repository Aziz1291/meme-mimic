"""Scorers: the real one (signal processing) and a mock one (fixed score, for fast tests).

Same idea as MockProvider / HfProvider in TP1: same method, same return type,
so the route doesn't know which one it's using. get_scorer() picks one by name.
"""

from pathlib import Path

from app.audio import features, scoring
from app.audio.io import load_wav
from app.schemas import SubScores, Verdict


class SignalScorer:
    """Compares the attempt to the original with MFCC, pitch, energy and duration."""

    def __init__(self, use_melody=True):
        self.use_melody = use_melody
        # The name is saved with every attempt, so we always know which scorer gave a score.
        if use_melody:
            self.name = "signal-v1"
        else:
            self.name = "signal-no-melody"

    def original_features(self, section_wav_path: Path) -> dict:
        """The original's features, computed once and cached next to the section file."""
        cache_path = section_wav_path.with_suffix(".npz")
        if cache_path.exists():
            return features.load_features(cache_path)
        samples, sample_rate = load_wav(section_wav_path)
        result = features.extract(samples, sample_rate)
        features.save_features(cache_path, result)
        return result

    def score(self, section_wav_path: Path, attempt_samples, sample_rate):
        """Returns (score, sub_scores, verdict)."""
        original = self.original_features(section_wav_path)
        attempt = features.extract(attempt_samples, sample_rate)
        return scoring.score(original, attempt, self.use_melody)


class MockScorer:
    """Always returns 0.8 / great. Used by tests that check the API plumbing, not the scoring."""

    name = "mock"

    def score(self, section_wav_path: Path, attempt_samples, sample_rate):
        sub_scores = SubScores(timbre=0.8, melody=0.8, loudness=0.8, rhythm=0.8)
        return 0.8, sub_scores, Verdict.great


def get_scorer(name: str):
    if name == "signal":
        return SignalScorer()
    if name == "signal-no-melody":
        return SignalScorer(use_melody=False)
    if name == "mock":
        return MockScorer()
    raise ValueError(f"unknown scorer: {name}")
