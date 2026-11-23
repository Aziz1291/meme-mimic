"""Shared test helpers (pytest loads this file automatically).

Every test gets its own empty storage folder, so tests never touch your real sessions.
"""

import numpy as np
import pytest

from app import config


@pytest.fixture(autouse=True)
def temporary_storage(tmp_path, monkeypatch):
    # autouse=True: applied to every test without asking for it.
    monkeypatch.setattr(config, "STORAGE_DIR", tmp_path / "sessions")
    return tmp_path / "sessions"


def make_tone(seconds, frequency=220.0, sample_rate=16000):
    """A simple beep: a fake 'voice' for tests, so no real audio file is needed."""
    times = np.arange(int(seconds * sample_rate)) / sample_rate
    return 0.5 * np.sin(2 * np.pi * frequency * times)


def make_silence(seconds, sample_rate=16000):
    return np.zeros(int(seconds * sample_rate))
