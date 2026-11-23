"""Compares the features of the original and of the attempt: 4 sub-scores → 1 score → verdict.

Used by the SignalScorer. Every threshold and weight lives in config.py.
"""

import math

import librosa
import numpy as np

from app import config
from app.schemas import SubScores, Verdict


def clip_0_1(value) -> float:
    # Careful: max(0, NaN) returns 0 in Python, which would hide a bug as a score of 0.
    # So we check for NaN/infinity first.
    if not math.isfinite(value):
        raise ValueError("a sub-score is not a finite number")
    return float(min(1.0, max(0.0, value)))


def timbre_cost(mfcc_original, mfcc_attempt) -> float:
    """DTW lines up the two sounds even if one is faster, then measures how far apart they are."""
    cost_matrix, path = librosa.sequence.dtw(X=mfcc_original, Y=mfcc_attempt, metric="cosine")
    # The total cost grows with length, so we divide by the path length: an average per step.
    return float(cost_matrix[-1, -1] / len(path))


def timbre_score(cost) -> float:
    """Turns a raw DTW cost into 0..1, using two reference points measured on real sounds:
    a good imitation (→ 1) and two unrelated sounds (→ 0)."""
    good = config.TIMBRE_COST_GOOD
    bad = config.TIMBRE_COST_BAD
    return clip_0_1((bad - cost) / (bad - good))


def melody_score(pitch_original, pitch_attempt) -> float | None:
    # No melody on either side (a scream, a noise): nothing to compare.
    if pitch_original is None or pitch_attempt is None:
        return None
    average_gap = np.mean(np.abs(pitch_original - pitch_attempt))
    return clip_0_1(1 - average_gap / config.MELODY_MAX_DIFF_SEMITONES)


def loudness_score(energy_original, energy_attempt) -> float:
    average_gap = np.mean(np.abs(energy_original - energy_attempt))
    return clip_0_1(1 - average_gap / config.LOUDNESS_MAX_DIFF)


def rhythm_score(duration_original, duration_attempt) -> float:
    """1.0 when both last the same time, 0.5 when one is twice as long."""
    longest = max(duration_original, duration_attempt)
    if longest == 0:
        return 0.0
    return min(duration_original, duration_attempt) / longest


def weighted_score(sub_scores: SubScores, use_melody=True) -> float:
    """Weighted average. If there's no melody, its weight is shared among the others
    (we divide by the sum of the weights actually used, so they still add up to 1)."""
    values = {
        "timbre": sub_scores.timbre,
        "loudness": sub_scores.loudness,
        "rhythm": sub_scores.rhythm,
    }
    if use_melody and sub_scores.melody is not None:
        values["melody"] = sub_scores.melody
    total = 0.0
    weight_sum = 0.0
    for name, value in values.items():
        total += config.WEIGHTS[name] * value
        weight_sum += config.WEIGHTS[name]
    return total / weight_sum


def verdict_for(score) -> Verdict:
    if score >= config.T_GREAT:
        return Verdict.great
    if score >= config.T_GOOD:
        return Verdict.good
    return Verdict.try_again


def score(original: dict, attempt: dict, use_melody=True):
    """Returns (score, sub_scores, verdict) for two feature dicts from features.extract()."""
    sub_scores = SubScores(
        timbre=timbre_score(timbre_cost(original["mfcc"], attempt["mfcc"])),
        melody=melody_score(original["pitch"], attempt["pitch"]),
        loudness=loudness_score(original["energy"], attempt["energy"]),
        rhythm=rhythm_score(original["duration"], attempt["duration"]),
    )
    final_score = weighted_score(sub_scores, use_melody)
    # A NaN would break JSON and means a bug upstream: never let it reach the player.
    if not math.isfinite(final_score):
        raise ValueError("score is not a finite number")
    return final_score, sub_scores, verdict_for(final_score)
