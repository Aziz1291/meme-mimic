"""Refusal rules: decide if a recording is usable BEFORE any score is computed.

The scorer always outputs a number, even for silence. These rules say "that number would be
meaningless: refuse". The app decides, not the model. Used by the attempt route.
"""

import librosa
import numpy as np

from app import config
from app.audio.features import trim
from app.schemas import RefusalReason

# What the player reads. The enum is for the code and the tests; this is for humans.
MESSAGES = {
    RefusalReason.silent: "We couldn't hear you. Check your microphone.",
    RefusalReason.too_short: "Too short. Try the whole section.",
    RefusalReason.too_loud: "Too loud, the sound is distorted. Step back a little.",
    RefusalReason.too_noisy: "Too much background noise. Find a quieter place.",
    RefusalReason.too_long: "Way longer than the original. Try again.",
}


def frame_levels_db(samples):
    """Loudness of each 20 ms frame, in decibels (0 dB = the loudest possible)."""
    energy = librosa.feature.rms(y=samples, hop_length=config.HOP_LENGTH)[0]
    # log10(0) is minus infinity, so we add a tiny number first.
    return 20 * np.log10(energy + 1e-10)


def is_silent(levels_db) -> bool:
    return levels_db.max() < config.SILENT_DB


def is_too_short(trimmed_seconds) -> bool:
    return trimmed_seconds < config.MIN_ATTEMPT_SECONDS


def is_too_loud(samples) -> bool:
    # Samples stuck at the maximum mean the microphone saturated (distortion).
    clipped_share = np.mean(np.abs(samples) >= config.CLIP_LEVEL)
    return clipped_share > config.MAX_CLIPPED_SHARE


def is_too_noisy(levels_db) -> bool:
    # In a clean recording, the voice (loud frames) is far above the background (quiet frames).
    # If the gap is small, the background noise is almost as loud as the voice.
    loud = np.percentile(levels_db, 90)
    quiet = np.percentile(levels_db, 10)
    return loud - quiet < config.MIN_DYNAMIC_RANGE_DB


def is_too_long(trimmed_seconds, section_seconds) -> bool:
    limit = config.MAX_LENGTH_FACTOR * section_seconds + config.MAX_LENGTH_EXTRA_SECONDS
    return trimmed_seconds > limit


def check(samples, sample_rate, section_seconds) -> RefusalReason | None:
    """Returns the first reason to refuse, or None if the recording can be scored.

    Order matters: silence would also look like "noise only", so it's checked first.
    """
    if len(samples) == 0:
        return RefusalReason.silent
    levels_db = frame_levels_db(samples)
    if is_silent(levels_db):
        return RefusalReason.silent
    trimmed_seconds = len(trim(samples)) / sample_rate
    if is_too_short(trimmed_seconds):
        return RefusalReason.too_short
    if is_too_loud(samples):
        return RefusalReason.too_loud
    if is_too_noisy(levels_db):
        return RefusalReason.too_noisy
    if is_too_long(trimmed_seconds, section_seconds):
        return RefusalReason.too_long
    return None
