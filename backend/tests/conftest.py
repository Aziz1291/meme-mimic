"""Shared test helpers (pytest loads this file automatically).

Every test gets its own empty storage folder, so tests never touch your real sessions.
"""

import json

import numpy as np
import soundfile
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


def make_chirp(seconds, start_frequency, end_frequency, sample_rate=16000):
    """A beep whose pitch slides from one frequency to another (a 'melody')."""
    times = np.arange(int(seconds * sample_rate)) / sample_rate
    frequencies = np.linspace(start_frequency, end_frequency, len(times))
    phase = 2 * np.pi * np.cumsum(frequencies) / sample_rate
    return 0.5 * np.sin(phase)


def make_noise(seconds, sample_rate=16000):
    # A fixed seed: the "random" noise is the same every run, so tests are repeatable.
    generator = np.random.default_rng(seed=0)
    return 0.3 * generator.standard_normal(int(seconds * sample_rate))


@pytest.fixture
def fake_catalog(tmp_path, monkeypatch):
    """A catalog with 2 memes made of beeps, in a temporary folder.

    meme_01: a 3 s chirp (a beep that goes up), 44 100 Hz stereo like an Audacity export.
    meme_02: a section longer than the audio, to test a broken catalog.
    """
    memes_dir = tmp_path / "memes"
    memes_dir.mkdir()
    chirp = make_chirp(3.0, 200, 400, sample_rate=44100)
    soundfile.write(memes_dir / "beep.wav", np.column_stack([chirp, chirp]), 44100)
    catalog = [
        {"id": "meme_01", "title": "Beep", "file": "beep.wav", "sections": [
            {"start_s": 0.0, "end_s": 1.5, "subtitle": "first"},
            {"start_s": 1.5, "end_s": 3.0, "subtitle": "second"},
        ]},
        {"id": "meme_02", "title": "Broken", "file": "beep.wav", "sections": [
            {"start_s": 0.0, "end_s": 9.0},  # longer than the audio: a catalog mistake
        ]},
    ]
    (memes_dir / "catalog.json").write_text(json.dumps(catalog))
    monkeypatch.setattr(config, "MEMES_DIR", memes_dir)
    monkeypatch.setattr(config, "CATALOG_PATH", memes_dir / "catalog.json")
