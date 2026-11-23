"""Turns a sound into numbers we can compare: MFCC (timbre), pitch (melody), energy, duration.

Pure functions: numpy arrays in, numbers/arrays out. No FastAPI, no files (except the cache helpers).
Used by the SignalScorer. The original section and the attempt always use the same settings.
"""

from pathlib import Path

import librosa
import numpy as np

from app import config


def trim(samples):
    """Removes the silence at the start and the end."""
    trimmed, _ = librosa.effects.trim(samples, top_db=config.TRIM_TOP_DB)
    return trimmed


def resample_curve(curve, point_count=config.CURVE_POINTS):
    """Stretches or squeezes a curve to a fixed number of points, so two clips of
    different lengths can be compared point by point."""
    old_positions = np.arange(len(curve))
    new_positions = np.linspace(0, len(curve) - 1, point_count)
    return np.interp(new_positions, old_positions, curve)


def mfcc(samples, sample_rate):
    """The 'fingerprint' of the sound: 13 numbers every 20 ms, normalized per coefficient."""
    matrix = librosa.feature.mfcc(
        y=samples, sr=sample_rate, n_mfcc=config.N_MFCC, hop_length=config.HOP_LENGTH
    )
    matrix = matrix[config.MFCC_FIRST_COEFFICIENT:]
    # Normalizing removes differences due to the microphone and the voice's overall color:
    # we compare the shape of the sound, not its absolute values.
    means = matrix.mean(axis=1, keepdims=True)
    spreads = matrix.std(axis=1, keepdims=True) + 1e-8  # + tiny number: never divide by 0
    return (matrix - means) / spreads


def pitch_semitones(samples, sample_rate):
    """The melody: how the voice goes up and down, in semitones relative to its own middle.

    Returns None when less than 20% of the sound has a pitch (a scream, a noise...).
    """
    frequencies, _, _ = librosa.pyin(
        samples,
        fmin=config.PITCH_MIN_HZ,
        fmax=config.PITCH_MAX_HZ,
        sr=sample_rate,
        frame_length=1024,
        hop_length=config.HOP_LENGTH,
    )
    # pyin gives NaN ("not a number") for frames without a pitch (silence, breath, noise).
    has_pitch = np.isfinite(frequencies)
    if len(frequencies) == 0 or has_pitch.mean() < config.MIN_VOICED_RATIO:
        return None
    # Relative to the median: a deep voice and a high voice can both match the same melody.
    median_frequency = np.nanmedian(frequencies)
    semitones = 12 * np.log2(frequencies / median_frequency)
    # Fill the gaps (NaN frames) by drawing a straight line between the known points.
    frame_numbers = np.arange(len(semitones))
    semitones = np.interp(frame_numbers, frame_numbers[has_pitch], semitones[has_pitch])
    return resample_curve(semitones)


def energy_envelope(samples):
    """Where the sound is loud and quiet: energy every 20 ms, divided by its max, 50 points."""
    energy = librosa.feature.rms(y=samples, hop_length=config.HOP_LENGTH)[0]
    energy = energy / (energy.max() + 1e-10)
    return resample_curve(energy)


def duration(samples, sample_rate):
    return len(samples) / sample_rate


def extract(samples, sample_rate) -> dict:
    """All features of one clip, computed on the trimmed sound."""
    trimmed = trim(samples)
    return {
        "mfcc": mfcc(trimmed, sample_rate),
        "pitch": pitch_semitones(trimmed, sample_rate),
        "energy": energy_envelope(trimmed),
        "duration": duration(trimmed, sample_rate),
    }


def save_features(path: Path, features: dict) -> None:
    """Caches the features of an original section, so each attempt doesn't recompute them."""
    pitch = features["pitch"]
    if pitch is None:
        pitch = np.array([])  # an empty array means "no melody"
    np.savez(path, mfcc=features["mfcc"], pitch=pitch,
             energy=features["energy"], duration=features["duration"])


def load_features(path: Path) -> dict:
    data = np.load(path)
    pitch = data["pitch"]
    if pitch.size == 0:
        pitch = None
    return {
        "mfcc": data["mfcc"],
        "pitch": pitch,
        "energy": data["energy"],
        "duration": float(data["duration"]),
    }
