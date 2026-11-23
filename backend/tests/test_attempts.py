"""Tests for the attempt, result and mix routes.

Most tests use the mock scorer (always 0.8): they check the plumbing, fast.
One test plays a full game with the real signal scorer.
"""

import io

import numpy as np
import pytest
import soundfile
from fastapi.testclient import TestClient

from app import config
from app.main import app
from tests.conftest import make_silence, make_tone

client = TestClient(app)
SAMPLE_RATE = 16000


@pytest.fixture(autouse=True)
def use_fake_catalog_and_mock_scorer(fake_catalog, monkeypatch):
    monkeypatch.setattr(config, "SCORER", "mock")


def start_game():
    return client.post("/api/sessions", json={"meme_id": "meme_01"}).json()


def wav_file(samples, sample_rate=SAMPLE_RATE):
    buffer = io.BytesIO()
    soundfile.write(buffer, samples, sample_rate, format="WAV")
    return {"file": ("attempt.wav", buffer.getvalue())}


def good_recording():
    """A beep with a bit of silence around it, like a real recording."""
    return np.concatenate([make_silence(0.3), make_tone(1.4), make_silence(0.3)])


def send(session_id, section_index, samples):
    url = f"/api/sessions/{session_id}/sections/{section_index}/attempts"
    return client.post(url, files=wav_file(samples))


def test_attempt_is_scored():
    session = start_game()
    response = send(session["session_id"], 0, good_recording())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scored"
    assert body["score"] == 0.8 and body["verdict"] == "great"
    assert body["scorer"] == "mock"
    assert body["latency_ms"] > 0


def test_rule_beats_the_scorer():
    # The mock scorer would say 0.8 / great, but a silent recording must be refused.
    session = start_game()
    body = send(session["session_id"], 0, make_silence(1.0)).json()
    assert body["status"] == "refused"
    assert body["refusal_reason"] == "silent"
    assert body["score"] is None
    assert body["message"] == "We couldn't hear you. Check your microphone."


def test_attempts_are_numbered_per_section(temporary_storage):
    session_id = start_game()["session_id"]
    send(session_id, 0, good_recording())
    send(session_id, 0, good_recording())
    attempt_files = sorted(p.name for p in (temporary_storage / session_id / "attempts").iterdir())
    assert attempt_files == ["0_1.wav", "0_2.wav"]


def test_unknown_section_is_404():
    session_id = start_game()["session_id"]
    assert send(session_id, 99, good_recording()).status_code == 404


def test_unknown_session_is_404():
    assert send("not-a-uuid", 0, good_recording()).status_code == 404


def test_text_file_attempt_is_415():
    session_id = start_game()["session_id"]
    url = f"/api/sessions/{session_id}/sections/0/attempts"
    assert client.post(url, files={"file": ("x.webm", b"nope")}).status_code == 415


def test_big_attempt_is_413(monkeypatch):
    monkeypatch.setattr(config, "ATTEMPT_MAX_BYTES", 1000)
    session_id = start_game()["session_id"]
    assert send(session_id, 0, good_recording()).status_code == 413


def test_result_and_mix_before_the_end_are_409():
    session_id = start_game()["session_id"]
    send(session_id, 0, good_recording())  # section 1 not done yet
    assert client.get(f"/api/sessions/{session_id}/result").status_code == 409
    assert client.get(f"/api/sessions/{session_id}/mix").status_code == 409


def test_refused_attempt_does_not_finish_a_section():
    session_id = start_game()["session_id"]
    send(session_id, 0, good_recording())
    send(session_id, 1, make_silence(1.0))  # refused
    assert client.get(f"/api/sessions/{session_id}/result").status_code == 409


def test_full_game_result_and_mix():
    session_id = start_game()["session_id"]
    send(session_id, 0, good_recording())
    send(session_id, 1, good_recording())
    send(session_id, 1, good_recording())

    result = client.get(f"/api/sessions/{session_id}/result").json()
    assert result["total_percent"] == 80
    assert result["sections"][1]["attempt_count"] == 2

    mix = client.get(f"/api/sessions/{session_id}/mix")
    assert mix.status_code == 200
    assert mix.headers["content-type"] == "audio/wav"
    samples, sample_rate = soundfile.read(io.BytesIO(mix.content))
    # 2 recordings of 2 s + 0.2 s of silence between them.
    assert abs(len(samples) / sample_rate - 4.2) < 0.05


def test_real_scorer_full_game(monkeypatch):
    """Imitate each section with its own audio: the real scorer must give a high score."""
    monkeypatch.setattr(config, "SCORER", "signal")
    session = start_game()
    for section in session["sections"]:
        original = client.get(section["audio_url"]).content
        samples, sample_rate = soundfile.read(io.BytesIO(original))
        padded = np.concatenate([make_silence(0.3), samples, make_silence(0.3)])
        body = send(session["session_id"], section["index"], padded).json()
        assert body["status"] == "scored"
        assert body["scorer"] == "signal-v1"
        assert body["score"] > 0.85
    result = client.get(f"/api/sessions/{session['session_id']}/result").json()
    assert result["total_percent"] > 85
