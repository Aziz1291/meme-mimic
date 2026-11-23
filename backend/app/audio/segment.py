"""Cuts audio into short sections that the player imitates one by one.

Catalog memes have hand-made sections; uploads are cut here automatically, at the natural pauses.
Used by the session routes.
"""

from http import HTTPStatus

import librosa
import numpy as np

from app import config
from app.audio.io import AudioError


def find_voice_intervals(samples, sample_rate) -> list[list[float]]:
    """Returns the non-silent parts as [start_s, end_s] pairs."""
    # Without this check, librosa would compare silence to silence and find "sound".
    if np.max(np.abs(samples)) < config.SILENCE_PEAK:
        return []
    # librosa gives sample numbers; we divide by the sample rate to get seconds.
    sample_intervals = librosa.effects.split(samples, top_db=config.SILENCE_TOP_DB)
    intervals = []
    for start_sample, end_sample in sample_intervals:
        intervals.append([start_sample / sample_rate, end_sample / sample_rate])
    return intervals


def merge_close_intervals(intervals):
    """A pause shorter than MERGE_GAP_SECONDS is a breath inside a sentence: don't cut there."""
    merged = []
    for start, end in intervals:
        if merged and start - merged[-1][1] < config.MERGE_GAP_SECONDS:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged


def merge_short_intervals(intervals):
    """A section shorter than MIN_SECTION_SECONDS is too short to imitate: join it to a neighbor."""
    merged = []
    for start, end in intervals:
        current_is_short = end - start < config.MIN_SECTION_SECONDS
        previous_is_short = merged and merged[-1][1] - merged[-1][0] < config.MIN_SECTION_SECONDS
        if merged and (current_is_short or previous_is_short):
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged


def split_long_intervals(intervals):
    """A part longer than MAX_SECTION_SECONDS is cut into equal pieces of about 1.5 s."""
    result = []
    for start, end in intervals:
        length = end - start
        if length <= config.MAX_SECTION_SECONDS:
            result.append([start, end])
            continue
        piece_count = max(2, round(length / config.TARGET_SECTION_SECONDS))
        piece_length = length / piece_count
        for piece in range(piece_count):
            piece_start = start + piece * piece_length
            result.append([piece_start, piece_start + piece_length])
    return result


def split_into_sections(samples, sample_rate) -> list[tuple[float, float]]:
    """The whole algorithm: find the voice → merge breaths → merge tiny bits → cut long parts."""
    intervals = find_voice_intervals(samples, sample_rate)
    if not intervals:
        raise AudioError(HTTPStatus.UNPROCESSABLE_ENTITY, "No voice found in this file.")
    intervals = merge_close_intervals(intervals)
    intervals = merge_short_intervals(intervals)
    intervals = split_long_intervals(intervals)
    intervals = intervals[: config.MAX_SECTIONS]

    sections = []
    for start, end in intervals:
        sections.append((round(start, 3), round(end, 3)))
    return sections


def cut_audio(samples, sample_rate, start_s: float, end_s: float):
    """Returns the samples between two times."""
    start_sample = int(round(start_s * sample_rate))
    end_sample = int(round(end_s * sample_rate))
    # A slice past the end doesn't raise an error in numpy, it just returns less.
    # So we check ourselves, to catch wrong times in catalog.json.
    if end_sample > len(samples) + sample_rate * 0.05:
        raise ValueError(f"section ends at {end_s}s but the audio is shorter")
    return samples[start_sample:end_sample]
