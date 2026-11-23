"""Tests for audio/io.py. They need ffmpeg, so they run inside Docker."""

import io
from http import HTTPStatus

import pytest
import soundfile

from app import config
from app.audio.io import AudioError, load_wav, validate_and_convert
from tests.conftest import make_tone


def wav_bytes(samples, sample_rate=16000):
    """Builds a WAV file in memory, like the browser would send."""
    buffer = io.BytesIO()
    soundfile.write(buffer, samples, sample_rate, format="WAV")
    buffer.seek(0)
    return buffer


def test_valid_wav_is_converted_to_16k_mono(tmp_path):
    output = tmp_path / "out.wav"
    # 44 100 Hz in, so we can check the conversion to 16 000 Hz.
    validate_and_convert(wav_bytes(make_tone(2.0, sample_rate=44100), 44100), output)
    samples, sample_rate = load_wav(output)
    assert sample_rate == 16000
    assert samples.ndim == 1  # mono
    assert abs(len(samples) / sample_rate - 2.0) < 0.05


def test_text_file_is_refused_with_415(tmp_path):
    fake_mp3 = io.BytesIO(b"this is not audio at all")
    with pytest.raises(AudioError) as error:
        validate_and_convert(fake_mp3, tmp_path / "out.wav")
    assert error.value.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


def test_big_file_is_refused_with_413(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1000)
    with pytest.raises(AudioError) as error:
        validate_and_convert(wav_bytes(make_tone(2.0)), tmp_path / "out.wav")
    assert error.value.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


def test_half_second_clip_is_refused_with_422(tmp_path):
    with pytest.raises(AudioError) as error:
        validate_and_convert(wav_bytes(make_tone(0.5)), tmp_path / "out.wav")
    assert error.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_long_clip_is_refused_with_422(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_SECONDS", 3.0)
    with pytest.raises(AudioError) as error:
        validate_and_convert(wav_bytes(make_tone(6.0)), tmp_path / "out.wav")
    assert error.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_error_message_has_no_technical_details(tmp_path):
    with pytest.raises(AudioError) as error:
        validate_and_convert(io.BytesIO(b"junk"), tmp_path / "out.wav")
    assert "ffprobe" not in error.value.message
    assert "/" not in error.value.message
