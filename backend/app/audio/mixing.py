"""Stitches the player's best attempts together into one WAV, for the "hear yourself" moment.

Used by GET /api/sessions/{id}/mix.
"""

from pathlib import Path

import numpy as np

from app import config
from app.audio.io import load_wav, write_wav


def mix(wav_paths: list[Path], output_path: Path) -> Path:
    """Puts the files one after the other, with a short silence between them."""
    gap = np.zeros(int(config.MIX_GAP_SECONDS * config.SAMPLE_RATE), dtype="float32")
    pieces = []
    for path in wav_paths:
        samples, _ = load_wav(path)  # every file is 16 000 Hz mono (io.py made sure of it)
        if pieces:
            pieces.append(gap)
        pieces.append(samples)
    write_wav(output_path, np.concatenate(pieces), config.SAMPLE_RATE)
    return output_path
